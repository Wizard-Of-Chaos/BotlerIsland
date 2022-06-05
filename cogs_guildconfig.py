# Guild Configuration Cog, for managing guild settings and bot features.
import os
import pickle
from datetime import datetime
from collections import defaultdict
from typing import Any, Optional

import asyncio as aio
import discord as dc
from discord.ext import commands, tasks

import sqlalchemy as sql

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import (
    bot, bot_coglist, guild_whitelist, sql_engine, sql_metadata
    )

MOD_PERMS = dc.Permissions(
    administrator=True, manage_channels=True,
    manage_roles=True, manage_nicknames=True,
    )
IMAGE_EXTS = ('png', 'gif', 'jpg', 'jpeg', 'jpe', 'jfif')
AVY_CHID = 664541525350547496
ATT_CHID = 696209752434278400

Context = commands.Context

async def grab_attachments(msg):
    att_channel = bot.get_channel(ATT_CHID)
    for attachment in msg.attachments:
        att_channel.send(
            f'`@{msg.author}`: UID {msg.author.id}: `#{msg.channel}`: CID {msg.channel.id}'
            f'\nURL (defunct) `{attachment.proxy_url}`',
            file=attachment.to_file(use_cached=True),
            )


class GuildConfiguration(commands.Cog):

    COLUMN_MAP: dict[str, str] = {
        'usrlog': 'UsrLogChanId',
        'msglog': 'MsgLogChanId',
        'modlog': 'ModLogChanId',
        }

    def __init__(self, bot) -> None:
        """Initializes cog."""
        self.bot = bot
        self._log_chan_ids = {}

        self.data_load()
        self.channel_toggles = bot.get_cog('ChannelToggles')
        self.global_metadata = bot.get_cog('GlobalMetaData')
        self.user_datalogger = None

    def data_load(self) -> None:
        """Loads cog data from database."""
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

    def cog_unload(self) -> None:
        """Cleanup function run when the cog is removed or unloaded."""
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

    def get_log_channel(self, guild: int, log: str) -> int:
        """Returns requested log channel ID for a given guild."""
        return self._log_chan_ids[guild.id][log]

    async def send_to_log_channel(self, guild: int, log: str, *args: Any, **kwargs: Any) -> None:
        """Shorthand for get_log_channel().send()"""
        channel = self.bot.get_channel(self.get_log_channel(guild, log))
        await channel.send(*args, **kwargs)

    @commands.Cog.listener()
    async def on_member_join(self, member: dc.Member) -> None:
        """Logs member joins."""
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
    async def on_member_update(self, bfr: dc.Member, aft: dc.Member) -> None:
        """Logs member data updates. (Information that is specific per guild)"""
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
    async def on_member_remove(self, member: dc.Member) -> None:
        """Logs members that leave the guild in any way."""
        guild = member.guild
        if not self.get_log_channel(guild, 'usrlog'):
            return
        now = datetime.utcnow()
        lastseen = self.user_datalogger and self.user_datalogger.get_last_seen(member)
        if lastseen is not None:
            lastseenmsg = (
                f'This user was last seen on `{lastseen.strftime("%d/%m/%Y %H:%M:%S")}` '
                f'({max(0, (now-lastseen).days)} days ago)'
                )
        else:
            lastseenmsg = 'This user has not spoken to my knowledge.'
        if self.user_datalogger is None:
            roles = member.roles
        else:
            roles = map(guild.get_role, self.user_datalogger.get_roles_taken(guild, member))
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
            value=(', '.join(f'`{role}`' for role in roles) or None),
            inline=False
            )
        embed.add_field(name='**User ID:**', value=f'`{member.id}`')
        await self.send_to_log_channel(guild, 'usrlog', embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: dc.Guild, user: dc.User) -> None:
        """Logs applied guild bans."""
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
        if self.user_datalogger is None:
            roles = ()
        else:
            roles = self.user_datalogger.get_roles_taken(guild, user)
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
            value=(', '.join(f'`{guild.get_role(role)}`' for role in roles) or None),
            inline=False
            )
        embed.add_field(name='**User ID:**', value=f'`{user.id}`')
        await self.send_to_log_channel(guild, 'modlog', embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: dc.Guild, user: dc.User) -> None:
        """Logs revoked guild bans."""
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
    async def on_user_update(self, bfr: dc.User, aft: dc.User) -> None:
        """Logs user data updates. (Information that is the same across all guilds)"""
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
                    embed.set_author(
                        name=ctype,
                        icon_url=await self.global_metadata.grab_avatar(bfr),
                        )
                    embed.set_thumbnail(
                        url=await self.global_metadata.grab_avatar(aft)
                        )
                else:
                    embed.set_author(name=ctype, icon_url=aft.avatar_url)
                embed.add_field(name='**User ID:**', value=f'`{aft.id}`', inline=False)
                await self.send_to_log_channel(guild, 'msglog', embed=embed)
                        
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: dc.Member, bfr: dc.VoiceState, aft: dc.VoiceState) -> None:
        """Logs changes in member voice states."""
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
    async def on_message(self, msg: dc.Message) -> None:
        """Logs messages added."""
        if msg.guild is None:
            return
        ctx = await bot.get_context(msg)
        dont_ignore = self.channel_toggles.check_disabled(msg, 'ignoreplebs')
        if ctx.valid:
            if dont_ignore:
                await bot.process_commands(msg)
        elif dont_ignore and msg.content.strip().lower() in query_bank.affirmation:
            await msg.channel.send(response_bank.affirmation_response)
        elif (self.channel_toggles.has_channel_id(msg.channel, 'autoreact')
            and any(any(map(att.url.lower().endswith, IMAGE_EXTS)) for att in msg.attachments)
            ):
            await msg.add_reaction('❤️')
       
    @commands.Cog.listener()
    async def on_message_edit(self, bfr: dc.Message, aft: dc.Message) -> None:
        """Logs messages edited."""
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
    async def on_message_delete(self, msg: dc.Message) -> None:
        """Logs messages deleted."""
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
    async def config(self, ctx: Context, log: str) -> None:
        """Sets the given context channel as the log channel for the given log type."""
        if log not in self.COLUMN_MAP:
            await ctx.send(response_bank.config_args_error.format(log=log))
            return
        self._log_chan_ids[ctx.guild.id][log] = ctx.channel.id
        await ctx.send(response_bank.config_completion.format(log=log))

    @config.error
    async def config_error(self, ctx: Context, error: Exception) -> None:
        """Error handler for the config command."""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        elif isinstance(error, commands.BotMissingPermissions):
            return
        raise error


class ChannelToggles(commands.Cog):

    TABLE_MAP: dict[str, str] = {
        'autoreact': 'AutoReactConfig',
        'ignoreplebs': 'IgnoreConfig',
        'enablelatex': 'LatexConfig',
        }

    def __init__(self, bot) -> None:
        """Initializes cog."""
        self.bot = bot
        self._tables = {}
        self._toggles = {}
        self.data_load()

    def data_load(self) -> None:
        """Loads cog data from database."""
        # Load old style data
        try:
            with open(os.path.join('data', 'config.pkl'), 'rb') as config_file:
                config_data = pickle.load(config_file)
        except FileNotFoundError:
            config_data = None
        # Load channel flags tables
        for field, table_name in self.TABLE_MAP.items():
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
                                {'ChannelId': channel_id, 'GuildId': guild_id}
                                for channel_id in guild_data[field]
                                ],
                            )
                    dbconn.commit()
        with sql_engine.connect() as dbconn:
            for field in self.TABLE_MAP:
                self._toggles[field] = defaultdict(set)
                for channel_id, guild_id in dbconn.execute(self._tables[field].select()):
                    self._toggles[field][guild_id].add(channel_id)
            dbconn.commit()

    def cog_unload(self) -> None:
        """Cleanup function run when the cog is removed or unloaded."""
        with sql_engine.connect() as dbconn:
            for field in self.TABLE_MAP:
                dbconn.execute(self._tables[field].delete())
                dbconn.execute(
                    self._tables[field].insert(),
                    [
                        {'ChannelId': channel_id, 'GuildId': guild_id}
                        for guild_id, channels in self._toggles[field]
                        for channel_id in channels
                        ]
                    )
            dbconn.commit()
        super().cog_unload()

    def check_enabled(self, msg: dc.Message, field: str) -> bool:
        """Returns True if the channel is considered toggled on, or if the author is a moderator."""
        if MOD_PERMS.value & msg.author.guild_permissions.value:
            return True
        return msg.channel.id in self._toggles[field][msg.guild.id]

    def check_disabled(self, msg: dc.Message, field: str) -> bool:
        """Returns True if the channel is considered toggled off, or if the author is a moderator."""
        if MOD_PERMS.value & msg.author.guild_permissions.value:
            return True
        return msg.channel.id not in self._toggles[field][msg.guild.id]

    def has_channel_id(self, channel: dc.abc.GuildChannel, field: str) -> bool:
        """Returns True if the toggled set contains the given channel."""
        if not hasattr(channel, 'guild') or channel.guild is None:
            return False
        return channel.id in self._toggles[field][channel.guild.id]

    def get_channel_ids(self, guild: dc.Guild, field: str) -> frozenset[int, ...]:
        """Returns the entire toggled set."""
        return frozenset(self._toggles[field][guild.id])
    
    def toggle_channel_flag(self, ctx: Context, field: str) -> bool:
        """Toggles the channel in the given context."""
        channel_id = ctx.channel.id
        channels = self._toggles[field][ctx.guild.id]
        if channel_id in channels:
            channels.add(channel_id)
            return True
        else:
            channels.remove(channel_id)
            return False

    @commands.command()
    @commands.bot_has_permissions(add_reactions=True, read_message_history=True)
    @commands.has_guild_permissions(manage_messages=True)
    async def autoreact(self, ctx: Context) -> None:
        """Toggles the automatic image reaction feature in the given context channel."""
        if self.toggle_channel_flag(ctx, 'autoreact'):
            await ctx.send(response_bank.allow_reacts)
        else:
            await ctx.send(response_bank.deny_reacts)

    @autoreact.error
    async def autoreact_error(self, ctx: Context, error: Exception) -> None:
        """Error handler for autoreact command."""
        if isinstance(error, commands.BotMissingPermissions):
            return
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        raise error

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.has_guild_permissions(manage_roles=True)
    async def ignoreplebs(self, ctx: Context) -> None:
        """Toggles whether non-moderators can use commands in the given context channel."""
        if self.toggle_channel_flag(ctx, 'ignoreplebs'):
            await ctx.send(response_bank.allow_users)
        else:
            await ctx.send(response_bank.deny_users)

    @ignoreplebs.error
    async def ignoreplebs_error(self, ctx: Context, error: Exception) -> None:
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        raise error

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.has_guild_permissions(manage_roles=True)
    async def togglelatex(self, ctx: Context) -> None:
        """Toggles whether the latex command is usable in the given context channel."""
        if self.toggle_channel_flag(ctx, 'enablelatex'):
            await ctx.send(response_bank.allow_latex)
        else:
            await ctx.send(response_bank.deny_latex)
            
    @togglelatex.error
    async def togglelatex_error(self, ctx: Context, error: Exception) -> None:
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        raise error


class GlobalMetaData(commands.Cog):

    HISTORY_LIMIT: int = 16
    
    def __init__(self, bot) -> None:
        """Initializes cog."""
        self.bot = bot
        self._records = {}
        self.data_load()

    def data_load(self) -> None:
        """Loads cog data from database."""
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
                    self._records['avatar_count'] = self._records['latex_count'] = 0
                else:
                    dbconn.execute(self._global_counters.insert().values(
                        AvatarCount=member_data['avatar_count'],
                        LatexCount=member_data['latex_count'],
                        ))
                    self._records['avatar_count'] = member_data['avatar_count']
                    self._records['latex_count'] = member_data['latex_count']
                dbconn.commit()
        else:
            with sql_engine.connect() as dbconn:
                counts = list(dbconn.execute(self._global_counters.select()))[0]
                self._records['avatar_count'], self._records['latex_count'] = counts

    def cog_unload(self) -> None:
        """Cleanup function run when the cog is removed or unloaded."""
        with sql_engine.connect() as dbconn:
            dbconn.execute(self._global_counters.delete())
            dbconn.execute(self._global_counters.insert().values(
                AvatarCount=self._records['avatar_count'],
                LatexCount=self._records['latex_count'],
                ))
            dbconn.commit()
        super().cog_unload()

    def get_record_id(self, record: str) -> int:
        """Returns a post-increment of a given record counter."""
        record_id = self._records[record]
        self._records[record] = (record_id + 1) & 0xFFFFFFFF
        return record_id

    async def grab_avatar(self, user: dc.User) -> Optional[str]:
        """
        Attempts to pull the given user's avatar into a holding channel, then return the url.
        Returns a default url if the operation fails.
        """
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
        async for msg in avy_channel.history(limit=self.HISTORY_LIMIT):
            if msg.content.split()[-1] == msg_id:
                return msg.attachments[0].url
        raise RuntimeError(response_bank.unexpected_state)


async def setup():
    await bot.add_cog(ChannelToggles(bot))
    await bot.add_cog(GlobalMetaData(bot))
    await bot.add_cog(GuildConfiguration(bot))

bot_coglist.append(setup())
