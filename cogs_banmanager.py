# The BanManager Cog, which handles channel mute functions.
import os
import pickle
from collections import defaultdict

import discord as dc
from discord.ext import commands, tasks

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot, CogtextManager

class BanManager(CogtextManager):
    @staticmethod
    def _generate_empty():
        return None

    @tasks.loop(hours=1)
    async def manage_mutelist(self):
        pass

    @manage_mutelist.before_loop
    async def prepare_mutelist(self):
        pass

    @commands.Cogs.listener
    async def on_message(self, msg):
        pass

    @commands.group(name='channel')
    async def role_mute(self, ctx):
        pass

    @role_mute.error
    async def role_mute_error(self, error):
        raise error

    @role_mute.command(name='ban')
    async def role_mute_apply(self, ctx, member: dc.Member, length, *, reason=''):
        pass

    @role_mute_apply.error
    async def role_mute_apply_error(self, error):
        raise error

    @role_mute.command(name='unban')
    async def role_mute_revoke(self, ctx, member: dc.Member, *, reason=''):
        pass

    @role_mute_revoke.error
    async def role_mute_revoke_error(self, error):
        raise error
