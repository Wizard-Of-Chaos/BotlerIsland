# Default bot events.
import discord as dc
from discord.ext import commands

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot, guild_whitelist, CONST_ADMINS, CONST_AUTHOR

@bot.event
async def on_ready(): # Bot starts
    print(response_bank.bot_startup.format(version='1.5.3'))
    for guild in bot.guilds:
        if guild.id not in guild_whitelist:
            await guild.leave()
    print(response_bank.verify_whitelist_complete)
    await bot.change_presence(
        activity=dc.Game(name=response_bank.online_status)
        )

@bot.event
async def on_guild_join(guild): # Bot joins guild
    if guild.id not in guild_whitelist:
        await guild.leave()

@bot.event
async def on_message(msg): # Force process_commands to not auto-call
    pass
