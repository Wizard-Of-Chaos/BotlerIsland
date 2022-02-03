# For most moderation commands.
from datetime import datetime
from collections import Counter

import asyncio as aio
import discord as dc
from discord.ext import commands

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot, CONST_ADMINS, CONST_AUTHOR, user_or_perms

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
            value='(Manage Channels only) Utilizes highly dangerous Stand power to moderate the server.',
            inline=False
            )
    await ctx.send(embed=embed)

@modhelp.error
async def modhelp_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(response_bank.perms_error)
        return
    raise error
    
@bot.command()
@commands.has_guild_permissions(manage_roles=True)
@commands.bot_has_permissions(send_messages=True)
async def modperms(ctx):
    # me and the boys using cursed if as a prototype
    permlist = ', '.join(sorted(perm for perm, val in ctx.author.guild_permissions if val))
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
    desc = 'D--> The aberrants listed below have been STRONGLY executed:\n' + ', '.join(members)
    embed = dc.Embed(
        color=ctx.author.color,
        timestamp=ctx.message.created_at,
        )
    embed.set_author(
        name=f'{ctx.author} used raidban command in #{ctx.channel}:',
        icon_url=ctx.author.avatar_url,
        )
    if (guild_config := bot.get_cog('GuildConfiguration')) is None:
        raise RuntimeError(response_bank.unexpected_state)
    await guild_config.send_to_log_channel(ctx.guild, 'modlog', desc, embed=embed)
    await ctx.message.delete()
    if ctx.channel.id != guild_config.get_log_channel(ctx.guild, 'modlog'):
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
        description=response_bank.freeze_channel_desc.format(ctx=ctx),
        )
    embed.set_author(
        name=response_bank.freeze_channel_head,
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
        await ctx.send(response_bank.purge_channel_zero_arg_error)
        return
    msgs = await ctx.channel.purge(limit=limit)
    embed = dc.Embed(
        color=dc.Color(0x303EBB),
        timestamp=ctx.message.created_at,
        description=response_bank.purge_channel_desc.format(ctx=ctx),
        )
    embed.set_author(
        name=response_bank.purge_channel_head,
        icon_url=url_bank.okuyasu_icon,
        )
    embed.set_image(url=url_bank.za_hando)
    await ctx.channel.send(embed=embed)
    guild_config = bot.get_cog('GuildConfiguration')
    if guild_config is None:
        raise RuntimeError(response_bank.unexpected_state)
    if not guild_config.get_log_channel(ctx.guild, 'msglog'): # Log immediately after.
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
    await guild_config.send_to_log_channel(ctx.guild, 'msglog', embed=log_embed)

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
            description=response_bank.unfreeze_channel_desc.format(ctx=ctx),
            )
        embed.set_author(
            name=response_bank.unfreeze_channel_head,
            icon_url=url_bank.dio_icon,
            )
        await ctx.channel.send(embed=embed)

@special_mod_command_unfreeze.error
async def special_mod_command_unfreeze_error(ctx, error):
    if isinstance(error, (commands.MissingPermissions, commands.BotMissingPermissions)):
        return
    raise error

# <== To Be Continued...
