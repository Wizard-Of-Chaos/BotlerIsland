# Initial setup for global variables. Import names from here for the main bot tasks.
import random
from datetime import datetime

import discord as dc
from discord.ext import commands, tasks

from cogs_modtools import (
    guild_whitelist, CogtextManager, 
    GuildConfig, MemberStalker, Suggestions,
    )
from cogs_statstracker import StatsTracker

random.seed(datetime.now())
bot = commands.Bot(command_prefix='D--> ', intents=dc.Intents.all())
bot.remove_command('help')

help_data = []

guild_config = GuildConfig(bot, 'config.pkl')
member_stalker = MemberStalker('members.pkl')
stats_tracker = StatsTracker('stats.pkl')
stored_suggestions = Suggestions('suggestions.pkl')

CONST_ADMINS = (120187484863856640, 148346796186271744) # Mac, Dirt
CONST_AUTHOR = (125433170047795200, 257144766901256192) # 9, WoC


def get_token() -> str:
    with open('token.dat', 'r') as tokenfile:
        raw = tokenfile.read().strip()
        return ''.join(chr(int(''.join(c), 16)) for c in zip(*[iter(raw)]*2))


def main(token):
    with guild_config, member_stalker, stats_tracker, stored_suggestions:
        bot.run(token)
