# The LogManager Cog, which handles logging and error reporting.
import os
from datetime import datetime

import discord as dc
from discord.ext import commands, tasks

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot

log_chid = 830752125998596126

class LogManager(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    def cog_unload(self):
        self.report_log.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        print('D--> Dumping logs...')
        self.log_channel = self.bot.get_channel(log_chid)
        self.report_log.start()

    @tasks.loop(hours=1)
    async def report_log(self):
        with open('discord.log', 'rb+') as logfile:
            await self.log_channel.send(datetime.utcnow(), file=dc.File(fp=logfile))
            logfile.truncate(0)


bot.add_cog(LogManager(bot))
