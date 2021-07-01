# The MetaCommand Cog, which handles all batch commands.
import os

import discord as dc
from discord.ext import commands

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot, CONST_AUTHOR, user_or_perms

_cmd_dir = 'cmd'

class BatchCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if bot.get_cog('ReactRoleTagger'):
            pass
        print(response_bank.batch_cog_ready)

    @commands.group(name='batch')
    @commands.bot_has_permissions(send_messages=True)
    @user_or_perms(CONST_AUTHOR, administrator=True)
    async def batch(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(response_bank.batch_usage_format)

    @batch.error
    async def batch_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            return
        raise error

    @batch.command(name='save')
    async def batch_save(self, ctx, name):
        if not (name.isascii() and name.replace('_', '').isalnum()):
            await ctx.send(response_bank.batch_save_name_error)
            return
        if not (atts := ctx.message.attachments):
            await ctx.send(response_bank.batch_save_missing_file)
            return
        if len(atts) > 1:
            await ctx.send(response_bank.batch_save_ambiguous_file)
            return
        await atts[0].save(os.path.join(_cmd_dir, f'{name}.txt'))
        await ctx.send(response_bank.batch_save_confirm.format(name=name))

    @batch_save.error
    async def batch_save_error(self, ctx, error):
        raise error

    @batch.command(name='exec')
    async def batch_exec(self, ctx, name):
        if not os.path.exists(fp := os.path.join(_cmd_dir, f'{name}.txt')):
            await ctx.send(response_bank.batch_exec_name_error.format(name=name))
            return
        await ctx.send(response_bank.batch_exec_start.format(name=name))
        with open(fp, 'r') as cmdfile:
            msg = ctx.message
            for line in cmdfile:
                msg.content = line.strip()
                try:
                    await self.bot.process_commands(msg)
                except Exception as exc:
                    await ctx.send(f'{type(exc).__name__}: {''.join(exc.args)}')
                    raise

    @batch_exec.error
    async def batch_exec_error(self, ctx, error):
        raise error


bot.add_cog(BatchCommands(bot))
