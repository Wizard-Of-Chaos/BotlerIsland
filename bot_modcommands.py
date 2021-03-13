# For most moderation commands.
from datetime import datetime
from collections import Counter

import asyncio as aio

import discord as dc
from discord.ext import commands

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot, CONST_ADMINS, CONST_AUTHOR, guild_config, stats_tracker

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

# INFOHELP COMMANDS

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
    if perms.manage_channels:
        embed.add_field(
            name='`config (msglog|usrlog|modlog)`',
            value='(Manage Channels only) Sets the appropriate log channel.',
            inline=False
            )
        embed.add_field(
            name='`ZA (WARUDO|HANDO)`',
            value='(Manage Channels Only) Utilizes highly dangerous Stand power to moderate the server.',
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
        await ctx.send(response_bank.perms_error)
        return
    elif isinstance(error, commands.BotMissingPermissions):
        return
    raise error

# END OF INFOHELP COMMANDS
# CONFIG COMMANDS

@bot.command()
@commands.bot_has_permissions(send_messages=True)
@commands.has_permissions(manage_channels=True)
async def config(ctx, log: str):
    await guild_config.setlog(ctx, log)

@config.error
async def config_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(response_bank.perms_error)
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
@commands.bot_has_permissions(send_messages=True)
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
@commands.bot_has_permissions(send_messages=True)
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

@bot.command()
@commands.bot_has_guild_permissions(ban_members=True)
@user_or_perms(CONST_ADMINS+CONST_AUTHOR, ban_members=True)
async def raidban(ctx, *args):
    if not args:
        return
    members = []
    for arg in args:
        member = await commands.UserConverter().convert(ctx, arg)
        members.append(f'`{member}`')
        await ctx.guild.ban(
            member,
            reason='Banned by anti-raid command.',
            delete_message_days=1,
            )
    desc = f'D--> The abbreants listed below have been STRONGLY executed:\n{", ".join(members)}'
    embed = dc.Embed(
        color=ctx.author.color,
        timestamp=ctx.message.created_at,
        # description=desc,
        )
    embed.set_author(
        name=f'{ctx.author} used raidban command in #{ctx.channel}:',
        icon_url=ctx.author.avatar_url,
        )
    await guild_config.log(ctx.guild, 'modlog', embed=embed, desc)
    await ctx.message.delete()
    if ctx.channel.id != guild_config.getlog('modlog'):
        await ctx.send(desc)

@raidban.error
async def raidban_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        channel = await ctx.author.create_dm()
        await channel.send(f'D--> {error.args[0]}')
    raise error

# END OF BANS
# JOJO's Bizarre Adventure Commands

@bot.group(name='ZA')
@user_or_perms(CONST_ADMINS, manage_channels=True)
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
        icon_url=url_bank.dio_icon,
        )
    embed.set_image(url=url_bank.za_warudo)
    await ctx.channel.send(embed=embed) # Order of operations is important
    perms = ctx.channel.overwrites_for(ctx.guild.roles[0])
    if perms.pair()[1].read_messages:
        return
    perms.update(send_messages=False)
    await ctx.channel.set_permissions(ctx.guild.roles[0], overwrite=perms)

@special_mod_command_freeze.error
async def special_mod_command_freeze_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@special_mod_command.command(name='HANDO')
@commands.bot_has_permissions(manage_messages=True)
async def special_mod_command_purge(ctx, limit: int=10):
    await ctx.message.delete()
    if limit < 1:
        await ctx.send('D--> You foolish creature.')
        return
    msgs = await ctx.channel.purge(limit=limit)
    embed = dc.Embed(
        color=dc.Color(0x303EBB),
        timestamp=ctx.message.created_at,
        description=f'D--> I shall show you my magneighficent STRENGTH, **#{ctx.channel}**!'
        )
    embed.set_author(
        name='D--> 「ザ・ハンド」!!',
        icon_url=url_bank.okuyasu_icon,
        )
    embed.set_image(url=url_bank.za_hando)
    await ctx.channel.send(embed=embed)
    if not guild_config.getlog(ctx.guild, 'msglog'): # Log immediately after.
        return
    user_msgs = Counter(msg.author for msg in msgs)
    log_embed = dc.Embed(
        color=dc.Color.blue(),
        timestamp=ctx.message.created_at,
        description='\n'.join(
            f'**@{user}**: {count} messages' for user, count in user_msgs.items()
            ),
        )
    log_embed.set_author(
        name=f'{ctx.channel} has been purged:',
        icon_url=url_bank.okuyasu_icon,
        )
    await guild_config.log(ctx.guild, 'msglog', embed=log_embed)

@special_mod_command_purge.error
async def special_mod_command_purge_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command(name='time')
@commands.bot_has_permissions(manage_roles=True)
@user_or_perms(CONST_ADMINS, manage_channels=True)
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
            icon_url=url_bank.dio_icon,
            )
        await ctx.channel.send(embed=embed)

@special_mod_command_unfreeze.error
async def special_mod_command_unfreeze_error(ctx, error):
    if isinstance(error, (commands.MissingPermissions, commands.BotMissingPermissions)):
        return
    raise error

# <== To Be Continued...
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
