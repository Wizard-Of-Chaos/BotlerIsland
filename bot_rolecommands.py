# The role command and all subcommands.
from typing import Union

import discord as dc
from discord.ext import commands

from cogs_textbanks import query_bank, response_bank
from bot_common import bot, emoji_roles, role_categories, process_role_grant

EmojiUnion = Union[dc.Emoji, dc.PartialEmoji, str]

@bot.group()
@commands.bot_has_permissions(send_messages=True)
async def role(ctx):
    if ctx.invoked_subcommand is None:
        if ctx.author.guild_permissions.manage_roles:
            await ctx.send(
                response_bank.role_usage_format.format(
                    response_bank.role_usage_extension
                    )
                )
        else:
            await ctx.send(response_bank.role_usage_format.format(''))

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
    if not await role_categories.purge_category(role, ctx.author):
        await ctx.send('D--> You are not allowed to self-assign this role.')
        return
    await ctx.author.add_roles(role)
    await ctx.send(f'D--> The role {role} has been granted.')

@role_add.error
async def role_add_error(ctx, error):
    if isinstance(error, commands.RoleNotFound):
        await ctx.send(response_bank.role_error)
        return
    raise error

@role.command(name='del')
@commands.bot_has_permissions(send_messages=True)
async def role_del(ctx, role: dc.Role):
    if role not in ctx.author.roles:
        await ctx.send('D--> You do not have this role.')
        return
    if not await role_categories.purge_category(role, ctx.author):
        await ctx.send('D--> You are not allowed to self-remove this role.')
        return
    await ctx.send(f'D--> The role {role} has been removed.')

@role_del.error
async def role_del_error(ctx, error):
    if isinstance(error, commands.RoleNotFound):
        await ctx.send(response_bank.role_error)
        return
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
    emoji_roles.add_reaction(msg, emoji, role)
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
