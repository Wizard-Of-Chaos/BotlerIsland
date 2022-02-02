# User Data Logger Cog, to handle user metrics and other boring stuff for mod reporting.
import os
import pickle
from datetime import datetime

import discord as dc
from discord.ext import commands, tasks

import sqlalchemy as sql

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import (
    bot, sql_engine, sql_metadata, guild_whitelist,
    CONST_ADMINS, CONST_AUTHOR,
    )
import cogs_guildconfig


class UserDataLogger(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
        self.guild_config = bot.get_cog('GuildConfiguration')
        if self.guild_config is not None:
            self.guild_config.user_datalogger = self
        else:
            raise RuntimeError(response_bank.unexpected_state)
        self.data_load()

    def data_load(self):
        missing_tables = False
        try:
            self.user_joindata = sql_metadata.tables['UserJoinData']
        except KeyError:
            self.user_joindata = sql.Table(
                'UserJoinData', sql_metadata,
                sql.Column('UserId', sql.Integer, nullable=False, primary_key=True),
                sql.Column('GuildId', sql.ForeignKey('GuildConfig.GuildId'), nullable=False, primary_key=True),
                sql.Column('RecordDateTime', sql.DateTime, nullable=False),
                sql.Column('RecordType', sql.Text, nullable=False),
                )
            missing_tables = True
        try:
            self.user_seendata = sql_metadata.tables['UserSeenData']
        except KeyError:
            self.user_seendata = sql.Table(
                'UserSeenData', sql_metadata,
                sql.Column('UserId', sql.Integer, nullable=False, primary_key=True),
                sql.Column('GuildId', sql.ForeignKey('GuildConfig.GuildId'), nullable=False, primary_key=True),
                sql.Column('LastSeenDateTime', sql.DateTime, nullable=False),
                )
            missing_tables = True
        try:
            self.user_roledata = sql_metadata.tables['UserRoleData']
        except KeyError:
            self.user_roledata = sql.Table(
                'UserRoleData', sql_metadata,
                sql.Column('RoleId', sql.Integer, nullable=False, primary_key=True),
                sql.Column('UserId', sql.Integer, nullable=False, primary_key=True),
                sql.Column('GuildId', sql.ForeignKey('GuildConfig.GuildId'), nullable=False),
                )
            missing_tables = True
        if missing_tables:
            sql_metadata.create_all(sql_engine)
            try:
                with open(os.path.join('data', 'members.pkl'), 'rb') as config_file:
                    member_data = pickle.load(config_file)
            except FileNotFoundError:
                return
            with sql_engine.connect() as dbconn:
                for guild_id, guild_data in member_data.items():
                    if not isinstance(guild_data, dict):
                        continue
                    guild = bot.get_guild(guild_id)
                    for user_id, user_data in guild_data.items():
                        member = guild and guild.get_member(user_id)
                        first_join = user_data['first_join'] and member and member.joined_at
                        if first_join is not None:
                            dbconn.execute(self.user_joindata.insert().values(
                                UserId=user_id,
                                GuildId=guild_id,
                                RecordDateTime=first_join,
                                RecordType='join',
                                ))
                        if user_data['last_seen'] is not None:
                            dbconn.execute(self.user_seendata.insert().values(
                                UserId=user_id,
                                GuildId=guild_id,
                                LastSeenDateTime=user_data['last_seen'],
                                ))
                        for role_id in user_data['last_roles']:
                            dbconn.execute(self.user_roledata.insert().values(
                                RoleId=role_id,
                                UserId=user_id,
                                GuildId=guild_id,
                                ))
                        dbconn.commit()

        def get_joins_on_date(self, date):
            with sql_engine.connect() as dbconn:
                return dbconn.execute(self.user_joindata
                    .select()
                    .where(sql.cast(self.user_joindata.c.RecordDateTime, sql.Date) == date)
                    )

        def get_first_join(self, member):
            with sql_engine.connect() as dbconn:
                cols = self.user_joindata.c
                return dbconn.execute(self.user_joindata
                    .select(cols.RecordDateTime)
                    .where(
                        cols.UserId == member.id
                        and cols.GuildId == member.guild.id
                        and cols.RecordType == 'join'
                        )
                    .order_by(cols.RecordType.asc())
                    )[0][0]

        def get_roles_taken(self, guild, user):
            with sql_engine.connect() as dbconn:
                cols = self.user_roledata.c
                return dbconn.execute(self.user_roledata
                    .select(cols.RoleId)
                    .where(cols.GuildId == guild.id and cols.UserId == user.id)
                    )

        def get_last_seen(self, member):
            with sql_engine.connect() as dbconn:
                cols = self.user_joindata.c
                record = dbconn.execute(self.user_joindata
                    .select(cols.LastSeenDateTime)
                    .where(cols.GuildId == member.guild.id and cols.UserId == member.id)
                    )
                if record:
                    return record[0][0]
                return None

        @commands.Cog.listener()
        async def on_message(self, msg):
            with sql_engine.connect() as dbconn:
                cols = self.user_seendata.c
                has_record = dbconn.execute(self.user_seendata
                    .select()
                    .where(
                        cols.UserId == msg.author.id
                        and cols.GuildId == msg.guild.id
                        )
                    )
                if has_record:
                    dbconn.execute(self.user_seendata.update()
                        .where(
                            cols.UserId == msg.author.id
                            and cols.GuildId == msg.guild.id
                            )
                        .values(LastSeenDateTime=msg.created_at)
                        )
                else:
                    dbconn.execute(self.user_seendata.insert().values(
                        UserId=msg.author.id,
                        GuildId=msg.guild.id,
                        LastSeenDateTime=msg.created_at,
                        ))
                dbconn.commit()

        @commands.Cog.listener()
        async def on_member_join(self, member):
            user_id = member.id
            guild_id = member.guild.id
            with sql_engine.conenct() as dbconn:
                dbconn.execute(self.user_joindata.insert().values(
                    UserId=user_id,
                    GuildId=guild_id,
                    RecordDateTime=member.joined_at,
                    RecordType='join',
                    ))
                cols = self.user_roledata.c
                role_ids = dbconn.execute(self.user_roledata
                    .select(cols.RoleId)
                    .where(cols.UserId == user_id and cols.GuildId == guild_id)
                    )
                if role_ids: # Restore roles if role data had been saved
                    dbconn.execute(self.user_roledata
                        .delete()
                        .where(cols.UserId == user_id and cols.GuildId == guild_id)
                        )
                    role_getter = member.guild.get_role
                    await member.add_roles(
                        *(role_getter(role_row[0]) for role_row in role_ids),
                        reason='Restore roles lost upon leaving guild'
                        )
                dbconn.commit()

        @commands.Cog.listener()
        async def on_member_remove(self, member):
            user_id = member.id
            guild_id = member.guild.id
            with sql_engine.conenct() as dbconn:
                dbconn.execute(self.user_joindata.insert().values(
                    UserId=user_id,
                    GuildId=guild_id,
                    RecordDateTime=datetime.utcnow(),
                    RecordType='leave',
                    ))
                dbconn.execute(self.user_roledata.insert(), # Save role data
                    [
                        {'RoleId': role.id, 'UserId': user_id, 'GuildId': guild_id}
                        for role in member.roles[1:]
                        ],
                    )
                dbconn.commit()

        @commands.Cog.listener()
        async def on_member_ban(self, guild, user):
            with sql_engine.conenct() as dbconn:
                dbconn.execute(self.user_joindata.insert().values(
                    UserId=user.id,
                    GuildId=guild.id,
                    RecordDateTime=datetime.utcnow(),
                    RecordType='ban',
                    ))
                dbconn.commit()


bot.add_cog(UserDataLogger(bot))
