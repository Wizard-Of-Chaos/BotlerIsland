# The MetaCommand Cog, which handles all batch commands.
import os

import discord as dc
from discord.ext import commands

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot, CONST_ADMINS, user_or_perms

_cmd_dir = 'cmd'

class BatchCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.group(name='batch')
    @commands.bot_has_permissions(send_messages=True)
    @user_or_perms(CONST_ADMINS, administrator=True)
    async def batch(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('batch command help here')

    @batch.error
    async def batch_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            return
        raise error

    @batch.command(name='save')
    async def batch_save(self, ctx, name):
        if not (name.isascii() and name.replace('_', '').isalnum()):
            await ctx.send("D--> Command names only support alphanumeric characters and underscores.")
            return
        if not (atts := ctx.message.attachments):
            await ctx.send("D--> Missing batch command file.")
            return
        if len(atts := ctx.message.attachments) > 1:
            await ctx.send("D--> Only one file may be assigned to a batch command.")
            return
        atts[0].save(os.path.join(_cmd_dir, f'{name}.txt'))

    @batch_save.error
    async def batch_save_error(self, ctx, error):
        raise error

    @batch.command(name='exec')
    async def batch_exec(self, ctx, name):
        if not os.path.exists(fp := os.path.join(_cmd_dir, name)):
            await ctx.send("D--> Command does not exist.")
            return
        with open(fp, 'r') as cmdfile:
            for line in cmdfile:
                ctx.message.content = line.strip()
                await self.bot.invoke(ctx)

    @batch_exec.error
    async def batch_exec_error(self, ctx, error):
        raise error


bot.add_cog(BatchCommands(bot))
