#!/usr/bin/env python
# HSDBot code by Wizard of Chaos#2459 and virtuNat#7998
import re
from datetime import datetime, timedelta
from random import randint
from collections import Counter
import asyncio as aio
import discord as dc
from discord.ext import commands, tasks
from modtools import guild_whitelist, GuildConfig, MemberStalker
from statstracker import StatsTracker

bot = commands.Bot(command_prefix='D--> ')
bot.remove_command('help')
guild_config = GuildConfig(bot, 'config.pkl')
member_stalker = MemberStalker('members.pkl')
stats_tracker = StatsTracker('stats.pkl')
stats_tracker.locked_msg = (
    'D--> It seems that I am currently in the middle of something. '
    'I STRONGLY suggest that you wait for me to finish.'
    )

daily_msg = {guild_id: Counter() for guild_id in guild_whitelist}
daily_usr = {guild_id: Counter({'join': 0, 'leave': 0}) for guild_id in guild_whitelist}

image_exts = ('png', 'gif', 'jpg', 'jpeg', 'jpe', 'jfif')
CONST_BAD_ID = 148346796186271744 # You-know-who
CONST_MOTHER = 257144766901256192
CONST_FATHER = 125433170047795200

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
    msg_id = hex(member_stalker.member_data['count'])[2:]
    member_stalker.member_data['count'] += 1
    with open('avatar.png', mode='rb') as avatarfile:
        await avy_channel.send(
            f'`@{user}`: UID {user.id}: MID {msg_id}',
            file=dc.File(avatarfile)
            )
    async for msg in avy_channel.history(limit=16):
        if msg.content.split()[-1] == msg_id:
            return msg.attachments[0].url

#END OF FUNCTIONS
#TASKS

@tasks.loop(hours=24)
async def post_dailies():
    for guild_id, admin_id in zip(guild_whitelist, (CONST_BAD_ID, CONST_MOTHER)):
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
        await guild_config.log(guild, 'modlog', admin.mention, embed=embed)

@post_dailies.before_loop
async def start_timer():
    now = datetime.utcnow()
    await aio.sleep(
        (datetime.combine(now.date() + timedelta(1), datetime.min.time()) - now).seconds
        )

#END OF TASKS
#EVENTS

@bot.event
async def on_ready():
    for guild in bot.guilds:
        if guild.id not in guild_whitelist:
            await guild.leave()
    await bot.change_presence(
        activity=dc.Game(name='D--> A beautiful stallion.')
        )
    post_dailies.start()
    print('D--> At your command.\n')

@bot.event
async def on_guild_join(guild):
    if guild.id not in guild_whitelist:
        await guild.leave()

@bot.event
async def on_message(msg):
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
    elif ctx.author.id == CONST_BAD_ID:
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
async def on_voice_state_update(member, bfr, aft): # Logged when a member joins and leaves VC
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

# END OF EVENTS
# EXECUTE ORDER 66

@bot.command()
@commands.bot_has_permissions(send_messages=True)
@commands.has_permissions(view_audit_log=True)
async def execute(ctx, *, args=None):
    if args == 'order 66':
        guild_config.set_containment(ctx)
        await ctx.send('D--> It will be done, my lord.')
    else:
        await ctx.send(
            'D--> It seems you were not quite clear. Vocalize your desire STRONGLY.'
            )

@execute.error
async def execute_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            f'D--> Only the senate may execute this order, {ctx.author.name}.'
            )
        return
    elif isinstance(error, commands.BotMissingPermissions):
        return
    raise error

# END OF EXECUTE
# CONFIG COMMANDS

@bot.command()
@commands.bot_has_permissions(send_messages=True)
@commands.has_permissions(view_audit_log=True)
async def config(ctx, log):
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
# STATS COMMANDS

@bot.group()
@commands.has_permissions(manage_roles=True)
async def stats(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(
            'D--> It seems that you have attempted to run a nonexistent command.'
            'Would you like to try again? Redos are free, you know.'
            )

@stats.error
async def stats_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            f'D--> It seems that you don\'t have the appropriate permissions for this command. '
            f'I STRONGLY recommend you back off or get bucked off, {ctx.author.name}.'
            )
        return
    elif isinstance(error, commands.BotMissingPermissions):
        return
    raise error
        
@stats.command()
async def woc_counter(ctx): # Beta statistic feature: Woc's Tard Counter!
    if ctx.author.id == CONST_BAD_ID:
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
# JOJO's Bizarre Adventure Commands

def user_or_perms(**perms):
    perm_check = commands.has_permissions(**perms).predicate
    async def extended_check(ctx):
        if ctx.guild is None:
            return False
        return ctx.author.id == 120187484863856640 or await perm_check(ctx)
    return commands.check(extended_check)

@bot.group(name='ZA')
@user_or_perms(view_audit_log=True)
async def moderate(ctx):
    if ctx.invoked_subcommand is None:
        pass

@moderate.error
async def moderate_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        return
    raise error
        
@moderate.command(name='WARUDO')
@commands.bot_has_permissions(manage_roles=True)
async def freeze(ctx):
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

@freeze.error
async def freeze_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@moderate.command(name='HANDO')
@commands.bot_has_permissions(manage_messages=True)
async def purge(ctx):
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

@purge.error
async def purge_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.group()
@user_or_perms(manage_roles=True)
@commands.has_permissions(view_audit_log=True)
async def time(ctx):
    if ctx.invoked_subcommand is None:
        pass

@time.error
async def time_error(ctx, error):
    if isinstance(error, (commands.MissingPermissions, commands.BotMissingPermissions)):
        return
    raise error

@time.command()
async def resumes(ctx):
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

# <== To Be Continued...
# BAN COMMANDS

# ALRIGHT HUNGOVER WIZARD OF CHAOS CODE IN THE HIZ-OUSE
# WE GONNA WRITE SOME MOTHERFUCKING BAN COMMANDS; INITIALIZE THAT SHIT
@bot.group()
@commands.has_guild_permissions(manage_roles=True)
async def channel(ctx):
    if ctx.invoked_subcommand is None:
        pass

@channel.error
async def channel_error(ctx, error):
    if isinstance(error, (commands.MissingPermissions, commands.BotMissingPermissions)):
        return
    raise error

@channel.command()
async def ban(ctx, member: dc.Member, *, duration=None):
    if not member: # WE'RE GRABBING A MEMBER WE GIVE NO SHITS
        return
    # WE'RE GONNA FIND THE FIRST FUCKING ROLE THAT HAS NO PERMS IN THIS CHANNEL
    # AND GUESS HOW WE DO THAT? THAT'S RIGHT, CURSED IF STATEMENT
    for role in ctx.guild.roles:
        if ctx.channel.overwrites_for(role).pair()[1].send_messages: # BOOM LOOK AT THAT SHIT SUCK MY DICK
            await member.add_roles(role)
            # OH BUT NOW SOMEONES GONNA WHINE THAT WE DIDNT LOG IT? HOLD YOUR ASS TIGHT BECAUSE WE'RE ABOUT TO
            if guild_config.getlog(ctx.guild, 'modlog'): # OHHHHHHH! HE DID IT! THE FUCKING MADMAN!
                embed = dc.Embed(
                    color=ctx.author.color,
                    timestamp=ctx.message.created_at,
                    description=f'{member.mention} has been banned in **#{ctx.channel}**'
                    )
                embed.add_field(name='**Role Granted:**', value=f'`{role}`')
                embed.add_field(name='**Duration/Reason:**', value=duration or 'None specified')
                embed.add_field(name='**User ID:**', value=member.id, inline=False)
                embed.set_author(
                    name=f'@{ctx.author} Issued Channel Ban:',
                    icon_url=ctx.author.avatar_url,
                    )
                await guild_config.log(ctx.guild, 'modlog', embed=embed)
            return
            # BOOM! SUUUUUUUUCK - IT!

@ban.error
async def ban_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        channel = await ctx.author.create_dm()
        await channel.send(f'D--> {error.args[0]}.')

@channel.command()
async def unban(ctx, *, member: dc.Member):
    if not member:
        return
    for role in member.roles:
        if ctx.channel.overwrites_for(role).pair()[1].send_messages:
            await member.remove_roles(role)
            if guild_config.getlog(ctx.guild, 'modlog'):
                embed = dc.Embed(
                    color=ctx.author.color,
                    timestamp=ctx.message.created_at,
                    description=f'{member.mention} has been unbanned in **#{ctx.channel}**'
                    )
                embed.add_field(name='**Role Revoked:**', value=f'`{role}`')
                embed.add_field(name='**User ID:**', value=member.id)
                embed.set_author(
                    name=f'@{ctx.author} Issued Channel Unban:',
                    icon_url=ctx.author.avatar_url,
                    )
                await guild_config.log(ctx.guild, 'modlog', embed=embed)
                return

@unban.error
async def unban_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        channel = await ctx.author.create_dm()
        await channel.send(f'D--> {error.args[0]}.')

@bot.command()
@commands.bot_has_guild_permissions(ban_members=True)
@commands.has_guild_permissions(ban_members=True)
async def raidban(ctx, *args):
    banned = []
    for arg in args:
        member = await commands.UserConverter().convert(ctx, arg)
        await ctx.guild.ban(member, reason='Raid banned', delete_message_days=1)
        banned.append(f'`{member.id}`')
    banned = ',\n'.join(banned)
    if guild_config.getlog(ctx.guild, 'modlog'):
        embed = dc.Embed(
            color=ctx.author.color,
            timestamp=ctx.message.created_at,
            description=f'Raiders demolished in **#{ctx.channel}**:\n{banned}'
            )
        embed.set_author(
            name=f'@{ctx.author} Issued Raid Ban(s):',
            icon_url=ctx.author.avatar_url,
            )
        await guild_config.log(ctx.guild, 'modlog', embed=embed)

@raidban.error
async def raidban_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        channel = await ctx.author.create_dm()
        await channel.send(f'D--> {error.args[0]}.')

# END OF BANS
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

@bot.command(aliases=['tc', 'tt'])
@commands.bot_has_permissions(send_messages=True)
async def tag(ctx):
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

@tag.error
async def tag_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

# END OF "TAG"S
# UNGROUPED COMMANDS
        
@bot.command(name='help')
@commands.bot_has_permissions(send_messages=True)
async def _help(ctx):
    perms = ctx.author.guild_permissions
    embed = dc.Embed(
        color=ctx.author.color,
        timestamp=ctx.message.created_at,
        description=f'D--> It seems you have asked about the *Homestuck and Hiveswap Discord Utility Bot*:tm:.'
        f'This is a bot designed to cater to the server\'s moderation, utility, and statistic '
        f'tracking needs. If the functions herein described are not performing to the degree '
        f'that is claimed, please direct your attention to **Wizard of Chaos#2459** or **virtuNat#7998**.\n\n'
        f'**Command List:**',
        )
    embed.set_author(name='Help message', icon_url=bot.user.avatar_url)
    embed.add_field(name='`help`', value='Display this message.', inline=False)
    embed.add_field(
        name='`info [user]`',
        value='Grabs user information. Leave user field empty to get your own info.',
        inline=False
        )
    embed.add_field(name='`ping`', value='Pings the user.', inline=False)
    embed.add_field(name='`fle%`', value='Provides you with STRONG eye candy.', inline=False)
    embed.add_field(
        name='`roll <n>d<f>[(+|-)<m>]`',
        value='Try your luck! Roll n f-faced dice, and maybe add a modifier m!',
        inline=False
        )
    embed.add_field(name='`linky`', value=':drewkas:', inline=False)
    await ctx.send(embed=embed)

@_help.error
async def help_error(ctx, error):
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
        name='`daily`',
        value='(Manage Roles only) Show server daily counts.',
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
@commands.bot_has_permissions(send_messages=True)
async def ping(ctx):
    await ctx.send(f'D--> {ctx.message.author.mention}')

@ping.error
async def ping_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command()
@commands.bot_has_permissions(send_messages=True)
async def roll(ctx, *, args):
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
    if ndice == nfaces == 8 and ctx.author.id == CONST_FATHER:
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
    # embed = dc.Embed(
    #     color=dc.Color(0x005682),
    #     description=f'`Min: {min(rolls)}; Max: {max(rolls)}; '
    #         f'Mean: {sum(rolls) / ndice:0.2f}; 1st Mode: {max(set(rolls), key=rolls.count)}`',
    #     )
    # embed.set_author(
    #     name='Roll Statistics:',
    #     icon_url='https://cdn.discordapp.com/attachments/'
    #         '663453347763716110/711985889680818266/unknown.png',
    #     )
    await ctx.send(msg)#, embed=embed)

@ping.error
async def roll_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command()
@commands.bot_has_permissions(send_messages=True)
async def latex(ctx, latex):
    await ctx.send('D--> Coming soon.')

@latex.error
async def latex_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command()
@commands.bot_has_permissions(send_messages=True)
async def linky(ctx):
    msg = re.sub(r'<@!(\d{18,})>', get_name, guild_config.random_linky())
    msg = re.sub(r'(?<!<)(https?://[^\s]+)(?!>)', r'<\1>', msg)
    admin = ctx.guild.get_member(CONST_BAD_ID)
    if admin is None:
        admin = ctx.guild.get_member(CONST_FATHER)
    embed = dc.Embed(
        color=admin.color,
        description=msg,
        )
    embed.set_author(name=f'{admin.name} says:', icon_url=admin.avatar_url)
    await ctx.send(embed=embed)

@linky.error
async def linky_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command()
@commands.has_guild_permissions(manage_roles=True)
async def daily(ctx):
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

@daily.error
async def daily_error(ctx, error):
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
    
#TOGGLE COMMANDS
@bot.command()
@commands.bot_has_permissions(add_reactions=True, read_message_history=True)
@commands.has_guild_permissions(manage_roles=True)
async def autoreact(ctx):
    if guild_config.toggle_reacts(ctx):
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
    if guild_config.toggle_cmd(ctx):
        await ctx.send('D--> I shall listen only to b100 b100ded commands.')
    else:
        await ctx.send('D--> Unfortunately, I must now listen to the lower classes.')

@ignoreplebs.error
async def ignoreplebs_error(ctx, error):
    if isinstance(error, MissingPermissions):
        await ctx.send('D--> Neigh, plebian.')
        return
    raise error
#END OF TOGGLE COMMANDS

if __name__ == '__main__':
    try:
        bot.run(get_token())
    except BaseException:
        raise
    finally:
        guild_config.save()
        member_stalker.save()
