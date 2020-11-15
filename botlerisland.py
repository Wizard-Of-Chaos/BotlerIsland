#!/usr/bin/env python
# HSDBot code by Wizard of Chaos#2459 and virtuNat#7998
import io
import re
import json
from datetime import datetime, timedelta
import random
from collections import Counter
from typing import Union

import aiohttp
import asyncio as aio

import discord as dc
from discord.ext import commands, tasks
from textbanks import query_bank, response_bank
from modtools import (
    guild_whitelist, GuildConfig, MemberStalker,
    Roleplay, RoleCategories, Suggestions,
    )
from statstracker import StatsTracker

EmojiUnion = Union[dc.Emoji, dc.PartialEmoji, str]

bot = commands.Bot(command_prefix='D--> ', intents=dc.Intents.all())
bot.remove_command('help')

guild_config = GuildConfig(bot, 'config.pkl')
member_stalker = MemberStalker('members.pkl')
stats_tracker = StatsTracker('stats.pkl')
roleplay = Roleplay('roles.pkl')
role_categories = RoleCategories('rolecats.pkl')
stored_suggestions = Suggestions('suggestions.pkl')

daily_msg = {guild_id: Counter() for guild_id in guild_whitelist}
daily_usr = {guild_id: Counter({'join': 0, 'leave': 0}) for guild_id in guild_whitelist}

image_exts = ('png', 'gif', 'jpg', 'jpeg', 'jpe', 'jfif')
CONST_ADMINS = (120187484863856640, 148346796186271744) # Mac, Dirt
CONST_AUTHOR = (125433170047795200, 257144766901256192) # 9, WoC

random.seed(datetime.now())

#FUNCTIONS

def get_token():
    with open('token.dat', 'r') as tokenfile:
        raw = tokenfile.read().strip()
        return ''.join(chr(int(''.join(c), 16)) for c in zip(*[iter(raw)]*2))

def get_name(member_id):
    return str(bot.get_user(int(member_id[1])))

async def grab_avatar(user):
    avy_channel = bot.get_channel(664541525350547496)
    with open('avatar.png', mode='wb') as avatarfile:
        try:
            await user.avatar_url.save(avatarfile)
        except dc.NotFound:
            return (
                'https://cdn.discordapp.com/attachments/'
                '663453347763716110/664578577479761920/unknown.png'
                )
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

async def grab_latex(preamble, postamble, raw_latex):
    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            'https://rtex.probablyaweb.site/api/v2',
            data={'format':'png','code':preamble+raw_latex+postamble},
            )
        resp = await resp.text() # Awaiting loading of the raw text data and unicode parsing
        resp = json.loads(resp)
        if (resp['status'] != 'success'):
            return None
        return await session.get(f'https://rtex.probablyaweb.site/api/v2/{resp["filename"]}')

async def process_role_grant(msg, react, role, members):
    for member in members:
        if role not in member.roles:
            category = role_categories.get_category(role)
            if category:
                for member_role in member.roles:
                    if member_role.id in category:
                        await member.remove_roles(member_role)
            await member.add_roles(role)
        else:
            await member.remove_roles(role)
        await msg.remove_reaction(react, member)

def user_or_perms(user_id, **perms):
    perm_check = commands.has_permissions(**perms).predicate
    async def extended_check(ctx):
        if ctx.guild is None:
            return False
        try:
            return ctx.author.id in user_id or await perm_check(ctx)
        except TypeError:
            return ctx.author.id == user_id or await perm_check(ctx)
    return commands.check(extended_check)

#END OF FUNCTIONS
#TASKS

@tasks.loop(hours=24)
async def post_dailies():
    for guild_id, admin_id in zip(guild_whitelist, (CONST_ADMINS[1], CONST_AUTHOR[0])):
        guild = bot.get_guild(guild_id)
        if guild is None or guild.get_member(bot.user.id) is None:
            continue
        admin = guild.get_member(admin_id)
        now = datetime.utcnow()
        msg_counts = "\n".join(
            f'`{guild.get_channel(chan_id)}:` **{count}**'
            for chan_id, count in daily_msg[guild_id].most_common()
            )
        embed = dc.Embed(
            color=admin.color,
            timestamp=now,
            description=f'**Message counts since midnight UTC or bot start:**\n\n{msg_counts}',
            )
        embed.set_author(name=f'Daily counts for {admin}', icon_url=admin.avatar_url)
        embed.add_field(name='Users Gained:', value=daily_usr[guild_id]['join'])
        embed.add_field(name='Users Lost:', value=daily_usr[guild_id]['leave'])
        embed.add_field(
            name='**DISCLAIMER:**',
            value='Counts may not be accurate if the bot has been stopped at any point during the day.',
            inline=False,
            )
        daily_msg[guild_id].clear()
        daily_usr[guild_id].clear()
        await guild_config.log(
            guild, 'modlog',
            admin.mention if admin_id == CONST_ADMINS[1] else '',
            embed=embed,
            )

@post_dailies.before_loop
async def post_dailies_start_delay():
    now = datetime.utcnow()
    await aio.sleep(
        (datetime.combine(now.date() + timedelta(1), datetime.min.time()) - now).seconds
        )

#END OF TASKS
#EVENTS

@bot.event
async def on_ready(): # Bot starts
    for guild in bot.guilds:
        if guild.id not in guild_whitelist:
            await guild.leave()
    await bot.change_presence(
        activity=dc.Game(name=response_bank.online_status)
        )
    post_dailies.start()
    userhelp_embed.set_author(name='Help message', icon_url=bot.user.avatar_url)
    print(response_bank.process_reacts)
    # This is a horrible fucking way of granting all the roles. Too bad!
    for chn_id, msg_dict in roleplay:
        channel = bot.get_channel(chn_id)
        for msg_id, emoji_dict in msg_dict.items():
            msg = await channel.fetch_message(msg_id)
            for react in msg.reactions:
                if (emoji_id := roleplay.get_react_id(react)) in emoji_dict:
                    role = msg.guild.get_role(emoji_dict[emoji_id])
                    members = [m async for m in react.users() if m.id != bot.user.id]
                    await process_role_grant(msg, react, role, members)
    print(response_bank.process_reacts_complete)
    print(response_bank.ready_prompt)

@bot.event
async def on_guild_join(guild): # Bot joins guild
    if guild.id not in guild_whitelist:
        await guild.leave()

@bot.event
async def on_member_join(member): # Log joined members
    guild = member.guild
    if guild.id in guild_whitelist:
        daily_usr[guild.id]['join'] += 1
    if not guild_config.getlog(guild, 'usrlog'):
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
    await guild_config.log(guild, 'usrlog', embed=embed)

@bot.event
async def on_member_update(bfr, aft): # Log role and nickname changes
    guild = bfr.guild
    if not guild_config.getlog(guild, 'msglog'):
        return
    if bfr.nick != aft.nick:
        embed = dc.Embed(
            color=dc.Color.magenta(),
            timestamp=datetime.utcnow(),
            description=f'**{bfr}** had their nickname changed to **{aft.nick}**',
            )
        embed.set_author(name='Nickname Update:', icon_url=aft.avatar_url)
        embed.add_field(name='**User ID:**', value=f'`{aft.id}`', inline=False)
        await guild_config.log(guild, 'msglog', embed=embed)
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
        await guild_config.log(guild, 'msglog', embed=embed)

@bot.event
async def on_member_remove(member): # Log left/kicked/banned members
    guild = member.guild
    if guild.id in guild_whitelist:
        daily_usr[guild.id]['leave'] += 1
    if not guild_config.getlog(guild, 'usrlog'):
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
    await guild_config.log(guild, 'usrlog', embed=embed)

@bot.event
async def on_member_ban(guild, user): # Log member full bans
    if not guild_config.getlog(guild, 'modlog'):
        return
    async for entry in guild.audit_logs(limit=16, action=dc.AuditLogAction.ban):
        if entry.target.id == user.id:
            break
    else:
        print(f'The last ban of {user.id} could not be found in the logs.')
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
    await guild_config.log(guild, 'modlog', embed=embed)

@bot.event
async def on_member_unban(guild, user): # Log member full ban appeals
    if not guild_config.getlog(guild, 'modlog'):
        return
    embed = dc.Embed(
        color=dc.Color.dark_teal(),
        timestamp=datetime.utcnow(),
        description=f'**{user}** has been unbanned :angel:!'
        )
    embed.set_author(name='Parole has been granted.')
    embed.set_thumbnail(url=user.avatar_url)
    embed.add_field(name='**User ID:**', value=f'`{user.id}`')
    await guild_config.log(guild, 'modlog', embed=embed)

@bot.event
async def on_user_update(bfr, aft): # Log avatar, name, discrim changes
    for guild in bot.guilds:
        if not (guild_config.getlog(guild, 'msglog') and guild.get_member(bfr.id)):
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
            await guild_config.log(guild, 'msglog', embed=embed)
                    
@bot.event
async def on_voice_state_update(member, bfr, aft): # Log when a member joins and leaves VC
    guild = member.guild
    if not guild_config.getlog(guild, 'msglog'):
        return
    changelog = None
    if bfr.channel != aft.channel:
        if bfr.channel == None:
            changelog = f':loud_sound: **{member}** has joined **{aft.channel}**'
        elif aft.channel == None:
            changelog = f':loud_sound: **{member}** has left **{bfr.channel}**'
    if changelog is not None: 
        embed = dc.Embed(color=dc.Color.blurple(), description=changelog)
        await guild_config.log(guild, 'msglog', embed=embed)

@bot.event
async def on_message(msg): # Message posted event
    if msg.guild is None:
        return
    if msg.guild.id in guild_whitelist:
        daily_msg[msg.guild.id][msg.channel.id] += 1
    member_stalker.update('last_seen', msg)
    ctx = await bot.get_context(msg)
    if ctx.valid:
        if guild_config.getcmd(ctx):
            await bot.process_commands(msg)
    elif guild_config.getcmd(ctx) and msg.content.strip().lower() == 'good work arquius':
        await msg.channel.send('D--> 😎')
    elif (msg.channel.id in guild_config.getlog(msg.guild, 'autoreact')
        and any(any(map(att.url.lower().endswith, image_exts)) for att in msg.attachments)
        ):
        await msg.add_reaction('❤️')
    elif ctx.author != bot.user and guild_config.detect_star_wars(msg):
        dt = await guild_config.punish_star_wars(msg)
        embed = dc.Embed(
            color=ctx.author.color,
            timestamp=msg.created_at,
            description=f'D--> It seems that **{ctx.author.name}** has mentioned that which '
            'has been expressly forbidden by the powers that be, and has thus been '
            'STRONGLY punished accordingly.'
            )
        embed.set_author(name='D--> Forbidden.', icon_url=bot.user.avatar_url)
        embed.add_field(
            name='**Time since last incident:**',
            value='N/A' if dt is None else
            f'It has been {dt.days} days, {dt.seconds//3600} hours, '
            f'{dt.seconds//60%60} minutes and {dt.seconds%60} seconds.'
            )
        await ctx.send(embed=embed)
    elif ctx.author.id == CONST_ADMINS[1]:
        if ctx.channel.id == guild_config.getlog(msg.guild, 'modlog'):
            return 
        guild_config.log_linky(msg)
   
@bot.event
async def on_message_edit(bfr, aft): # Log edited messages
    if bfr.author == bot.user or bfr.content == aft.content:
        return
    guild = bfr.guild
    if not guild_config.getlog(guild, 'msglog'):
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
            await guild_config.log(
                guild, 'msglog', embed=embed,
                file=dc.File(bfrfile, f'{bfr.id}-old.txt'),
                )
    else:
        await guild_config.log(guild, 'msglog', embed=embed)

@bot.event
async def on_message_delete(msg): # Log deleted messages
    if msg.guild is None:
        return
    guild = msg.channel.guild
    if not guild_config.getlog(guild, 'msglog'):
        return
    roleplay.remove_message(msg)
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
        # att_channel = bot.get_channel(696209752434278400)
        embed.add_field(
            name='**Attachments:**',
            value='\n'.join(att.url for att in msg.attachments),
            inline=False,
            )
    await guild_config.log(guild, 'msglog', embed=embed)

@bot.event
async def on_raw_reaction_add(payload): # Reaction is added to message
    # Not on_reaction_add because of this weird assed queue of messages CHRIST i hate discord
    # Because discord can't save every message in RAM, this is what suffering looks like.
    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return
    member = guild.get_member(payload.user_id)
    if member.id == bot.user.id:
        return 
    emoji = payload.emoji
    chn_id = payload.channel_id
    msg_id = payload.message_id
    # Checks if the message is in the dict
    if react_map := roleplay.get_reactmap(chn_id, msg_id):
        # Checks if the react is in the message
        try:
            role = guild.get_role(react_map[emoji.id])
        except KeyError: # If emoji is not in the message, ignore.
            return
        except commands.RoleNotFound as exc:
            print(exc.args[0])
            return
        # There should be another exception clause here for missing roles but fuck that shit
        # Toggle role addition/removal.
        msg = await guild.get_channel(chn_id).fetch_message(msg_id)
        await process_role_grant(msg, emoji, role, (member,))

@bot.event
async def on_raw_reaction_remove(payload): # Reaction is removed from message
    # If reacts from the bot are removed from messages under the role reacts, remove the associated data.
    if (guild := bot.get_guild(payload.guild_id)) is None:
        return
    if payload.user_id != bot.user.id:
        return
    emoji = payload.emoji
    chn_id = payload.channel_id
    msg_id = payload.message_id
    # Checks if the message is in the dict
    if react_map := roleplay.get_reactmap(chn_id, msg_id):
        # Find the reaction with matching emoji, then prune all further reacts.
        msg = await guild.get_channel(chn_id).fetch_message(msg_id)
        roleplay.remove_reaction(msg, emoji)
        for react in msg.reactions:
            if str(react.emoji) == str(emoji):
                async for member in react.users():
                    await msg.remove_reaction(emoji, member)
                return

@bot.event
async def on_raw_reaction_clear_emoji(payload): # All reacts of one emoji cleared from message
    # If all reacts of a certain emoji are removed, remove associated data if it exists.
    if (guild := bot.get_guild(payload.guild_id)) is None:
        return
    emoji = payload.emoji
    chn_id = payload.channel_id
    msg_id = payload.message_id
    # Checks if the message is in the dict
    if react_map := roleplay.get_reactmap(chn_id, msg_id):
        # Find the reaction with matching emoji, then prune all further reacts.
        msg = await guild.get_channel(chn_id).fetch_message(msg_id)
        roleplay.remove_reaction(msg, emoji)

@bot.event
async def on_raw_reaction_clear(payload): # All reacts cleared from message
    # If all reacts from a message are removed, remove associated data if it exists.
    if (guild := bot.get_guild(payload.guild_id)) is None:
        return
    roleplay.remove_message(
        await guild.get_channel(payload.channel_id).fetch_message(payload.message_id)
        )

# END OF EVENTS
# INFOHELP COMMANDS

userhelp_embed = dc.Embed(
    description=f'D--> It seems you have asked about the *Homestuck and Hiveswap Discord Utility Bot*:tm:.'
        f'This is a bot designed to cater to the server\'s moderation, utility, and statistic '
        f'tracking needs. If the functions herein described are not performing to the degree '
        f'that is claimed, please direct your attention to **Wizard of Chaos#2459** or **virtuNat#7998**.\n\n'
        f'**Command List:**'
    ).set_author(
    name='Help message'
    ).add_field(
    name='`help`',
    value='Display this message.',
    inline=False,
    ).add_field(
    name='`info [user]`',
    value='Grabs user information. Leave user field empty to get your own info.',
    inline=False,
    ).add_field(
    name='`role (subcommand) [args...]`',
    value='Provides help for the role command group.',
    inline=False,
    ).add_field(
    name='`ping`',
    value='Pings the user.',
    inline=False,
    ).add_field(
    name='`fle%`',
    value='Provides you with STRONG eye candy.',
    inline=False,
    ).add_field(
    name='`husky`',
    value='Provides you with an image of a corpulent canine.',
    inline=False,
    ).add_field(
    name='`roll <n>d<f>[(+|-)<m>]`',
    value='Try your luck! Roll n f-faced dice, and maybe add a modifier m!',
    inline=False,
    ).add_field(
    name='`latex <latex_code>`',
    value='Presents a pretty little image for your latex code.',
    inline=False,
    ).add_field(
    name='`linky`',
    value='<:drewkas:684981372678570023>',
    inline=False,
    )
        
@bot.command(name='help')
@commands.bot_has_permissions(send_messages=True)
async def userhelp(ctx):
    userhelp_embed.color=ctx.author.color
    userhelp_embed.timestamp=ctx.message.created_at
    await ctx.send(embed=userhelp_embed)

@userhelp.error
async def userhelp_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command()
@commands.bot_has_permissions(send_messages=True)
async def info(ctx, *, name=None):
    if name is None:
        member = ctx.author
    elif (member := await commands.MemberConverter().convert(ctx, name)) is None:
        await ctx.send('D--> It seems that user can\'t be found. Please check your spelling.')
        return
    now = datetime.utcnow()
    firstjoin = member_stalker.get('first_join', member) or member.joined_at
    embed = dc.Embed(color=member.color, timestamp=now)
    embed.set_author(name=f'Information for {member}')
    embed.set_thumbnail(url=member.avatar_url)
    if ctx.author != member and ctx.author != bot.user:
        lastseen = member_stalker.get('last_seen', member)
        if lastseen is not None:
            lastseenmsg = (
                f'This user was last seen on `{lastseen.strftime("%d/%m/%Y %H:%M:%S")}` '
                f'({max(0, (now-lastseen).days)} days ago)'
                )
        else:
            lastseenmsg = 'This user has not spoken to my knowledge!'
        embed.add_field(name='Last Seen:', value=lastseenmsg, inline=False)
    embed.add_field(
        name='Account Created On:',
        value=f"`{member.created_at.strftime('%d/%m/%Y %H:%M:%S')}` "
        f'({(now-member.created_at).days} days ago)'
        )
    embed.add_field(
        name='Guild Last Joined On:',
        value=f"`{member.joined_at.strftime('%d/%m/%Y %H:%M:%S')}` "
        f'({(now-member.joined_at).days} days ago, {(now-firstjoin).days} days since first recorded join)'
        )
    embed.add_field(name='User ID:', value=f'`{member.id}`', inline=False)
    embed.add_field(
        name='Roles:',
        value=', '.join(f'`{role.name}`' for role in member.roles[1:]) or None,
        inline=False
        )
    if bot.user == member:
        msg = 'D--> Do you wish to check out my STRONG muscles?'
    elif ctx.author != member:
        msg = 'D--> It seems you\'re a bit of a stalker, aren\'t you?'
    else:
        msg = 'D--> I understand the need to look at yourself in the mirror.'
    await ctx.send(msg, embed=embed)

@info.error
async def info_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command()
@commands.has_guild_permissions(manage_roles=True)
@commands.bot_has_permissions(send_messages=True)
async def modhelp(ctx):
    perms = ctx.author.guild_permissions
    embed = dc.Embed(
        color=ctx.author.color,
        timestamp=ctx.message.created_at,
        description=f'D--> It seems you have asked about the *Homestuck and Hiveswap Discord Utility Bot*:tm:.'
        f'This is a bot designed to cater to the server\'s moderation, utility, and statistic '
        f'tracking needs. If the functions herein described are not performing to the degree '
        f'that is claimed, please direct your attention to **Wizard of Chaos#2459** or **virtuNat#7998**.\n\n'
        f'**Moderation Command List:**',
        )
    embed.set_author(name='Moderation Help message', icon_url=bot.user.avatar_url)
    embed.add_field(
        name='`modhelp`',
        value='(Manage Roles only) Display this message.',
        inline=False
        )
    embed.add_field(
        name='`modperms`',
        value='(Manage Roles only) Show all global guild permissions allowed.',
        inline=False
        )
    embed.add_field(
        name='`role (subcommand) [args...]`',
        value='(Manage Roles only) Provides mod help for the role command group.',
        inline=False
        )
    embed.add_field(
        name='`daily`',
        value='(Manage Roles only) Force server daily counts.',
        inline=False
        )
    embed.add_field(
        name='`autoreact`',
        value='(Manage Roles only) Toggle auto-react feature.',
        inline=False
        )
    embed.add_field(
        name='`ignoreplebs`',
        value='(Manage Roles only) Toggle non-mod commands getting ignored in a channel.',
        inline=False
        )
    embed.add_field(
        name='`togglelatex`',
        value='(Manage Roles only) Toggles whether or not latex commands can be used.',
        inline=False
        )
    embed.add_field(
        name='`channel (ban|unban) <username>`',
        value='(Manage Roles only) Add or remove a channel mute role.',
        inline=False
        )
    if perms.ban_members:
        embed.add_field(
            name='`raidban <user1> [<user2> <user3> ...]`',
            value='(Ban Members only) Ban a list of raiders.',
            inline=False
            )
    if perms.view_audit_log:
        embed.add_field(
            name='`config (msglog|usrlog|modlog)`',
            value='(View Audit only) Sets the appropriate log channel.',
            inline=False
            )
        embed.add_field(
            name='`execute order 66`',
            value='(View Audit only) Declares all Jedi to be enemies of the Republic for 5 minutes.',
            inline=False
            )
        embed.add_field(
            name='`ZA (WARUDO|HANDO)`',
            value='(View Audit Only) Utilizes highly dangerous Stand power to moderate the server.',
            inline=False
            )
    await ctx.send(embed=embed)

@modhelp.error
async def modhelp_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send('D--> Neigh, user.')
        return
    raise error

@bot.command(name='daily')
@commands.has_guild_permissions(manage_roles=True)
async def force_daily_post(ctx):
    now = datetime.utcnow()
    msg_counts = "\n".join(
        f'`{ctx.guild.get_channel(chan_id)}:` **{count}**'
        for chan_id, count in daily_msg[ctx.guild.id].most_common()
        )
    embed = dc.Embed(
        color=ctx.author.color,
        timestamp=now,
        description=f'**Message counts since midnight UTC or bot start:**\n{msg_counts}',
        )
    embed.set_author(name=f'Daily counts for {ctx.author}', icon_url=ctx.author.avatar_url)
    embed.add_field(name='Users Gained:', value=daily_usr[ctx.guild.id]['join'])
    embed.add_field(name='Users Lost:', value=daily_usr[ctx.guild.id]['leave'])
    embed.add_field(
        name='**DISCLAIMER**:',
        value=
            'Counts may not be accurate if the bot has been stopped at any point during the day.\n'
            'Counts will reset upon midnight UTC, upon which an automated message will display.',
        inline=False,
        )
    await guild_config.log(ctx.guild, 'modlog', embed=embed)

@force_daily_post.error
async def force_daily_post_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('D--> It seems you have insufficient permission elevations.')
        return
    raise error
    
@bot.command()
@commands.has_guild_permissions(manage_roles=True)
@commands.bot_has_permissions(send_messages=True)
async def modperms(ctx):
    # me and the boys using cursed if as a prototype
    permlist = ', '.join(perm for perm, val in ctx.author.guild_permissions if val)
    embed = dc.Embed(
        color=ctx.author.color,
        timestamp=datetime.utcnow(),
        description=f'```{permlist}```',
        )
    embed.set_author(name=f'{ctx.author} has the following guild perms:')
    embed.set_thumbnail(url=ctx.author.avatar_url)
    await ctx.send(embed=embed)

@modperms.error
async def modperms_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('D--> It seems you have insufficient permission elevations.')
        return
    elif isinstance(error, commands.BotMissingPermissions):
        return
    raise error

# END OF INFOHELP COMMANDS
# CONFIG COMMANDS

@bot.command()
@commands.bot_has_permissions(send_messages=True)
@commands.has_permissions(view_audit_log=True)
async def config(ctx, log: str):
    if log not in ('usrlog', 'msglog', 'modlog'):
        await ctx.send(
            'D--> It seems that you have attempted to create an invalid log. '
            'Would you like to try again? Redos are free, you know.'
            )
        return
    await ctx.send(f'D--> The {log} channel has been set and saved.')

@config.error
async def config_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            f'D--> It seems that you don\'t have the appropriate permissions for this command. '
            f'I STRONGLY recommend you back off or get bucked off, {ctx.author.name}.'
            )
        return
    elif isinstance(error, commands.BotMissingPermissions):
        return
    raise error

# END OF CONFIG
# TOGGLE COMMANDS

@bot.command()
@commands.bot_has_permissions(add_reactions=True, read_message_history=True)
@commands.has_guild_permissions(manage_roles=True)
async def autoreact(ctx):
    if guild_config.toggle(ctx, 'autoreact'):
        await ctx.send('D--> ❤️')
    else:
        await ctx.send('D--> 💔')

@autoreact.error
async def autoreact_error(ctx, error):
    if isinstance(error, BotMissingPermissions):
        return
    elif isinstance(error, MissingPermissions):
        await ctx.send('D--> Neigh.')
        return
    raise error

@bot.command()
@commands.has_guild_permissions(manage_roles=True)
async def ignoreplebs(ctx):
    if guild_config.toggle(ctx, 'ignoreplebs'):
        await ctx.send('D--> I shall listen only to b100 b100ded commands.')
    else:
        await ctx.send('D--> Unfortunately, I must now listen to the lower classes.')

@ignoreplebs.error
async def ignoreplebs_error(ctx, error):
    if isinstance(error, MissingPermissions):
        await ctx.send('D--> Neigh, plebian.')
        return
    raise error

@bot.command()
@commands.has_permissions(manage_roles=True)
async def togglelatex(ctx):
    if guild_config.toggle(ctx, 'enablelatex'):
        await ctx.send('D--> Latex functions have been enabled.')
    else:
        await ctx.send('D--> Latex functions have been disabled.')
        
@togglelatex.error
async def togglelatex_error(ctx, error):
    if isinstance(error, MissingPermissions):
        await ctx.send('D--> Neigh.')
        return
    raise error
    
# END OF TOGGLE COMMANDS
# BAN COMMANDS

@bot.group()
@commands.has_guild_permissions(manage_roles=True)
async def channel(ctx):
    # ALRIGHT HUNGOVER WIZARD OF CHAOS CODE IN THE HIZ-OUSE
    # WE GONNA WRITE SOME MOTHERFUCKING BAN COMMANDS; INITIALIZE THAT SHIT
    if ctx.invoked_subcommand is None:
        await ctx.send(
            'D--> Usage of the channel function: `channel (ban|unban) <user>`\n\n'
            '`channel ban <user>`: Apply lowest available channel mute role to user.\n'
            '`channel unban <user>`: Revoke lowest available channel mute role from user.\n'
            '<user> can be the user id, mention, or name.'
            )
        await aio.sleep(4)
        async for msg in ctx.channel.history(limit=128):
            if msg.author.id == bot.user.id and msg.content.startswith('D--> Usage'):
                await msg.delete()
                break

@channel.error
async def channel_error(ctx, error):
    if isinstance(error, (commands.MissingPermissions, commands.BotMissingPermissions)):
        return
    raise error

@channel.command(name='ban')
async def channel_ban(ctx, member: dc.Member, *, flavor=''):
    if not member: # WE'RE GRABBING A MEMBER WE GIVE NO SHITS
        return
    # WE'RE GONNA FIND THE FIRST FUCKING ROLE THAT HAS NO PERMS IN THIS CHANNEL
    # AND GUESS HOW WE DO THAT? THAT'S RIGHT, CURSED IF STATEMENT
    for role in ctx.guild.roles:
        if ctx.channel.overwrites_for(role).pair()[1].send_messages: # BOOM LOOK AT THAT SHIT SUCK MY DICK
            await member.add_roles(role)
            break
    else:
        return
    # OH BUT NOW SOMEONES GONNA WHINE THAT WE DIDNT LOG IT? HOLD YOUR ASS TIGHT BECAUSE WE'RE ABOUT TO
    if guild_config.getlog(ctx.guild, 'modlog'): # OHHHHHHH! HE DID IT! THE FUCKING MADMAN!
        embed = dc.Embed(
            color=ctx.author.color,
            timestamp=ctx.message.created_at,
            description=f'{member.mention} has been banned in **#{ctx.channel}**'
            )
        embed.add_field(name='**Role Granted:**', value=f'`{role}`')
        embed.add_field(name='**Reason and/or Duration:**', value=flavor or 'None specified')
        embed.add_field(name='**User ID:**', value=member.id, inline=False)
        embed.set_author(
            name=f'@{ctx.author} Issued Channel Ban:',
            icon_url=ctx.author.avatar_url,
            )
        await guild_config.log(ctx.guild, 'modlog', embed=embed)
        await ctx.message.delete()
        await ctx.send(f'D--> Abberant {member} has been CRUSHED by my STRONG hooves.')
        await aio.sleep(10)
        async for msg in ctx.channel.history(limit=128):
            if msg.author.id == bot.user.id and msg.content.startswith('D--> Abberant'):
                await msg.delete()
                break
        # BOOM! SUUUUUUUUCK - IT!

@channel_ban.error
async def channel_ban_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        channel = await ctx.author.create_dm()
        await channel.send(f'D--> {error.args[0]}')

@channel.command(name='unban')
async def channel_unban(ctx, member: dc.Member):
    if not member:
        return
    for role in member.roles:
        if ctx.channel.overwrites_for(role).pair()[1].send_messages:
            await member.remove_roles(role)
            break
    else:
        return
    if guild_config.getlog(ctx.guild, 'modlog'):
        embed = dc.Embed(
            color=ctx.author.color,
            timestamp=ctx.message.created_at,
            description=f'{member.mention} has been unbanned in **#{ctx.channel}**'
            )
        embed.add_field(name='**Role Revoked:**', value=f'`{role}`')
        embed.add_field(name='**User ID:**', value=member.id)
        embed.set_author(
            name=f'@{ctx.author} Undid Channel Ban:',
            icon_url=ctx.author.avatar_url,
            )
        await guild_config.log(ctx.guild, 'modlog', embed=embed)

@channel_unban.error
async def channel_unban_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        channel = await ctx.author.create_dm()
        await channel.send(f'D--> {error.args[0]}')
    raise error

@bot.command()
@commands.bot_has_guild_permissions(ban_members=True)
@user_or_perms(CONST_ADMINS+CONST_AUTHOR, ban_members=True)
async def raidban(ctx, *args):
    if not args:
        return
    for arg in args:
        member = await commands.UserConverter().convert(ctx, arg)
        await ctx.guild.ban(member, reason='Banned by anti-raid command.', delete_message_days=1)
    embed = dc.Embed(
        color=ctx.author.color,
        timestamp=ctx.message.created_at,
        )
    embed.set_author(
        name=f'{ctx.author} used raidban command:',
        icon_url=ctx.author.avatar_url,
        )
    await guild_config.log(ctx.guild, 'modlog', embed=embed)

@raidban.error
async def raidban_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        channel = await ctx.author.create_dm()
        await channel.send(f'D--> {error.args[0]}')
    raise error

# END OF BANS
# ROLE-MODIFY AND REACT-ROLE COMMANDS

@bot.group()
@commands.bot_has_permissions(send_messages=True)
async def role(ctx):
    if ctx.invoked_subcommand is None:
        msg = (
            'D--> Usage of the role function: `role (subcommand) [args...]`\n\n'
            '`role list`: List all valid roles under their categories.\n'
            '`role add <role_name>`: Adds a specified role if valid.\n'
            '`role del <role_name>`: Removes a specified role if valid.\n'
            '{}'
            )
        if ctx.author.guild_permissions.manage_roles:
            await ctx.send(msg.format((
                '`role forcegrant <message_link> <emoji> <role>`: Add roles from a message manually.\n'
                '`role addreact <message_link> <emoji> <role>`: Add a role-bound reaction to a message to toggle a role.\n'
                '`role delreact <message_link> <emoji>`: Delete a role-bound reaction and associated data.\n'
                '`role addcategory <category> [<role_name1> <role_name2> ...]`: Add roles to a category.\n'
                '`role delcategory <category>`: Delete a category and related role data.\n'
                )))
        else:
            await ctx.send(msg.format(''))

@role.error
async def role_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return

@role.command(name='list')
@commands.bot_has_permissions(send_messages=True)
async def role_list(ctx, category: str):
    pass

@role_list.error
async def role_list_error(ctx, error):
    raise error

@role.command(name='add')
@commands.bot_has_permissions(send_messages=True)
async def role_add(ctx, role: dc.Role):
    pass

@role_add.error
async def role_add_error(ctx, error):
    raise error

@role.command(name='del')
@commands.bot_has_permissions(send_messages=True)
async def role_del(ctx, role: dc.Role):
    pass

@role_del.error
async def role_del_error(ctx, error):
    raise error

@role.command(name='forcegrant')
@commands.bot_has_permissions(
    send_messages=True, manage_messages=True, read_message_history=True,
    manage_roles=True,
    )
@commands.has_permissions(manage_roles=True)
async def role_forcegrant(ctx, msglink: str, emoji: EmojiUnion, role: dc.Role):
    # Force all who reacted with the specified emoji in the given message link to be granted a role.
    *_, chn_id, msg_id = msglink.split('/')
    try:
        msg = await ctx.guild.get_channel(int(chn_id)).fetch_message(int(msg_id))
    except dc.NotFound:
        await ctx.send('D--> It seems that I could not find the specified message.')
        return
    except dc.Forbidden:
        await ctx.send('D--> It seems you do not have permission required to get this message.')
        return
    except dc.HTTPException:
        await ctx.send('D--> We could not have predicted this tomfoolery. Try again.')
        return
    try:
        react = next(
            r for r in msg.reactions
            if type(emoji) is str and r.emoji == emoji
            or r.emoji.id == emoji.id
            )
    except StopIteration:
        await ctx.send('D--> It seems I could not find a matching reaction in that message.')
        return
    members = [m async for m in react.users() if m.id != bot.user.id]
    await process_role_grant(msg, react, role, members)
    await ctx.send('D--> Roles have been granted.')

@role_forcegrant.error
async def role_forcegrant_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send('D--> It seems you do not have permission to force role grants.')
        return
    elif isinstance(error, commands.RoleNotFound):
        await ctx.send('D--> It seems that the role could not be found.')
        return
    raise error

@role.command(name='addreact')
@commands.bot_has_permissions(
    send_messages=True, read_message_history=True, add_reactions=True
    )
@commands.has_permissions(manage_roles=True)
async def role_addreact(ctx, msglink: str, emoji: EmojiUnion, role: dc.Role):
    # Add a reaction to a message that will be attached to a toggleable role when reacted to.
    *_, chn_id, msg_id = msglink.split('/')
    try:
        msg = await ctx.guild.get_channel(int(chn_id)).fetch_message(int(msg_id))
    except dc.NotFound:
        await ctx.send('D--> It seems that I could not find the specified message.')
        return
    except dc.Forbidden:
        await ctx.send('D--> It seems you do not have permission required to get this message.')
        return
    except dc.HTTPException:
        await ctx.send('D--> We could not have predicted this tomfoolery. Try again.')
        return
    try:
        await msg.add_reaction(emoji)
    except dc.HTTPException:
        await ctx.send('D--> I was unable to react to the specified message. Please try again.')
        return
    roleplay.add_reaction(msg, emoji, role)
    await ctx.send(f'D--> Success. Reacting to this emoji will grant you the {role.name} role.')

@role_addreact.error
async def role_addreact_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send('D--> It seems you do not have permission to setup role reacts.')
        return
    elif isinstance(error, commands.RoleNotFound):
        await ctx.send('D--> It seems that the role could not be found.')
        return
    raise error

@role.command(name='delreact')
@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
@commands.has_permissions(manage_roles=True)
async def role_delreact(ctx, msglink: str, emoji: EmojiUnion):
    pass

@role_delreact.error
async def role_delreact_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send('D--> It seems you do not have permission to setup role reacts.')
        return
    raise error

@role.command('addcategory')
@commands.has_permissions(manage_roles=True)
async def role_addcategory(ctx, category: str, *roles):
    # I'm going full mONKE, no actually idk if serializing it is more efficient.
    converter = commands.RoleConverter().convert
    role_ids = []
    for role_text in roles:
        try:
            role = await converter(ctx, role_text)
        except commands.RoleNotFound:
            await ctx.send(f'D--> Role {role} not found.')
            continue
        role_ids.append(role.id)
    role_categories.add_category(ctx.guild, category, role_ids)
    await ctx.send(f'D--> Added the roles to category {category}.')
    
@role_addcategory.error
async def role_addcategory_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('D--> It seems you do not have permission to modify categories.')
        return
    raise error

@role.command('delcategory')
@commands.has_permissions(manage_roles=True)
async def role_delcategory(ctx, category: str):
    if role_categories.remove_category(ctx.guild, category):
        await ctx.send(f'D--> Removed category {category}.')
    else:
        await ctx.send(f'D--> Unable to remove category. Perhaps... it was never there?')

@role_delcategory.error
async def role_delcategory_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('D--> It seems you do not have permission to modify categories.')
        return
    raise error

# END OF ROLE COMMANDS
# JOJO's Bizarre Adventure Commands

@bot.group(name='ZA')
@user_or_perms(CONST_ADMINS, view_audit_log=True)
async def special_mod_command(ctx):
    if ctx.invoked_subcommand is None:
        pass

@special_mod_command.error
async def special_mod_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        return
    raise error
        
@special_mod_command.command(name='WARUDO')
@commands.bot_has_permissions(manage_roles=True)
async def special_mod_command_freeze(ctx):
    embed = dc.Embed(
        color=dc.Color(0xE4E951),
        timestamp=ctx.message.created_at,
        description=f'D--> The time is neigh; your foolish actions shall face STRONG '
        f'consequences, **#{ctx.channel}**! It is __***USELESS***__ to resist!'
        )
    embed.set_author(
        name='D--> 「ザ・ワールド」!!',
        icon_url='https://cdn.discordapp.com/attachments/'
        '663453347763716110/667117484612124694/DIOICON.png',
        )
    embed.set_image(
        url='https://cdn.discordapp.com/attachments/'
        '663453347763716110/667117771099734052/ZAWARUDO.gif'
        )
    await ctx.channel.send(embed=embed) # Order of operations is important
    await ctx.channel.set_permissions(
        ctx.guild.roles[0],
        overwrite=dc.PermissionOverwrite(send_messages=False)
        )

@special_mod_command_freeze.error
async def special_mod_command_freeze_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@special_mod_command.command(name='HANDO')
@commands.bot_has_permissions(manage_messages=True)
async def special_mod_command_purge(ctx):
    msgs = await ctx.channel.purge(limit=11)
    embed = dc.Embed(
        color=dc.Color(0x303EBB),
        timestamp=ctx.message.created_at,
        description=f'D--> I shall show you my magneighficent STRENGTH, **#{ctx.channel}**!'
        )
    embed.set_author(
        name='D--> 「ザ・ハンド」!!',
        icon_url='https://cdn.discordapp.com/attachments/'
        '663453347763716110/667117479910440976/OKUYASUICON.png',
        )
    embed.set_image(
        url='https://cdn.discordapp.com/attachments/'
        '663453347763716110/667117626128072714/ZAHANDO.gif'
        )
    await ctx.channel.send(embed=embed)
    if not guild_config.getlog(ctx.guild, 'msglog'): # Log immediately after.
        return
    user_msgs = {}
    for msg in msgs:
        if msg.author not in user_msgs:
            user_msgs[msg.author] = 0
        user_msgs[msg.author] += 1
    log_embed = dc.Embed(
        color=dc.Color.blue(),
        timestamp=ctx.message.created_at,
        description='\n'.join(
            f'**@{user}**: {count} messages' for user, count in user_msgs.items()
            ),
        )
    log_embed.set_author(
        name=f'{ctx.channel} has been purged:',
        icon_url='https://cdn.discordapp.com/attachments/'
        '663453347763716110/667117479910440976/OKUYASUICON.png',
        )
    await guild_config.log(ctx.guild, 'msglog', embed=log_embed)

@special_mod_command_purge.error
async def special_mod_command_purge_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command(name='time')
@commands.bot_has_permissions(manage_roles=True)
@user_or_perms(CONST_ADMINS, view_audit_log=True)
async def special_mod_command_unfreeze(ctx, *, args=''):
    if args == 'resumes':
        perms = ctx.channel.overwrites_for(ctx.guild.roles[0])
        if not perms.pair()[1].send_messages:
            return
        perms.update(send_messages=None)
        await ctx.channel.set_permissions(ctx.guild.roles[0], overwrite=perms)
        embed = dc.Embed(
            color=dc.Color(0xE4E951),
            timestamp=ctx.message.created_at,
            description=f'D--> Time has resumed in **#{ctx.channel}**.'
            )
        embed.set_author(
            name='D--> 時は動きです。',
            icon_url='https://cdn.discordapp.com/attachments/'
            '663453347763716110/667117484612124694/DIOICON.png',
            )
        await ctx.channel.send(embed=embed)

@special_mod_command_unfreeze.error
async def special_mod_command_unfreeze_error(ctx, error):
    if isinstance(error, (commands.MissingPermissions, commands.BotMissingPermissions)):
        return
    raise error

# <== To Be Continued...
# EXECUTE ORDER 66

@bot.command(name='execute')
@commands.bot_has_permissions(send_messages=True)
@commands.has_permissions(view_audit_log=True)
async def star_wars_punisher_activate(ctx, *, args=''):
    if args == 'order 66':
        guild_config.set_containment(ctx)
        await ctx.send('D--> It will be done, my lord.')
    else:
        await ctx.send(
            'D--> It seems you were not quite clear. Vocalize your desire STRONGLY.'
            )

@star_wars_punisher_activate.error
async def star_wars_punisher_activate_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            f'D--> Only the senate may execute this order, {ctx.author.name}.'
            )
        return
    elif isinstance(error, commands.BotMissingPermissions):
        return
    raise error

# END OF EXECUTE
# "TAG" COMMANDS

@bot.command(name='fle%')
@commands.bot_has_permissions(send_messages=True)
async def flex(ctx):
    await ctx.send(
        embed=dc.Embed(
            color=ctx.guild.get_member(bot.user.id).color,
            description='D--> It seems you have STRONGLY requested to gaze upon my beautiful body, '
            'and who am I to refuse such a request?'
            ).set_author(
            name='D--> I STRONGLY agree.', icon_url=bot.user.avatar_url
            ).set_image(
            url='https://cdn.discordapp.com/attachments/'
            '390337910244769792/704686351228076132/arquius_smooth.gif'
            ))

@flex.error
async def flex_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command(name='tag', aliases=['tc', 'tt'])
@commands.bot_has_permissions(send_messages=True)
async def deny_old_tags(ctx):
    await ctx.send(
        embed=dc.Embed(
            color=ctx.guild.get_member(bot.user.id).color,
            description='D--> I would never stoop so low as to entertain the likes of this. '
            'You are STRONGLY recommended to instead gaze upon my beautiful body.'
            ).set_author(
            name='D--> No.', icon_url=bot.user.avatar_url
            ).set_image(
            url='https://cdn.discordapp.com/attachments/'
            '152981670507577344/664624516370268191/arquius.gif'
            ))

@deny_old_tags.error
async def deny_old_tags_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command(name='husky', aliases=['fathusky', 'fatHusky'])
@commands.bot_has_permissions(send_messages=True)
async def post_fat_husky(ctx):
    await ctx.send(
        embed=dc.Embed(
            color=ctx.guild.get_member(bot.user.id).color,
            ).set_author(
            name='D--> A corpulent canine.', 
            icon_url='https://cdn.discordapp.com/attachments/'
            '663453347763716110/773577148577480754/unknown.png',
            ).set_image(
            url='https://cdn.discordapp.com/attachments/'
            '663453347763716110/773574707231457300/dogress.png',
            ))

@post_fat_husky.error
async def post_fat_husky_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

# END OF "TAG" COMMANDS
# STATS COMMANDS

@bot.group(name='stats')
@commands.has_permissions(manage_roles=True)
async def statistics_beta(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(
            'D--> It seems that you have attempted to run a nonexistent command.'
            'Would you like to try again? Redos are free, you know.'
            )

@statistics_beta.error
async def statistics_beta_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            f'D--> It seems that you don\'t have the appropriate permissions for this command. '
            f'I STRONGLY recommend you back off or get bucked off, {ctx.author.name}.'
            )
        return
    elif isinstance(error, commands.BotMissingPermissions):
        return
    raise error
        
@statistics_beta.command()
async def woc_counter(ctx): # Beta statistic feature: Woc's Tard Counter!
    if ctx.author.id == CONST_ADMINS[1]:
        await ctx.send(
            'D--> Are you sure you want to know that, Master Linky? '
            'Regardless of your answer, I shall tell you, though I STRONGLY suggest you wait.'
            )
    tards = await stats_tracker.take('woc_counter', ctx, None)
    if tards is not None:
        await ctx.send(
            f'D--> Wizard of Chaos has slurred {tards} times in this server, {ctx.author.mention}.'
            )

# END OF STATS
# MISCELLANEOUS UNGROUPED COMMANDS

@bot.command(name='ping', aliases=['p'])
@commands.bot_has_permissions(send_messages=True)
async def reflect_ping(ctx):
    await ctx.send(f'D--> {ctx.author.mention}')

@reflect_ping.error
async def reflect_ping_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command(name='roll', aliases=['r'])
@commands.bot_has_permissions(send_messages=True)
async def dice_roller(ctx, *, args):
    if not (match := re.match(r'(\d+)\s*d\s*(\d+)\s*(?:([-+])\s*(\d+))?$', args.strip())):
        await ctx.send('D--> Use your words, straight from the horse\'s mouth.')
        return
    ndice, nfaces, sign, mod = (group or '0' for group in match.groups())
    ndice, nfaces = int(ndice), int(nfaces)
    # Stop people from doing the 0 dice 0 faces bullshit
    if ndice <= 0 or nfaces <= 0:
        await ctx.send('D--> That doesn\'t math very well. I STRONGLY suggest you try again.')
        return
    modnum = int(sign + mod)
    # Precalc minimum length to see if roll should go
    if modnum:
        bfr = f'{ctx.author.mention} **rolled {ndice}d{nfaces}{sign}{mod}:** `('
        aft = f') {sign} {mod} = '
    else:
        bfr = f'{ctx.author.mention} **rolled {ndice}d{nfaces}:** `('
        aft = f') = '
    if len(bfr+aft) + 3*(ndice-1) > 2000:
        await ctx.send(
            'D--> Woah there pardner, that\'s a few too many dice '
            'or a few too large a die. Try again with something smaller.'
            )
        return
    # Do the rolls
    if ndice == nfaces == 8 and ctx.author.id == CONST_AUTHOR[0]:
        rolls = [8] * 8
    else:
        rolls = [randint(1, nfaces) for _ in range(ndice)]
    msg = f'{bfr}{" + ".join(map(str, rolls))}{aft}{sum(rolls) + modnum}`'
    if len(msg) > 2000:
        await ctx.send(
            'D--> Woah there pardner, that\'s a few too many dice '
            'or a few too large a die. Try again with something smaller.'
            )
        return
    embed = dc.Embed(
        color=dc.Color(0x005682),
        description=f'`Min: {min(rolls)}; Max: {max(rolls)}; '
            f'Mean: {sum(rolls) / ndice:0.2f}; 1st Mode: {max(set(rolls), key=rolls.count)}`',
        )
    embed.set_author(
        name='Roll Statistics:',
        icon_url='https://cdn.discordapp.com/attachments/'
            '663453347763716110/711985889680818266/unknown.png',
        )
    await ctx.send(msg, embed=embed)

@dice_roller.error
async def dice_roller_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

default_preamble = (
    r'\documentclass{standalone}\usepackage{color}\usepackage{amsmath}'
    r'\color{white}\begin{document}\begin{math}\displaystyle '
    )
default_postamble = r'\end{math}\end{document}'

@bot.command(name='latex', aliases=['l'])
@commands.bot_has_permissions(send_messages=True)
async def render_latex(ctx, *, raw_latex=''):
    if not guild_config.getltx(ctx) or not raw_latex:
        return
    with ctx.channel.typing():
        if (image := await grab_latex(default_preamble, default_postamble, raw_latex)) is None:
            await ctx.send('D--> Your latex code is beneighth contempt. Try again.')
            return
        # Send the image to the latex channel and embed.
        latex_channel = bot.get_channel(773594582175973376)
        msg_id = hex(member_stalker.member_data['latex_count'])[2:]
        member_stalker.member_data['latex_count'] += 1
        await latex_channel.send(
            f'`@{ctx.author}`: UID {ctx.author.id}: MID {msg_id}',
            file=dc.File(io.BytesIO(await image.read()), 'latex.png')
            )
        async for msg in latex_channel.history(limit=16):
            if msg.content.split()[-1] == msg_id:
                latex_image_url = msg.attachments[0].url
                break
        embed = dc.Embed(
            color=ctx.author.color,
            timestamp=datetime.utcnow(),
            )
        embed.set_author(
            name=f'D--> Latex render for {ctx.author}',
            icon_url='https://cdn.discordapp.com/attachments/'
            '663453347763716110/773600642752839700/stsmall507x507-pad600x600f8f8f8.png',
            )
        embed.set_image(url=latex_image_url)
        await ctx.send(embed=embed)
        await ctx.message.delete()

@render_latex.error
async def render_latex_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command(name='linky', aliases=['8ball'])
@commands.bot_has_permissions(send_messages=True)
async def magic_8ball(ctx, *, query=''):
    await aio.sleep(0)
    msg = re.sub(r'<@!(\d{18,})>', get_name, guild_config.random_linky(ctx.message.content))
    msg = re.sub(r'(?<!<)(https?://[^\s]+)(?!>)', r'<\1>', msg)
    admin = ctx.guild.get_member(CONST_ADMINS[1])
    embed = dc.Embed(
        color=admin.color if admin else dc.Color.green(),
        description=msg,
        )
    embed.set_author(
        name=f'{admin.name if admin else "Linky"} says:',
        icon_url=admin.avatar_url if admin else (
            'https://cdn.discordapp.com/attachments/'
            '663453347763716110/776420647625949214/Linky.gif'
            ),
        )
    await ctx.send(embed=embed)

@magic_8ball.error
async def magic_8ball_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command(name='suggest')
@commands.bot_has_permissions(send_messages=True)
async def suggest_to_dev(ctx, *, suggestion: str):
    suggestions = bot.get_channel(777555413213642772)
    suggest_id = ctx.message.id
    embed = dc.Embed(
        color=dc.Color.red(),
        description=suggestion,
        timestamp=datetime.utcnow(),
        )
    embed.set_author(
        name=f'{ctx.author} suggests:'
        )
    embed.add_field(
        name='**Message ID:**',
        value=f'`{suggest_id}`',
        inline=False,
        )
    await suggestions.send(embed=embed)
    await ctx.send(f'D--> Your suggestion has been noted.')
    stored_suggestions.add_suggestion(suggest_id, ctx.author.id, ctx.channel.id) 

@suggest_to_dev.error
async def suggest_to_dev_error(ctx, error):
    raise error

@bot.command(name='respond')
@commands.bot_has_permissions(send_messages=True)
async def response_from_dev(ctx, msg_id: int, *, response: str):
    if ctx.author.id not in CONST_AUTHOR:
        return
    try:
        channel, member = stored_suggestions.get_suggestion(bot, msg_id)
    except KeyError:
        await ctx.send('D--> Suggestion does not exist.')
        return
    async for msg in bot.get_channel(777555413213642772).history(limit=None):
        if msg.author.id != bot.user.id:
            continue
        if not msg.embeds:
            continue
        embed = msg.embeds[0]
        suggestion = embed.description
        if not embed.fields:
            continue
        if embed.fields[0].value == f'`{msg_id}`':
            break
    embed = dc.Embed(
        color=dc.Color.green(),
        description=response,
        timestamp=datetime.utcnow(),
        )
    embed.set_author(
        name='D--> In response to your suggestion, the devs say:',
        icon_url=bot.user.avatar_url,
        )
    embed.add_field(
        name='Suggestion:',
        value=suggestion,
        inline=False,
        )
    await channel.send(f'{member.mention}', embed=embed)
    stored_suggestions.remove_suggestion(msg_id)

@response_from_dev.error
async def response_from_dev_error(ctx, error):
    raise error

# END OF MISC COMMANDS
# MAIN

if __name__ == '__main__':
    with guild_config, member_stalker, roleplay, role_categories:
        bot.run(get_token())
