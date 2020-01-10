#!/usr/bin/env python
# HSDBot code by Wizard of Chaos#2459 and virtuNat#7998
from datetime import datetime
from operator import attrgetter
import asyncio as aio
import discord as dc
from discord.ext import commands
from guildconfig import GuildConfig
from rolesaver import RoleSaver
from memberstalker import MemberStalker

bot = commands.Bot(command_prefix='D--> ')
bot.remove_command('help')
guild_config = GuildConfig(bot, 'config.pkl')
role_saver = RoleSaver('roles.pkl')
member_stalker = MemberStalker('times.pkl')

CONST_BAD_ID = 148346796186271744 # You-know-who


#FUNCTIONS

def get_token():
    with open('token.dat', 'r') as tokenfile:
        return ''.join(
            chr(int(''.join(c), 16))
            for c in zip(*[iter(tokenfile.read().strip())]*2)
            )

async def grab_avatar(user):
    avy_channel = bot.get_channel(664541525350547496)
    with open('avatar.png', mode='wb') as avatarfile:
        try:
            await user.avatar_url.save(avatarfile)
        except dc.errors.NotFound:
            return (
                'https://cdn.discordapp.com/attachments/'
                '663453347763716110/664578577479761920/unknown.png'
                )
    with open('avatar.png', mode='rb') as avatarfile:
        await avy_channel.send(file=dc.File(avatarfile))
    async for msg in avy_channel.history(limit=1):
        return msg.attachments[0].url

async def find_member(guild, name):
    name = name.strip()
    for predicate in (str, attrgetter('name'), attrgetter('nick')):
        for member in guild.members:
            if predicate(member) == name:
                break
        else:
            await aio.sleep(0)
            continue
        return member
    return None

#END OF FUNCTIONS
#EVENTS

@bot.event
async def on_ready():
    print('D--> At your command.')
    
@bot.event
async def on_message(msg):
    member_stalker.update(msg)
    if msg.author.id == 167131099456208898:
        return
    if msg.content == 'good work arquius':
        await msg.channel.send('D--> :sunglasses:')
    else:
        await bot.process_commands(msg)

@bot.event
async def on_message_edit(bfr, aft):
    if bfr.author == bot.user:
        return
    if bfr.content == aft.content:
        return
    guild = bfr.guild
    if guild_config.getlog(guild, 'msglog'):
        embed = dc.Embed(color=dc.Color.gold(), timestamp=aft.created_at)
        embed.set_author(
            name=f'@{bfr.author} edited a message in #{bfr.channel}:',
            icon_url=bfr.author.avatar_url,
            )
        embed.add_field(name='**Before:**', value=bfr.content, inline=False)
        embed.add_field(name='**After:**', value=aft.content, inline=False)
        embed.add_field(name='**Message ID:**', value=f'`{aft.id}`')
        embed.add_field(name='**User ID:**', value=f'`{bfr.author.id}`')
        await guild_config.log(guild, 'msglog', embed=embed)

@bot.event
async def on_message_delete(msg):
    if msg.guild is None:
        return
    guild = msg.channel.guild
    if guild_config.getlog(guild, 'msglog'):
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
        embed.add_field(
            name='**Attachments:**',
            value='\n'.join(att.url for att in msg.attachments) or None,
            inline=False,
            )
        await guild_config.log(guild, 'msglog', embed=embed)
            
@bot.event
async def on_member_join(member):
    guild = member.guild 
    if guild_config.getlog(guild, 'usrlog'):
        await role_saver.load_roles(member)
        embed = dc.Embed(
            color=dc.Color.green(),
            timestamp=datetime.utcnow(),
            description=f':green_circle: {member.mention} : ``{member}`` has joined **{guild}**!\n'
            f'The guild now has {guild.member_count} members!\n'
            f'This account was created on `{member.created_at.strftime("%d/%m/%Y %H:%M:%S")}`'
            )
        embed.set_author(name=f'A user has joined the server!')
        embed.set_thumbnail(url=member.avatar_url)
        embed.add_field(name='**User ID**', value=f'`{member.id}`')
        await guild_config.log(guild, 'usrlog', embed=embed)

@bot.event
async def on_member_remove(member):
    guild = member.guild
    if guild_config.getlog(guild, 'usrlog'):
        role_saver.save_roles(member)
        lastseen = member_stalker.get(member)
        if lastseen is not None:
            lastseenmsg = f'This user was last seen on `{lastseen.strftime("%d/%m/%Y %H:%M:%S")}`'
        else:
            lastseenmsg = 'This user has not spoken to my knowledge!'
        embed = dc.Embed(
            color=dc.Color.red(),
            timestamp=datetime.utcnow(),
            description=f':red_circle: **{member}** has left **{guild}**!\n'
            f'The guild now has {guild.member_count} members!\n{lastseenmsg}'
            )
        embed.set_author(name=f'A user left or got beaned!')
        embed.set_thumbnail(url=member.avatar_url)
        embed.add_field(
            name='**Roles Snagged:**',
            value=(', '.join(
                    f'`{guild.get_role(role).name}`'
                    for role in role_saver.get_roles(member)
                    )
                or None),
            inline=False)
        embed.add_field(name='**User ID:**', value=f'`{member.id}`')
        await guild_config.log(guild, 'usrlog', embed=embed)

@bot.event
async def on_member_update(bfr, aft): # Log role and nickname changes
    guild = bfr.guild
    if guild_config.getlog(guild, 'msglog'):
        changetype = None
        if bfr.nick != aft.nick:
            embed = dc.Embed(
                color=dc.Color.blue(),
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
        if guild_config.getlog(guild, 'msglog') and guild.get_member(bfr.id):
            changetype = None
            if bfr.name != aft.name:
                changetype = 'Username Update:'
                changelog = (
                    f'**Old Username:** {bfr}\n'
                    f'**New Username:** {aft}'
                    )
            if bfr.discriminator != aft.discriminator:
                changetype = 'Discriminator Update:'
                changelog = (
                    f'{bfr} had their discriminator changed from '
                    f'{bfr.discriminator} to {aft.discriminator}'
                    )
            if bfr.avatar != aft.avatar:
                changetype = 'Avatar Update:'
                changelog = f'{bfr} has changed their avatar to:'
            if changetype is not None:
                embed = dc.Embed(
                    color=dc.Color.purple(),
                    timestamp=datetime.utcnow(),
                    description=changelog,
                    )
                if changetype.startswith('Avatar'):
                    embed.set_thumbnail(url=f'{aft.avatar_url}')
                    embed.set_author(name=changetype, icon_url=await grab_avatar(bfr))
                else:
                    embed.set_author(name=changetype, icon_url=aft.avatar_url)
                embed.add_field(name='**User ID:**', value=f'`{aft.id}`', inline=False)
                await guild_config.log(guild, 'msglog', embed=embed)
                    
@bot.event
async def on_voice_state_update(member, bfr, aft): #Logged when a member joins and leaves VC
    guild = member.guild
    if guild_config.getlog(guild, 'msglog'):
        changelog = None
        if bfr.channel != aft.channel:
            if bfr.channel == None:
                changelog = f':loud_sound: **{member}** has joined **{aft.channel}**'
            elif aft.channel == None:
                changelog = f':loud_sound: **{member}** has left **{bfr.channel}**'
        if changelog is not None: 
            embed = dc.Embed(color=dc.Color.blurple(), description=changelog)
            await guild_config.log(guild, 'msglog', embed=embed)

#END OF EVENTS
#CONFIG COMMANDS

@bot.group()
async def config(ctx):
    try:
        if ctx.invoked_subcommand is None:
            await ctx.send(
                'D--> It seems that you have attempted to run a nonexistent command. '
                'Would you like to try again? Redos are free, you know.'
                )
    except dc.Forbidden:
        pass

@config.command()
async def usrlog(ctx):
    if ctx.author.guild_permissions.manage_guild == True:
        await ctx.send(guild_config.setlog(ctx, 'usrlog'))
    else:
        await ctx.send(
            'D--> It seems that you don\'t have the appropriate permissions for this command. '
            'I STRONGLY recommend you back off or get bucked off.'
            )
        
@config.command()
async def msglog(ctx):
    try:
        if ctx.author.guild_permissions.manage_guild == True:
            await ctx.send(guild_config.setlog(ctx, 'msglog'))
        else:
            await ctx.send(
                'D--> It seems that you don\'t have the appropriate permissions for this command. '
                'I STRONGLY recommend you back off or get bucked off.'
                )
    except dc.Forbidden:
        pass

#END OF CONFIG
#STATS COMMANDS

@bot.group()
async def stats(ctx):
    try:
        if ctx.invoked_subcommand is None:
            await ctx.send(
                'D--> It seems that you have attempted to run a nonexistent command.'
                'Woudl you like to try again? Redos are free, you know.'
                )
    except dc.Forbidden:
        pass
        
@stats.command()
async def woc_counter(ctx):
    try:
        woc_id = 125433170047795200
        if ctx.author.id == woc_id:
            guild = ctx.guild
            tards = 0
            for channel in ctx.guild.text_channels:
                msgs = await channel.history().flatten()
                for msg in msgs:
                    if msg.author.id == woc_id and 'retard' in msg.content:
                        tards += 1
            await ctx.send(
                f'D--> Wizard of Chaos has slurred {tards} times in this server.'
                )
        else:
            await ctx.send(
                'D--> It seems you are not the appropriate user for this command.'
                )
                
    except dc.Forbidden:
        pass

#END OF STATS
#UNGROUPED COMMANDS
        
@bot.command()
async def help(ctx):
    try:
        embed = dc.Embed(
            color=ctx.author.color,
            timestamp=ctx.message.created_at,
            description=f'D--> It seems you have asked about the Homestuck and Hiveswap Discord Utility Bot:tm:.'
            f'This is a bot designed to cater to the server\'s moderation, utility, and statistic '
            f'tracking needs. If the functions herein described are not performing to the degree '
            f'that is claimed, please direct your attention to Wizard of Chaos#2459.\n\n'
            f'**Command List:**',
            )
        embed.set_author(name='Help message', icon_url=bot.user.avatar_url)
        embed.add_field(name='`help`', value='Display this message.', inline=False)
        embed.add_field(
            name='`info [username]`',
            value='Grabs user information. Leave username empty to get your own info.',
            inline=False
            )
        embed.add_field(name='`ping`', value='Pong!', inline=False)
        embed.add_field(
            name='`config (msglog|usrlog)`',
            value='(Manage Server only) Sets the appropriate log channel.',
            inline=False
            )
        await ctx.send(embed=embed)
    except dc.Forbidden:
        pass

@bot.command()
async def info(ctx, *, name=None):
    try:
        if name is None:
            member = ctx.author
        else:
            member = await find_member(ctx.guild, name)
            if member is None:
                await ctx.send('D--> It seems that user can\'t be found. Please check your spelling.')
                return
        lastseen = member_stalker.get(member)
        if lastseen is not None:
            lastseenmsg = f'This user was last seen on `{lastseen.strftime("%d/%m/%Y %H:%M:%S")}`'
        else:
            lastseenmsg = 'This user has not spoken to my knowledge!'
        embed = dc.Embed(color=member.color, timestamp=datetime.utcnow())
        embed.set_author(name=f'Information for {member}')
        embed.set_thumbnail(url=member.avatar_url)
        embed.add_field(name='User ID:', value=f'`{member.id}`')
        embed.add_field(name='Last Seen:', value=lastseenmsg, inline=False)
        embed.add_field(name='Account Created On:', value=member.created_at.strftime('%d/%m/%Y %H:%M:%S'))
        embed.add_field(name='Guild Joined On:', value=member.joined_at.strftime('%d/%m/%Y %H:%M:%S'))
        embed.add_field(name='Roles:', value=', '.join(f'`{role.name}`' for role in member.roles[1:]), inline=False)
        if bot.user == member:
            msg = 'D--> Do you wish to check out my STRONG muscles?'
        elif ctx.author != member:
            msg = 'D--> It seems you\'re a bit of a stalker, aren\'t you?'
        else:
            msg = 'D--> I understand the need to look at yourself in the mirror.'
        await ctx.send(msg, embed=embed)
    except dc.Forbidden:
        pass

@bot.command()
async def ping(ctx):
    try:
        await ctx.send(f'Pong, <@!{ctx.message.author.id}>!')
    except dc.Forbidden:
        pass
async def tag(ctx):
    try:
        denial = dc.Embed(
            color=dc.Color(0xFF0000),
            description='D--> I would never stoop so low as to entertain the likes of this. '
            'You are STRONGLY recommended to instead gaze upon my beautiful body.'
            )
        denial.set_author(name='D--> No.', icon_url=bot.user.avatar_url)
        denial.set_image(
            url='https://cdn.discordapp.com/attachments/'
            '152981670507577344/664624516370268191/arquius.gif'
            )
        await ctx.send(embed=denial)
    except dc.Forbidden:
        pass

bot.command(name='tag')(tag)
bot.command(name='tc')(tag)
bot.command(name='tt')(tag)

if __name__ == '__main__':
    try:
        bot.run(get_token())
    except BaseException:
        raise
    finally:
        member_stalker.save()
