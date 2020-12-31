# The BanManager Cog, which handles channel mute functions.
import os
import pickle
from collections import defaultdict

import discord as dc
from discord.ext import commands

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot, CogtextManager

class BanManager(CogtextManager):
    pass
