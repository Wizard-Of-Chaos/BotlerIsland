# Initial setup for global variables. Import names from here for the main bot tasks.
import random
from datetime import datetime

import discord as dc
from discord.ext import commands, tasks

from cogs_modtools import (
    guild_whitelist, GuildConfig, MemberStalker,
    EmojiRoles, RoleCategories, Suggestions,
    )
from cogs_statstracker import StatsTracker

random.seed(datetime.now())
bot = commands.Bot(command_prefix='D--> ', intents=dc.Intents.all())
bot.remove_command('help')

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
