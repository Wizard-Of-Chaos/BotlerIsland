#Really, really stupid commands.
import random
import discord as dc
from discord.ext import commands

from cogs_textbanks import query_bank, response_bank
from bot_common import bot

class BullshitGenerator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


consonants = "BCDFGHJKLMNPQRSTVXZ"
vowels = "AEIOUWY"
weights = ((7, 19), (3, 1), (7, 15), (2, 9), (7, 2), (3, 7))
def generate_troll_name():
    return ' '.join(
        ''.join(
            random.choice(random.choices((vowels, consonants), i)[0])
            for i in weights
            ).capitalize()
        for _ in range(2)
        )

@bot.group()
@commands.bot_has_permissions(send_messages=True)
async def generate(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(response_bank.generator_extension)

@generate.error
async def generate_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
        
