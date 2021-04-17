# The LogManager Cog, which handles logging and error reporting.
import os
import logging
from datetime import datetime

import discord as dc
from discord.ext import commands, tasks

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot

log_chid = 830752125998596126

logger = logging.getLogger('discord')
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='r+')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)


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
