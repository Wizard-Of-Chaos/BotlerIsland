# The LogManager Cog, which handles logging and error reporting.
import os
import logging
from datetime import datetime

import discord as dc
from discord.ext import commands, tasks
import aiohttp

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot

log_chid = 830752125998596126

logger = logging.getLogger('discord')
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='r+')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
handler.setLevel(logging.WARNING)
logger.addHandler(handler)

def get_token():
    with open('pbtoken.dat', 'r') as tokenfile:
        return tokenfile.read().strip()


class LoggingError(Exception):
    """When some shit happens to the logging. But if that happens, how does it log?"""


class LogManager(commands.Cog):
    _post_data = {
        'api_option': 'paste',
        'api_dev_key': get_token(),
        'api_paste_private': '1',
        'api_paste_expire_date': '1M',
        }

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
        now = datetime.utcnow()
        with open('discord.log', 'r+') as logfile:
            if not (code:=logfile.read()): return
            logfile.truncate(0)
            self._post_data.update(api_paste_code=code, api_paste_name=f'ArquiusBot Log {now}')
            async with aiohttp.ClientSession() as session:
                resp = await session.post('https://pastebin.com/api/api_post.php', data=self._post_data)
                if resp.status != 200:
                    raise LoggingError(f'Error {resp.status}: {await resp.text()}')
                await self.log_channel.send(f'ArquiusBot Log {now} @ <{await resp.text()}>')


bot.add_cog(LogManager(bot))
