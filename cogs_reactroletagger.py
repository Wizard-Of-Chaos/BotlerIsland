# The ReactRoleTagger cog and all associated commands and data.
import os
import pickle
from datetime import datetime
from collections import defaultdict
from typing import Union, List, Optional

import discord as dc
from discord.ext import commands

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot, CogtextManager

EmojiUnion = Union[dc.Emoji, dc.PartialEmoji, str]

react_timetable = {}

def get_react_id(react: Union[dc.Reaction, EmojiUnion]) -> int:
    if isinstance(react, dc.Reaction):
        react = react.emoji
    if isinstance(react, (dc.Emoji, dc.PartialEmoji)):
        return react.id
    return hash(react)

async def get_msg_from_link(ctx, msglink: str) -> Optional[dc.Message]:
    *_, chn_id, msg_id = msglink.split('/')
    try:
        msg = await ctx.guild.get_channel(int(chn_id)).fetch_message(int(msg_id))
    except dc.NotFound:
        await ctx.send(response_bank.message_error)
        return None
    except dc.Forbidden:
        await ctx.send(response_bank.channel_perms_error.format(ctx=ctx))
        return None
    except dc.HTTPException:
        await ctx.send(response_bank.unexpected_state)
        return None
    return msg

async def process_role_grant(bot, msg, react, role, members) -> None:
    role_manager = bot.get_cog('RoleManager')
    if role_manager is None:
        raise RuntimeError(response_bank.unexpected_state)
    for member in members:
        await role_manager.purge_category(role, member)
        if role not in member.roles:
            await member.add_roles(role)
        await msg.remove_reaction(react, member)

class ReactRoleTagger(CogtextManager):
    @staticmethod
    def _generate_empty():
        return dict

    def cleanup_before_save(self):
        for chn_id, msg_dict in self.data.items():
            for msg_id in list(msg_dict):
                if not msg_dict[msg_id]:
                    del msg_dict[msg_id]
    
    def remove_reaction(self, msg, react):
        try:
            del self.data[msg.channel.id][msg.id][get_react_id(react)]
        except KeyError:
            print(response_bank.role_remove_react_error.format(react=react, msg=msg))
            return
        self.data_save()

    @commands.Cog.listener()
    async def on_ready(self):
        print(response_bank.process_reacts)
        # This is a horrible fucking way of granting all the pending roles. Too bad!
        for chn_id, msg_dict in self.data.items():
            channel = bot.get_channel(chn_id)
            for msg_id, emoji_dict in msg_dict.items():
                try:
                    msg = await channel.fetch_message(msg_id)
                except (AttributeError, dc.NotFound): # This message entry will be cleared when the bot closes.
                    emoji_dict.clear()
                    continue
                for react in msg.reactions:
                    if (emoji_id := get_react_id(react)) in emoji_dict:
                        role = msg.guild.get_role(emoji_dict[emoji_id])
                        members = [m async for m in react.users() if m.id != bot.user.id]
                        await process_role_grant(self.bot, msg, react, role, members)
        print(response_bank.process_reacts_complete)

    @commands.Cog.listener()
    async def on_message_delete(self, msg):
        # If a message with a react is removed, remove associated data if it exists.
        try:
            del self.data[msg.channel.id][msg.id]
        except KeyError:
            return
        self.data_save()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload): # Reaction is added to message
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
        if react_map := self.data[chn_id][msg_id]:
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
            if (last_react := react_timetable.get(member.id)) is not None:
                if (datetime.utcnow() - last_react).seconds < 2*60:
                    await msg.remove_reaction(emoji, member)
                    return
            react_timetable[member.id] = datetime.utcnow()
            await process_role_grant(self.bot, msg, emoji, role, (member,))

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload): # Reaction is removed from message
        # If reacts from the bot are removed from messages under the role reacts, remove the associated data.
        if (guild := bot.get_guild(payload.guild_id)) is None:
            return
        if payload.user_id != bot.user.id:
            return
        emoji = payload.emoji
        chn_id = payload.channel_id
        msg_id = payload.message_id
        # Checks if the message is in the dict
        if react_map := self.data[chn_id][msg_id]:
            # Find the reaction with matching emoji, then prune all further reacts.
            msg = await guild.get_channel(chn_id).fetch_message(msg_id)
            self.remove_reaction(msg, emoji)
            for react in msg.reactions:
                if str(react.emoji) == str(emoji):
                    async for member in react.users():
                        await msg.remove_reaction(emoji, member)
                    return

    @commands.Cog.listener()
    async def on_raw_reaction_clear_emoji(self, payload): # All reacts of one emoji cleared from message
        # If all reacts of a certain emoji are removed, remove associated data if it exists.
        if (guild := bot.get_guild(payload.guild_id)) is None:
            return
        emoji = payload.emoji
        chn_id = payload.channel_id
        msg_id = payload.message_id
        # Checks if the message is in the dict
        if react_map := self.data[chn_id][msg_id]:
            # Find the reaction with matching emoji, then prune all further reacts.
            msg = await guild.get_channel(chn_id).fetch_message(msg_id)
            self.remove_reaction(msg, emoji)

    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload): # All reacts cleared from message
        # If all reacts from a message are removed, remove associated data if it exists.
        if (guild := bot.get_guild(payload.guild_id)) is None:
            return
        msg = await guild.get_channel(payload.channel_id).fetch_message(payload.message_id)
        try:
            del self.data[msg.channel.id][msg.id]
        except KeyError:
            return
        self.data_save()

    @commands.group()
    @commands.bot_has_permissions(send_messages=True, manage_roles=True)
    async def reactrole(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(response_bank.reactrole_usage_format)

    @reactrole.error
    async def reactrole_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            print(response_bank.channel_perms_error.format(ctx=ctx))
            return
        raise error

    @reactrole.command(name='grant')
    @commands.bot_has_permissions(
        send_messages=True, read_message_history=True,
        manage_roles=True, manage_messages=True,
        )
    @commands.has_permissions(manage_roles=True)
    async def reactrole_grant(self, ctx, msglink: str, emoji: EmojiUnion, role: dc.Role):
        # Force all who reacted with the specified emoji in the given message link to be granted a role.
        if (msg := await get_msg_from_link(ctx, msglink)) is None:
            return
        try:
            react = next(
                r for r in msg.reactions
                if type(emoji) is str and r.emoji == emoji
                or r.emoji.id == emoji.id
                )
        except StopIteration:
            await ctx.send(response_bank.react_error)
            return
        members = [m async for m in react.users() if m.id != bot.user.id]
        await process_role_grant(self.bot, msg, react, role, members)
        await ctx.send(response_bank.reactrole_grant_confirm)

    @reactrole_grant.error
    async def reactrole_grant_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            print(response_bank.channel_perms_error.format(ctx=ctx))
            return
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        elif isinstance(error, commands.RoleNotFound):
            await ctx.send(response_bank.role_error)
            return
        raise error

    @reactrole.command(name='add')
    @commands.bot_has_permissions(
        send_messages=True, read_message_history=True, add_reactions=True
        )
    @commands.has_permissions(manage_roles=True)
    async def reactrole_add(self, ctx, msglink: str, emoji: EmojiUnion, role: dc.Role):
        # Add a reaction to a message that will be attached to a toggleable role when reacted to.
        if (msg := await get_msg_from_link(ctx, msglink)) is None:
            return
        try:
            await msg.add_reaction(emoji)
        except dc.HTTPException:
            await ctx.send(response_bank.reactrole_add_error)
            return
        self.data[msg.channel.id][msg.id][get_react_id(emoji)] = role.id
        self.data_save()
        await ctx.send(response_bank.reactrole_add_confirm.format(role=role))

    @reactrole_add.error
    async def reactrole_add_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            print(response_bank.channel_perms_error.format(ctx=ctx))
            return
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        elif isinstance(error, commands.RoleNotFound):
            await ctx.send(response_bank.role_error)
            return
        raise error

    @reactrole.command(name='del')
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    @commands.has_permissions(manage_roles=True)
    async def reactrole_del(self, ctx, msglink: str, emoji: EmojiUnion):
        pass

    @reactrole_del.error
    async def reactrole_del_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            print(response_bank.channel_perms_error.format(ctx=ctx))
            return
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        raise error


bot.add_cog(ReactRoleTagger(bot))
