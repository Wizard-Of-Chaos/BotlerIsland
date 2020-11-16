from datetime import datetime

import discord as dc
from discord.ext import commands

from cogs_textbanks import query_bank, response_bank
from cogs_dailycounts import post_dailies, daily_usr, daily_msg
from bot_common import (
    bot, guild_whitelist, CONST_ADMINS, CONST_AUTHOR,
    guild_config, member_stalker, emoji_roles,
    process_role_grant,
    )

image_exts = ('png', 'gif', 'jpg', 'jpeg', 'jpe', 'jfif')

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

@bot.event
async def on_ready(): # Bot starts
    print(response_bank.bot_startup.format(version='1.3.0'))
    for guild in bot.guilds:
        if guild.id not in guild_whitelist:
            await guild.leave()
    print(response_bank.verify_whitelist_complete)
    await bot.change_presence(
        activity=dc.Game(name=response_bank.online_status)
        )
    post_dailies.start()
    print(response_bank.tasks_started)
    print(response_bank.process_reacts)
    # This is a horrible fucking way of granting all the pending roles. Too bad!
    for chn_id, msg_dict in emoji_roles:
        channel = bot.get_channel(chn_id)
        for msg_id, emoji_dict in msg_dict.items():
            try:
                msg = await channel.fetch_message(msg_id)
            except dc.NotFound: # This message entry will be cleared when the bot closes.
                emoji_dict.clear()
                continue
            for react in msg.reactions:
                if (emoji_id := emoji_roles.get_react_id(react)) in emoji_dict:
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
    elif guild_config.getcmd(ctx) and msg.content.strip().lower() in query_bank.affirmation:
        await msg.channel.send(response_bank.affirmation_response)
    elif (msg.channel.id in guild_config.getlog(msg.guild, 'autoreact')
        and any(any(map(att.url.lower().endswith, image_exts)) for att in msg.attachments)
        ):
        await msg.add_reaction('❤️')
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
    emoji_roles.remove_message(msg)
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
    if react_map := emoji_roles.get_reactmap(chn_id, msg_id):
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
    if react_map := emoji_roles.get_reactmap(chn_id, msg_id):
        # Find the reaction with matching emoji, then prune all further reacts.
        msg = await guild.get_channel(chn_id).fetch_message(msg_id)
        emoji_roles.remove_reaction(msg, emoji)
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
    if react_map := emoji_roles.get_reactmap(chn_id, msg_id):
        # Find the reaction with matching emoji, then prune all further reacts.
        msg = await guild.get_channel(chn_id).fetch_message(msg_id)
        emoji_roles.remove_reaction(msg, emoji)

@bot.event
async def on_raw_reaction_clear(payload): # All reacts cleared from message
    # If all reacts from a message are removed, remove associated data if it exists.
    if (guild := bot.get_guild(payload.guild_id)) is None:
        return
    emoji_roles.remove_message(
        await guild.get_channel(payload.channel_id).fetch_message(payload.message_id)
        )