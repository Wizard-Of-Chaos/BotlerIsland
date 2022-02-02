# Guild Configuration Cog, for managing guild settings and bot features.
import os
import pickle
from datetime import datetime
from collections import defaultdict

import asyncio as aio
import discord as dc
from discord.ext import commands, tasks

import sqlalchemy as sql

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import (
    bot, guild_whitelist, sql_engine, sql_metadata
    )

MOD_PERMS = dc.Permissions(
    administrator=True, manage_channels=True,
    manage_roles=True, manage_nicknames=True,
    )
IMAGE_EXTS = ('png', 'gif', 'jpg', 'jpeg', 'jpe', 'jfif')
AVY_CHID = 664541525350547496
ATT_CHID = 696209752434278400

async def grab_attachments(msg):
    att_channel = bot.get_channel(ATT_CHID)
    for attachment in msg.attachments:
        att_channel.send(
            f'`@{msg.author}`: UID {msg.author.id}: `#{msg.channel}`: CID {msg.channel.id}'
            f'\nURL (defunct) `{attachment.proxy_url}`',
            file=attachment.to_file(use_cached=True),
            )


class GuildConfiguration(commands.Cog):

    COLUMN_MAP = {
        'usrlog': 'UsrLogChanId',
        'msglog': 'MsgLogChanId',
        'modlog': 'ModLogChanId',
        }

    def __init__(self, bot):
        self.bot = bot
        self._log_chan_ids = {}

        self.data_load()
        bot.add_cog(ChannelToggles(bot))
        bot.add_cog(GlobalMetaData(bot))
        self.channel_toggles = bot.get_cog('ChannelToggles')
        self.global_metadata = bot.get_cog('GlobalMetaData')
        self.user_datalogger = None

    def data_load(self):
        # Load guild config table
        try:
            self._guild_config = sql_metadata.tables['GuildConfig']
        except KeyError:
            self._guild_config = sql.Table(
                'GuildConfig', sql_metadata,
                sql.Column('GuildId', sql.Integer, nullable=False, primary_key=True),
                sql.Column('UsrLogChanId', sql.Integer, nullable=True),
                sql.Column('MsgLogChanId', sql.Integer, nullable=True),
                sql.Column('ModLogChanId', sql.Integer, nullable=True),
                )
            sql_metadata.create_all(sql_engine)
            # Populate guild config table
            with sql_engine.connect() as dbconn:
                try:
                    with open(os.path.join('data', 'config.pkl'), 'rb') as config_file:
                        config_data = pickle.load(config_file)
                except FileNotFoundError:
                    dbconn.execute(
                        self._guild_config.insert(),
                        [{'GuildId': guild_id} for guild_id in guild_whitelist],
                        )
                else:
                    dbconn.execute(
                        self._guild_config.insert(),
                        [{
                            'GuildId': guild_id,
                            'UsrLogChanId': guild_data['usrlog'],
                            'MsgLogChanId': guild_data['msglog'],
                            'ModLogChanId': guild_data['modlog'],
                            }
                            for guild_id, guild_data in config_data.items()
                            ],
                        )
                dbconn.commit()
        with sql_engine.connect() as dbconn:
            for guild_id, *chan_ids in dbconn.execute(self._guild_config.select()):
                self._log_chan_ids[guild_id] = dict(zip(self.COLUMN_MAP, chan_ids))

    def cog_unload(self):
        with sql_engine.connect() as dbconn:
            dbconn.execute(self._guild_config.delete())
            dbconn.execute(
                self._guild_config.insert(),
                [{
                    'GuildId': guild_id,
                    'UsrLogChanId': guild_data['usrlog'],
                    'MsgLogChanId': guild_data['msglog'],
                    'ModLogChanId': guild_data['modlog'],
                    }
                    for guild_id, guild_data in self._log_chan_ids.items()
                    ],
                )
                dbconn.commit()
        super().cog_unload()

    def get_log_channel(self, guild, log):
        return self._log_chan_ids[guild][log]

    async def send_to_log_channel(self, guild, log, *args, **kwargs):
        channel = self.bot.get_channel(self.get_log_channel(guild, log))
        await channel.send(*args, **kwargs)

    @commands.Cog.listener()
    async def on_member_join(self, member): # Log joined members
        guild = member.guild
        if not self.get_log_channel(guild, 'usrlog'):
            return
        embed = dc.Embed(
            color=dc.Color.green(),
            timestamp=datetime.utcnow(),
            description=f':green_circle: {member.mention}: ``{member}`` has joined **{guild}**!\n'
            f'The guild now has {guild.member_count} members!\n'
            f'This account was created on `{member.created_at.strftime("%d/%m/%Y %H:%M:%S")}`'
            )
        embed.set_author(name=f'A user has joined the server!')
        embed.set_thumbnail(url=member.avatar_url)
        embed.add_field(name='**User ID**', value=f'`{member.id}`')
        # TODO: make extensible
        banfield = "<:tereziGun:334848458940874752>"
        if ("RTFKT" in member.name):
            embed.add_field(name=banfield, value="banned for nft")
            await member.ban()
        else:
            embed.add_field(name=banfield, value="passed checks")
        await self.send_to_log_channel(guild, 'usrlog', embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, bfr, aft): # Log role and nickname changes
        guild = bfr.guild
        if not self.get_log_channel(guild, 'msglog'):
            return
        if bfr.nick != aft.nick:
            embed = dc.Embed(
                color=dc.Color.magenta(),
                timestamp=datetime.utcnow(),
                description=f'**{bfr}** had their nickname changed to **{aft.nick}**',
                )
            embed.set_author(name='Nickname Update:', icon_url=aft.avatar_url)
            embed.add_field(name='**User ID:**', value=f'`{aft.id}`', inline=False)
            await self.send_to_log_channel(guild, 'msglog', embed=embed)
        if bfr.roles != aft.roles:
            embed = dc.Embed(
                color=dc.Color.teal(),
                timestamp=datetime.utcnow(),
                description=f'**{bfr}** had the following roles changed:',
                )
            embed.set_author(name='Role Update:', icon_url=aft.avatar_url)
            rolesprev, rolesnext = set(bfr.roles), set(aft.roles)
            embed.add_field(
                name='**Roles Added:**',
                value=', '.join(f'`{role.name}`' for role in rolesnext-rolesprev) or None,
                inline=False
                )
            embed.add_field(
                name='**Roles Removed:**',
                value=', '.join(f'`{role.name}`' for role in rolesprev-rolesnext) or None,
                inline=False
                )
            embed.add_field(name='**User ID:**', value=f'`{aft.id}`', inline=False)
            await self.send_to_log_channel(guild, 'msglog', embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member): # Log left/kicked/banned members
        guild = member.guild
        if not self.get_log_channel(guild, 'usrlog'):
            return
        now = datetime.utcnow()
        if self.user_datalogger is not None:
            lastseen = self.user_datalogger.get_last_seen(member)
            lastseenmsg = (
                f'This user was last seen on `{lastseen.strftime("%d/%m/%Y %H:%M:%S")}` '
                f'({max(0, (now-lastseen).days)} days ago)'
                )
        else:
            lastseenmsg = 'This user has not spoken to my knowledge.'
        embed = dc.Embed(
            color=dc.Color.red(),
            timestamp=now,
            description=f':red_circle: **{member}** has left **{guild}**!\n'
            f'The guild now has {guild.member_count} members!\n{lastseenmsg}'
            )
        embed.set_author(name=f'A user left or got bucked off.')
        embed.set_thumbnail(url=member.avatar_url)
        embed.add_field(
            name='**Roles Snagged:**',
            value=(', '.join(
                    f'`{guild.get_role(role).name}`'
                    for role in member.roles
                    )
                or None),
            inline=False)
        embed.add_field(name='**User ID:**', value=f'`{member.id}`')
        await self.send_to_log_channel(guild, 'usrlog', embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user): # Log member full bans
        if not self.get_log_channel(guild, 'modlog'):
            return
        async for entry in guild.audit_logs(limit=256, action=dc.AuditLogAction.ban):
            if entry.target.id == user.id:
                break
        else:
            await self.send_to_log_channel(
                guild, 'modlog',
                f'The last ban of {user} `{user.id}` could not be found in the audit log.',
                )
            return
        author = entry.user
        embed = dc.Embed(
            color=author.color,
            timestamp=datetime.utcnow(),
            description=f'**{author}** has full banned :hammer: **{user}**!'
            )
        embed.set_author(name=f'Good riddance.', icon_url=author.avatar_url)
        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(
            name='**Reason:**',
            value=entry.reason or 'None specified.',
            inline=False,
            )
        embed.add_field(
            name='**Roles Snagged:**',
            value=(', '.join(
                    f'`{guild.get_role(role).name}`'
                    for role in member_stalker.get('last_roles', user)
                    )
                or None),
            inline=False)
        embed.add_field(name='**User ID:**', value=f'`{user.id}`')
        await self.send_to_log_channel(guild, 'modlog', embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user): # Log member full ban appeals
        if not self.get_log_channel(guild, 'modlog'):
            return
        embed = dc.Embed(
            color=dc.Color.dark_teal(),
            timestamp=datetime.utcnow(),
            description=f'**{user}** has been unbanned :angel:!'
            )
        embed.set_author(name='Parole has been granted.')
        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name='**User ID:**', value=f'`{user.id}`')
        await self.send_to_log_channel(guild, 'modlog', embed=embed)

    @commands.Cog.listener()
    async def on_user_update(self, bfr, aft): # Log avatar, name, discrim changes
        for guild in bot.guilds:
            if not (self.get_log_channel(guild, 'msglog') and guild.get_member(bfr.id)):
                continue
            changelog = []
            if bfr.name != aft.name:
                changelog.append((
                    'Username Update:',
                    f'**Old Username:** {bfr}\n**New Username:** {aft}',
                    ))
            if bfr.discriminator != aft.discriminator:
                changelog.append((
                    'Discriminator Update:',
                    f'{bfr} had their discriminator changed from '
                    f'{bfr.discriminator} to {aft.discriminator}',
                    ))
            await aio.sleep(0)
            if bfr.avatar != aft.avatar:
                changelog.append(('Avatar Update:', f'{bfr} has changed their avatar to:'))
            for ctype, desc in changelog:
                embed = dc.Embed(
                    color=dc.Color.purple(),
                    timestamp=datetime.utcnow(),
                    description=desc,
                    )
                if ctype.startswith('Avatar'):
                    embed.set_author(name=ctype, icon_url=await grab_avatar(bfr))
                    embed.set_thumbnail(url=await grab_avatar(aft))
                else:
                    embed.set_author(name=ctype, icon_url=aft.avatar_url)
                embed.add_field(name='**User ID:**', value=f'`{aft.id}`', inline=False)
                await self.send_to_log_channel(guild, 'msglog', embed=embed)
                        
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, bfr, aft): # Log when a member joins and leaves VC
        guild = member.guild
        if not self.get_log_channel(guild, 'msglog'):
            return
        changelog = None
        if bfr.channel != aft.channel:
            if bfr.channel == None:
                changelog = f':loud_sound: **{member}** has joined **{aft.channel}**'
            elif aft.channel == None:
                changelog = f':loud_sound: **{member}** has left **{bfr.channel}**'
        if changelog is not None: 
            embed = dc.Embed(color=dc.Color.blurple(), description=changelog)
            await self.send_to_log_channel(guild, 'msglog', embed=embed)

    @commands.Cog.listener()
    async def on_message(self, msg): # Message posted event
        if msg.guild is None:
            return
        ctx = await bot.get_context(msg)
        dont_ignore = self.channel_toggles.check_disabled(msg, 'ignoreplebs')
        if ctx.valid:
            if dont_ignore:
                await bot.process_commands(msg)
        elif dont_ignore and msg.content.strip().lower() in query_bank.affirmation:
            await msg.channel.send(response_bank.affirmation_response)
        elif (msg.channel.id in self.channel_toggles.get_channel_ids(msg.guild, 'autoreact')
            and any(any(map(att.url.lower().endswith, IMAGE_EXTS)) for att in msg.attachments)
            ):
            await msg.add_reaction('❤️')
       
    @commands.Cog.listener()
    async def on_message_edit(self, bfr, aft): # Log edited messages
        if bfr.author == bot.user or bfr.content == aft.content:
            return
        guild = bfr.guild
        if not self.get_log_channel(guild, 'msglog'):
            return
        if len(bfr.content) <= 1024:
            bfrmsg = bfr.content
            long_edit = False
        else:
            bfrmsg = '`D--> The pre-edit message is too long to contain.`'
            long_edit = True
            with open('tmpmsg.txt', 'w') as bfrfile:
                bfrfile.write(bfr.content)
        if len(aft.content) <= 1024:
            aftmsg = aft.content
        else:
            aftmsg = f'`D--> The post-edit message is too long, use this:` {aft.jump_url}'
        embed = dc.Embed(color=dc.Color.gold(), timestamp=aft.edited_at)
        embed.set_author(
            name=f'@{bfr.author} edited a message in #{bfr.channel}:',
            icon_url=bfr.author.avatar_url,
            )
        embed.add_field(name='**Before:**', value=bfrmsg, inline=False)
        embed.add_field(name='**After:**', value=aftmsg, inline=False)
        embed.add_field(name='**Message ID:**', value=f'`{aft.id}`')
        embed.add_field(name='**User ID:**', value=f'`{bfr.author.id}`')
        if long_edit:
            with open('tmpmsg.txt', 'r') as bfrfile:
                await self.send_to_log_channel(
                    guild, 'msglog', embed=embed,
                    file=dc.File(bfrfile, f'{bfr.id}-old.txt'),
                    )
        else:
            await self.send_to_log_channel(guild, 'msglog', embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, msg): # Log deleted messages
        if msg.guild is None:
            return
        guild = msg.channel.guild
        if not self.get_log_channel(guild, 'msglog'):
            return
        embed = dc.Embed(
            color=dc.Color.darker_grey(),
            timestamp=msg.created_at,
            description=msg.content,
            )
        embed.set_author(
            name=f'@{msg.author} deleted a message in #{msg.channel}:',
            icon_url=msg.author.avatar_url,
            )
        embed.add_field(name='**Message ID:**', value=f'`{msg.id}`')
        embed.add_field(name='**User ID:**', value=f'`{msg.author.id}`')
        if msg.attachments:
            embed.add_field(
                name='**Attachments:**',
                value='\n'.join(att.url for att in msg.attachments),
                inline=False,
                )
        await self.send_to_log_channel(guild, 'msglog', embed=embed)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.has_guild_permissions(manage_channels=True)
    async def config(self, ctx, log: str):
        if log not in self.COLUMN_MAP:
            await ctx.send(response_bank.config_args_error.format(log=log))
            return
        self._log_chan_ids[ctx.guild.id][log] = ctx.channel.id
        await ctx.send(response_bank.config_completion.format(log=log))

    @config.error
    async def config_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        elif isinstance(error, commands.BotMissingPermissions):
            return
        raise error


class ChannelToggles(commands.Cog):

    TABLE_MAP = {
        'autoreact': 'AutoReactConfig',
        'ignoreplebs': 'IgnoreConfig',
        'enablelatex': 'LatexConfig',
        }

    def __init__(self, bot):
        self.bot = bot
        self._tables = {}
        self._toggles = {}
        self.data_load()

    def data_load(self):
        # Load old style data
        try:
            with open(os.path.join('data', 'config.pkl'), 'rb') as config_file:
                config_data = pickle.load(config_file)
        except FileNotFoundError:
            config_data = None
        # Load channel flags tables
        for field in ('autoreact', 'ignoreplebs', 'enablelatex'):
            table_name = self.TABLE_MAP[field]
            try:
                self._tables[field] = sql_metadata.tables[table_name]
            except KeyError:
                self._tables[field] = sql.Table(
                    table_name, sql_metadata,
                    sql.Column('ChannelId', sql.Integer, nullable=False, primary_key=True),
                    sql.Column('GuildId', sql.ForeignKey('GuildConfig.GuildId'), nullable=False),
                    )
                sql_metadata.create_all(sql_engine)
                # Populate channel flags tables
                if config_data is None:
                    return
                with sql_engine.connect() as dbconn:
                    for guild_id, guild_data in config_data.items():
                        if not guild_data[field]: continue
                        dbconn.execute(
                            self._tables[field].insert(),
                            [
                                {'ChannelId': chan_id, 'GuildId': guild_id}
                                for chan_id in guild_data[field]
                                ],
                            )
                    dbconn.commit()

    def cog_unload(self):
        super().cog_unload()

    def check_enabled(self, msg, field):
        if MOD_PERMS.value & msg.author.guild_permissions.value:
            return True
        table = self._tables[field]
        with sql_engine.connect() as dbconn:
            return bool(dbconn.execute(sql
                .select(table.c.ChannelId)
                .where(table.c.ChannelId == msg.channel.id)
                ))

    def check_disabled(self, msg, field):
        if MOD_PERMS.value & msg.author.guild_permissions.value:
            return True
        table = self._tables[field]
        with sql_engine.connect() as dbconn:
            return not bool(dbconn.execute(sql
                .select(table.c.ChannelId)
                .where(table.c.ChannelId == msg.channel.id)
                ))

    def get_channel_ids(self, guild, field):
        table = self._tables[field]
        with sql_engine.connect() as dbconn:
            return [row[0] for row in dbconn.execute(sql
                .select(table.c.ChannelId)
                .where(table.c.GuildId == guild.id)
                )]

    def has_channel_id(self, guild, channel, field):
        table = self._tables[field]
        with sql_engine.connect() as dbconn:
            return bool(dbconn.execute(sql
                .select(table.c.ChannelId)
                .where(table.c.GuildId == guild.id and table.c.ChannelId == channel.id)
                ))
    
    def toggle_channel_flag(self, ctx, field):
        with sql_engine.connect() as dbconn:
            table = self._tables[field]
            channel_ids = [row[0] for row in dbconn.execute(
                sql.select(table.c.ChannelId)
                .where(table.c.GuildId == ctx.guild.id)
                )]
            channel_id = ctx.channel.id
            if channel_id in channel_ids:
                dbconn.execute(table.delete().where(table.c.ChannelId == channel_id))
                dbconn.commit()
                return False
            else:
                dbconn.execute(
                    table.insert(),
                    [{'ChannelId': channel_id, 'GuildId': ctx.guild.id}],
                    )
                dbconn.commit()
                return True

    @commands.command()
    @commands.bot_has_permissions(add_reactions=True, read_message_history=True)
    @commands.has_guild_permissions(manage_messages=True)
    async def autoreact(self, ctx):
        if self.toggle_channel_flag(ctx, 'autoreact'):
            await ctx.send(response_bank.allow_reacts)
        else:
            await ctx.send(response_bank.deny_reacts)

    @autoreact.error
    async def autoreact_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            return
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        raise error

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.has_guild_permissions(manage_roles=True)
    async def ignoreplebs(self, ctx):
        if self.toggle_channel_flag(ctx, 'ignoreplebs'):
            await ctx.send(response_bank.allow_users)
        else:
            await ctx.send(response_bank.deny_users)

    @ignoreplebs.error
    async def ignoreplebs_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        raise error

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.has_guild_permissions(manage_roles=True)
    async def togglelatex(self, ctx):
        if self.toggle_channel_flag(ctx, 'enablelatex'):
            await ctx.send(response_bank.allow_latex)
        else:
            await ctx.send(response_bank.deny_latex)
            
    @togglelatex.error
    async def togglelatex_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        raise error


class GlobalMetaData(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
        self.records = {}
        self.data_load()

    def data_load(self):
        # Load global clounters table
        try:
            self._global_counters = sql_metadata.tables['GlobalCounters']
        except KeyError:
            self._global_counters = sql.Table(
                'GlobalCounters', sql_metadata,
                sql.Column('AvatarCount', sql.Integer, nullable=False),
                sql.Column('LatexCount', sql.Integer, nullable=False),
                )
            sql_metadata.create_all(sql_engine)
            # Populate global counters table
            with sql_engine.connect() as dbconn:
                try:
                    with open(os.path.join('data', 'members.pkl'), 'rb') as config_file:
                        member_data = pickle.load(config_file)
                except FileNotFoundError:
                    dbconn.execute(self._global_counters.insert(AvatarCount=0, LatexCount=0))
                    self.records['avatar_count'] = self.records['latex_count'] = 0
                else:
                    dbconn.execute(
                        self._global_counters.insert(),
                        [{
                            'AvatarCount': member_data['avatar_count'],
                            'LatexCount': member_data['latex_count'],
                            }],
                        )
                    self.records['avatar_count'] = member_data['avatar_count']
                    self.records['latex_count'] = member_data['latex_count']
                dbconn.commit()
        else:
            with sql_engine.connect() as dbconn:
                counts = list(dbconn.execute(self._global_counters.select()))[0]
                self.records['avatar_count'], self.records['latex_count'] = counts

    def cog_unload(self):
        with sql_engine.connect() as dbconn:
            dbconn.execute(self._global_counters.delete())
            dbconn.execute(
                self._global_counters.insert(),
                [{
                    'AvatarCount': self.records['avatar_count'],
                    'LatexCount': self.records['latex_count'],
                    }],
                )
            dbconn.commit()
        super().cog_unload()

    def get_record_id(self, record):
        record_id = self.records[record]
        self.records[record] = (record_id + 1) & 0xFFFFFFFF
        return record_id

    async def grab_avatar(self, user):
        avy_channel = bot.get_channel(AVY_CHID)
        with open('avatar.png', mode='wb') as avatarfile:
            try:
                await user.avatar_url.save(avatarfile)
            except dc.NotFound:
                return url_bank.null_avatar
        msg_id = f'{self.get_record_id("avatar_count"):x}'
        with open('avatar.png', mode='rb') as avatarfile:
            await avy_channel.send(
                f'`@{user}`: UID {user.id}: MID {msg_id}',
                file=dc.File(avatarfile)
                )
        async for msg in avy_channel.history(limit=16):
            if msg.content.split()[-1] == msg_id:
                return msg.attachments[0].url


bot.add_cog(GuildConfiguration(bot))
