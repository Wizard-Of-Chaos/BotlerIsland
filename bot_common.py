# Initial setup for global variables. Import names from here for the main bot tasks.
import random
import logging
from datetime import datetime

import discord as dc
from discord.ext import commands, tasks

from cogs_modtools import (
    guild_whitelist, GuildConfig, MemberStalker, Suggestions
    RoleCategories, EmojiRoles
    )
from cogs_statstracker import StatsTracker

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

random.seed(datetime.now())
bot = commands.Bot(command_prefix='D--> ', intents=dc.Intents.all())
bot.remove_command('help')

help_data = []

guild_config = GuildConfig(bot, 'config.pkl')
member_stalker = MemberStalker('members.pkl')
stats_tracker = StatsTracker('stats.pkl')
emoji_roles = EmojiRoles('roles.pkl')
role_categories = RoleCategories('rolecats.pkl')
stored_suggestions = Suggestions('suggestions.pkl')

CONST_ADMINS = (120187484863856640, 148346796186271744) # Mac, Dirt
CONST_AUTHOR = (125433170047795200, 257144766901256192) # 9, WoC

async def process_role_grant(msg, react, role, members):
    for member in members:
        await role_categories.purge_category(role, member)
        if role not in member.roles:
            await member.add_roles(role)
        await msg.remove_reaction(react, member)


def get_token() -> str:
    with open('token.dat', 'r') as tokenfile:
        raw = tokenfile.read().strip()
        return ''.join(chr(int(''.join(c), 16)) for c in zip(*[iter(raw)]*2))


def main(token):
    with guild_config, member_stalker, stats_tracker, stored_suggestions, emoji_roles, role_categories:
        bot.run(token)
