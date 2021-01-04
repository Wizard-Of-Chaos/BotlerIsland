# The BanManager Cog, which handles channel mute functions.
import os
import pickle
from collections import defaultdict

import discord as dc
from discord.ext import commands, tasks

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot, CogtextManager

class BanManager(CogtextManager):
    @staticmethod
    def _generate_empty():
        return None

    @tasks.loop(hours=1)
    async def manage_mutelist(self):
        pass

    @manage_mutelist.before_loop
    async def prepare_mutelist(self):
        pass

    @commands.Cog.listener()
    async def on_ready(self):
        self.manage_mutelist.start()

    @commands.Cog.listener()
    async def on_message(self, msg):
        pass

    @commands.group(name='channel')
    @commands.has_guild_permissions(send_messages=True, manage_roles=True)
    async def role_mute(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.message.delete()
            await ctx.send(response_bank.channel_usage)
            await aio.sleep(4)
            async for msg in ctx.channel.history(limit=128):
                if msg.author.id == bot.user.id and msg.content == response_bank.channel_usage:
                    await msg.delete()
                    break

    @role_mute.error
    async def role_mute_error(self, ctx, error):
        if isinstance(error,
            (commands.MissingPermissions, commands.BotMissingPermissions)
            ):
            return
        raise error

    @role_mute.command(name='ban')
    async def role_mute_apply(self, ctx, member: dc.Member, length, *, reason=''):
        pass

    @role_mute_apply.error
    async def role_mute_apply_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(response_bank.channel_member_error.format(
                member=error.args[0].split()[1]
                ))
            return
        raise error

    @role_mute.command(name='unban')
    async def role_mute_revoke(self, ctx, member: dc.Member, *, reason=''):
        pass

    @role_mute_revoke.error
    async def role_mute_revoke_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(response_bank.channel_member_error.format(
                member=error.args[0].split()[1]
                ))
            return
        raise error
