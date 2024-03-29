# User Data Logger Cog, to handle user metrics and other boring stuff for mod reporting.
from datetime import datetime
from collections import defaultdict
from copy import deepcopy
from typing import DefaultDict

import discord as dc
from discord.ext import commands, tasks

import sqlalchemy as sql

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import (
    bot, bot_coglist, sql_engine, sql_metadata, guild_whitelist,
    CONST_ADMINS, CONST_AUTHOR,
    )
import cogs_guildconfig

Context = commands.Context


class ChanDataLogger(commands.Cog):
    
    def __init__(self, bot) -> None:
        self.bot = bot
        self.guild_config = bot.get_cog('GuildConfiguration')
        if self.guild_config is not None:
            self.guild_config.chan_datalogger = self
        else:
            raise RuntimeError(response_bank.unexpected_state)
        self.data_load()
        self._current_record = self._generate_record()

    @staticmethod
    def _generate_record() -> DefaultDict[int, DefaultDict[int, dict[str, datetime | int]]]:
        return defaultdict(lambda: defaultdict(lambda: {
            'RecordDate': datetime.utcnow().date(),
            'ChannelMutesByBot': 0,
            'MessagesAdded': 0,
            'MessagesEdited': 0,
            'MessagesDeleted': 0,
            }))

    def data_load(self) -> None:
        missing_tables = False
        try:
            self.chan_metadata = sql_metadata.tables['ChanMetaData']
        except KeyError:
            self.chan_metadata = sql.Table(
                'ChanMetaData', sql_metadata,
                sql.Column('GuildId', sql.ForeignKey('GuildConfig.GuildId'), nullable=False),
                sql.Column('ChannelId', sql.Integer, nullable=False),
                sql.Column('RecordDate', sql.Date, nullable=False),
                sql.Column('ChannelMutesByBot', sql.Integer, nullable=False),
                sql.Column('MessagesAdded', sql.Integer, nullable=False),
                sql.Column('MessagesEdited', sql.Integer, nullable=False),
                sql.Column('MessagesDeleted', sql.Integer, nullable=False),
                )
            missing_tables = True
        try:
            self.chan_topusers = sql_metadata.tables['ChanTopUsers']
        except KeyError:
            self.chan_topusers = sql.Table(
                'ChanTopUsers', sql_metadata,
                sql.Column('GuildId', sql.ForeignKey('GuildConfig.GuildId'), nullable=False),
                sql.Column('ChannelId', sql.Integer, nullable=False),
                sql.Column('UserId', sql.Integer, nullable=False),
                sql.Column('RecordDate', sql.Date, nullable=False),
                sql.Column('MessageCount', sql.Integer, nullable=False),
                )
            missing_tables = True
        if missing_tables:
            sql_metadata.create_all(sql_engine)

    def log_channel_mute(self, ctx: Context) -> None:
        self._current_record[ctx.guild.id][ctx.channel.id]['ChannelMutesByBot'] += 1

    def get_current_record(self) -> DefaultDict[int, DefaultDict[int, dict[str, datetime | int]]]:
        # While race conditions are unlikely, I'm not taking my fucking chances
        return deepcopy(self._current_record)

    def reset_current_record(self) -> None:
        self._current_record = self._generate_record()

    def update_records(self) -> None:
        with sql_engine.connect() as dbconn:
            dbconn.execute(
                self.chan_metadata.insert(),
                [
                    {'GuildId': guild_id, 'ChannelId': channel_id, **record}
                    for guild_id, guild_data in self._current_record.items()
                    for channel_id, record in guild_data.items()
                    ]
                )
            dbconn.commit()
        self._current_record = self._generate_record()

    def cog_unload(self) -> None:
        self.update_records()

    @commands.Cog.listener()
    async def on_message(self, msg: dc.Message) -> None:
        self._current_record[msg.guild.id][msg.channel.id]['MessagesAdded'] += 1

    @commands.Cog.listener()
    async def on_message_edit(self, msg_old: dc.Message, msg_new: dc.Message) -> None:
        self._current_record[msg_new.guild.id][msg_new.channel.id]['MessagesEdited'] += 1

    @commands.Cog.listener()
    async def on_message_delete(self, msg: dc.Message) -> None:
        self._current_record[msg.guild.id][msg.channel.id]['MessagesDeleted'] += 1


async def setup():
    await bot.add_cog(ChanDataLogger(bot))

bot_coglist.append(setup())
