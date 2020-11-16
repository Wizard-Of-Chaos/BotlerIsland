#Really, really stupid commands.

import random
import bot_common
import discord as dc
from cogs_textbanks import query_bank, response_bank

bot.group()
@commands.bot_has_permissions(send_messages=True)
async def generate(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(response_bank.generator_extension)

@generate.error
async def generate_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
        
