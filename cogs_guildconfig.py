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
    bot, member_stalker, guild_whitelist, CogtextManager, sql_engine, sql_metadata
    )

modref = dc.Permissions(
    administrator=True, manage_channels=True,
    manage_roles=True, manage_nicknames=True,
    )
image_exts = ('png', 'gif', 'jpg', 'jpeg', 'jpe', 'jfif')
avy_chid = 664541525350547496
att_chid = 696209752434278400

async def grab_avatar(user):
    avy_channel = bot.get_channel(avy_chid)
    with open('avatar.png', mode='wb') as avatarfile:
        try:
            await user.avatar_url.save(avatarfile)
        except dc.NotFound:
            return url_bank.null_avatar
    msg_id = hex(member_stalker.member_data['avatar_count'])[2:]
    member_stalker.member_data['avatar_count'] += 1
    with open('avatar.png', mode='rb') as avatarfile:
        await avy_channel.send(
            f'`@{user}`: UID {user.id}: MID {msg_id}',
            file=dc.File(avatarfile)
            )
    async for msg in avy_channel.history(limit=16):
        if msg.content.split()[-1] == msg_id:
            return msg.attachments[0].url

async def grab_attachments(msg):
    pass


class GuildConfiguration(commands.Cog):

    log_map = {
        'usrlog': 'UsrLogChanId',
        'msglog': 'MsgLogChanId',
        'modlog': 'ModLogChanId',
        'autoreact': 'AutoReactChanId',
        'ignoreplebs': 'IgnoreChanId',
        'enablelatex': 'LatexChanId',
        }
    table_map = {
        'usrlog': 'GuildConfig',
        'msglog': 'GuildConfig',
        'modlog': 'GuildConfig',
        'autoreact': 'AutoReactConfig',
        'ignoreplebs': 'IgnoreConfig',
        'enablelatex': 'LatexConfig',
        }

    def __init__(self, bot):
        self.bot = bot
        self.data_load()

    def data_load(self):
        is_new_style = True
        try:
            self.guild_config = sql_metadata.tables['GuildConfig']
        except KeyError:
            self.guild_config = sql.Table(
                'GuildConfig', sql_metadata,
                sql.Column('GuildId', sql.Integer, nullable=False, primary_key=True),
                sql.Column('UsrLogChanId', sql.Integer, nullable=True),
                sql.Column('MsgLogChanId', sql.Integer, nullable=True),
                sql.Column('ModLogChanId', sql.Integer, nullable=True),
                )
            sql_metadata.create_all(sql_engine)
            is_new_style = False
        for field in ('autoreact', 'ignoreplebs', 'enablelatex'):
            table_name = self.table_map[field]
            try:
                self.__setattr__(field, sql_metadata.tables[table_name])
            except KeyError:
                self.__setattr__(field, sql.Table(
                    table_name, sql_metadata,
                    sql.Column(self.log_map[field], sql.Integer, nullable=False, primary_key=True),
                    sql.Column('GuildId', sql.ForeignKey('GuildConfig.GuildId'), nullable=False),
                    ))
                sql_metadata.create_all(sql_engine)
                is_new_style = False
        if not is_new_style:
            with open('config.pkl', 'rb') as config_file:
                data = pickle.load(config_file)
            with sql_engine.connect() as dbconn:
                for guild_id, config in data.items():
                    dbconn.execute(self.guild_config.insert(
                        GuildId=guild_id,
                        UsrLogChanId=config['usrlog'],
                        MsgLogChanId=config['msglog'],
                        ModLogChanId=config['modlog'],
                        ))
                    for field in ('autoreact', 'ignoreplebs', 'enablelatex'):
                        dbconn.execute(
                            getattr(self, field).insert(),
                            [{self.log_map[field]: chan_id, 'GuildId': guild_id} for chan_id in config[field]],
                            )
                dbconn.commit()

    def getlog(self, guild, log):
        return self.get_channel_ids(guild, log)[0]

    def get_channel_ids(self, guild, log):
        if log in ('usrlog', 'msglog', 'modlog'):
            table = self.guild_config
        else:
            table = getattr(self, log)
        with sql_engine.connect() as dbconn:
            return [row[0] for row in dbconn.execute(sql
                .select(getattr(table.c, self.log_map[log]))
                .where(table.c.GuildId == guild.id)
                )]

    async def log(self, guild, log, *args, **kwargs):
        channel_id = self.getlog(guild, log)
        await self.bot.get_channel(channel_id).send(*args, **kwargs)

    def check_disabled(self, msg, log):
        perms = msg.author.guild_permissions
        return ((perms.value & modref.value)
            or msg.channel.id not in self.get_channel_ids(guild, log)
            )

    def check_enabled(self, msg, log):
        perms = msg.author.guild_permissions
        return ((perms.value & modref.value)
            or msg.channel.id in self.get_channel_ids(guild, log)
            )

    async def setlog(self, ctx, log):
        if log not in ('usrlog', 'msglog', 'modlog'):
            await ctx.send(response_bank.config_args_error.format(log=log))
            return
        with sql_engine.connect() as dbconn:
            guild_id = ctx.guild.id
            if dbconn.execute(self.guild_config.select()
                .where(self.guild_config.c.GuildId == guild_id)
                ):
                dbconn.execute(self.guild_config.update()
                    .where(self.guild_config.c.GuildId == guild_id)
                    .values(**{self.log_map[log]: ctx.channel.id})
                    )
            else:
                dbconn.execute(
                    self.guild_config.insert(),
                    [{self.log_map[log]: ctx.channel.id, 'GuildId': guild_id}],
                    )
            dbconn.commit()
        await ctx.send(response_bank.config_completion.format(log=log))

    def toggle(self, ctx, log):
        with sql_engine.connect() as dbconn:
            table = getattr(self, log)
            col = getattr(table.c, self.log_map[log])
            channel_ids = [row[0] for row in dbconn.execute(
                sql.select(col)
                .where(table.c.GuildId == ctx.guild.id)
                )]
            channel_id = ctx.channel.id
            if channel_id in channel_ids:
                dbconn.execute(table.delete().where(col == channel_id))
                dbconn.commit()
                return False
            else:
                dbconn.execute(
                    table.insert(),
                    [{self.log_map[log]: channel_id, 'GuildId': ctx.guild.id}],
                    )
                dbconn.commit()
                return True

    @commands.Cog.listener()
    async def on_member_join(self, member): # Log joined members
        guild = member.guild
        if not self.getlog(guild, 'usrlog'):
            return
        member_stalker.update('first_join', member)
        await member_stalker.load_roles(member)
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
        await self.log(guild, 'usrlog', embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, bfr, aft): # Log role and nickname changes
        guild = bfr.guild
        if not self.getlog(guild, 'msglog'):
            return
        if bfr.nick != aft.nick:
            embed = dc.Embed(
                color=dc.Color.magenta(),
                timestamp=datetime.utcnow(),
                description=f'**{bfr}** had their nickname changed to **{aft.nick}**',
                )
            embed.set_author(name='Nickname Update:', icon_url=aft.avatar_url)
            embed.add_field(name='**User ID:**', value=f'`{aft.id}`', inline=False)
            await self.log(guild, 'msglog', embed=embed)
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
            await self.log(guild, 'msglog', embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member): # Log left/kicked/banned members
        guild = member.guild
        if not self.getlog(guild, 'usrlog'):
            return
        member_stalker.update('first_join', member)
        member_stalker.update('last_roles', member)
        now = datetime.utcnow()
        lastseen = member_stalker.get('last_seen', member)
        if lastseen is not None:
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
                    for role in member_stalker.get('last_roles', member)
                    )
                or None),
            inline=False)
        embed.add_field(name='**User ID:**', value=f'`{member.id}`')
        await self.log(guild, 'usrlog', embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user): # Log member full bans
        if not self.getlog(guild, 'modlog'):
            return
        async for entry in guild.audit_logs(limit=256, action=dc.AuditLogAction.ban):
            if entry.target.id == user.id:
                break
        else:
            await self.log(
                guild,
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
        await self.log(guild, 'modlog', embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user): # Log member full ban appeals
        if not self.getlog(guild, 'modlog'):
            return
        embed = dc.Embed(
            color=dc.Color.dark_teal(),
            timestamp=datetime.utcnow(),
            description=f'**{user}** has been unbanned :angel:!'
            )
        embed.set_author(name='Parole has been granted.')
        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name='**User ID:**', value=f'`{user.id}`')
        await self.log(guild, 'modlog', embed=embed)

    @commands.Cog.listener()
    async def on_user_update(self, bfr, aft): # Log avatar, name, discrim changes
        for guild in bot.guilds:
            if not (self.getlog(guild, 'msglog') and guild.get_member(bfr.id)):
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
                await self.log(guild, 'msglog', embed=embed)
                        
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, bfr, aft): # Log when a member joins and leaves VC
        guild = member.guild
        if not self.getlog(guild, 'msglog'):
            return
        changelog = None
        if bfr.channel != aft.channel:
            if bfr.channel == None:
                changelog = f':loud_sound: **{member}** has joined **{aft.channel}**'
            elif aft.channel == None:
                changelog = f':loud_sound: **{member}** has left **{bfr.channel}**'
        if changelog is not None: 
            embed = dc.Embed(color=dc.Color.blurple(), description=changelog)
            await self.log(guild, 'msglog', embed=embed)

    @commands.Cog.listener()
    async def on_message(self, msg): # Message posted event
        if msg.guild is None:
            return
        member_stalker.update('last_seen', msg)
        ctx = await bot.get_context(msg)
        dont_ignore = self.check_disabled(msg, 'ignoreplebs')
        if ctx.valid:
            if dont_ignore:
                await bot.process_commands(msg)
        elif dont_ignore and msg.content.strip().lower() in query_bank.affirmation:
            await msg.channel.send(response_bank.affirmation_response)
        elif (msg.channel.id in self.get_channel_ids(msg.guild, 'autoreact')
            and any(any(map(att.url.lower().endswith, image_exts)) for att in msg.attachments)
            ):
            await msg.add_reaction('❤️')
       
    @commands.Cog.listener()
    async def on_message_edit(self, bfr, aft): # Log edited messages
        if bfr.author == bot.user or bfr.content == aft.content:
            return
        guild = bfr.guild
        if not self.getlog(guild, 'msglog'):
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
                await self.log(
                    guild, 'msglog', embed=embed,
                    file=dc.File(bfrfile, f'{bfr.id}-old.txt'),
                    )
        else:
            await self.log(guild, 'msglog', embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, msg): # Log deleted messages
        if msg.guild is None:
            return
        guild = msg.channel.guild
        if not self.getlog(guild, 'msglog'):
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
            # att_channel = bot.get_channel(att_chid)
            embed.add_field(
                name='**Attachments:**',
                value='\n'.join(att.url for att in msg.attachments),
                inline=False,
                )
        await self.log(guild, 'msglog', embed=embed)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.has_guild_permissions(manage_channels=True)
    async def config(self, ctx, log: str):
        await self.setlog(ctx, log)

    @config.error
    async def config_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        elif isinstance(error, commands.BotMissingPermissions):
            return
        raise error

    @commands.command()
    @commands.bot_has_permissions(add_reactions=True, read_message_history=True)
    @commands.has_guild_permissions(manage_messages=True)
    async def autoreact(self, ctx):
        if self.toggle(ctx, 'autoreact'):
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
        if self.toggle(ctx, 'ignoreplebs'):
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
        if self.toggle(ctx, 'enablelatex'):
            await ctx.send(response_bank.allow_latex)
        else:
            await ctx.send(response_bank.deny_latex)
            
    @togglelatex.error
    async def togglelatex_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        raise error


bot.add_cog(GuildConfiguration(bot))
