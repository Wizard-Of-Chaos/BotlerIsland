# Initial setup for global variables. Import names from here for the main bot tasks.
import random
from datetime import datetime

import discord as dc
from discord.ext import commands, tasks

import sqlalchemy as sql

from cogs_modtools import (
    guild_whitelist, CogtextManager, 
    MemberStalker, Suggestions,
    )
from cogs_statstracker import StatsTracker

random.seed(datetime.now())
bot = commands.Bot(command_prefix='D--> ', intents=dc.Intents.all())
bot.remove_command('help')

help_data = []

sql_engine = sql.create_engine('sqlite+pysqlite:///aqbot.db', echo=True, future=True)
sql_metadata = sql.MetaData()
sql_metadata.reflect(bind=sql_engine)

member_stalker = MemberStalker('members.pkl')
stats_tracker = StatsTracker('stats.pkl')
stored_suggestions = Suggestions('suggestions.pkl')

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


def main():
    with open('token.dat', 'r') as tokenfile, member_stalker, stats_tracker, stored_suggestions:
        raw = tokenfile.read().strip()
        bot.run(''.join(chr(int(''.join(c), 16)) for c in zip(*[iter(raw)]*2)))
