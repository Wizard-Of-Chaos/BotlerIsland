# Initial setup for global variables. Import names from here for the main bot tasks.
import sys
import random
from datetime import datetime
import argparse

import discord as dc
from discord.ext import commands, tasks

import sqlalchemy as sql

from cogs_modtools import CogtextManager, Suggestions

parser = argparse.ArgumentParser()
parser.add_argument('tokenfile')
args = parser.parse_args()

random.seed(datetime.now())
bot = commands.Bot(command_prefix='D--> ', intents=dc.Intents.all())
bot.remove_command('help')
bot_coglist = []

help_data = []

sql_engine = sql.create_engine('sqlite+pysqlite:///aqbot.db', echo=True, future=True)
sql_metadata = sql.MetaData()
sql_metadata.reflect(bind=sql_engine)

stored_suggestions = Suggestions('suggestions.pkl')

guild_whitelist = (
    152981670507577344, 663452978237407262, 402880303065989121, 431698070510501891,
    )
CONST_ADMINS = (120187484863856640, 148346796186271744) # Mac, Dirt
CONST_AUTHOR = (125433170047795200, 257144766901256192) # 9, WoC

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

async def main():
    async with bot:
        for cog_adder in bot_coglist:
            await cog_adder
        with open(args.tokenfile, 'r') as tokenfile, stored_suggestions:
            raw = tokenfile.read().strip()
            try:
                await bot.start(''.join(chr(int(''.join(c), 16)) for c in zip(*[iter(raw)]*2)))
            except KeyboardInterrupt:
                return
