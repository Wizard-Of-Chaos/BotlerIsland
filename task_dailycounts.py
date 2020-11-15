from datetime import datetime, timedelta
from collections import Counter

import asyncio as aio

import discord as dc
from discord.ext import tasks

from textbanks import query_bank, response_bank
from bot_common import bot, guild_whitelist

daily_msg = {guild_id: Counter() for guild_id in guild_whitelist}
daily_usr = {guild_id: Counter({'join': 0, 'leave': 0}) for guild_id in guild_whitelist}

@tasks.loop(hours=24)
async def post_dailies():
    for guild_id, admin_id in zip(guild_whitelist, (CONST_ADMINS[1], CONST_AUTHOR[0])):
        guild = bot.get_guild(guild_id)
        if guild is None or guild.get_member(bot.user.id) is None:
            continue
        admin = guild.get_member(admin_id)
        now = datetime.utcnow()
        msg_counts = "\n".join(
            f'`{guild.get_channel(chan_id)}:` **{count}**'
            for chan_id, count in daily_msg[guild_id].most_common()
            )
        embed = dc.Embed(
            color=admin.color,
            timestamp=now,
            description=f'**Message counts since midnight UTC or bot start:**\n\n{msg_counts}',
            )
        embed.set_author(name=f'Daily counts for {admin}', icon_url=admin.avatar_url)
        embed.add_field(name='Users Gained:', value=daily_usr[guild_id]['join'])
        embed.add_field(name='Users Lost:', value=daily_usr[guild_id]['leave'])
        embed.add_field(
            name='**DISCLAIMER:**',
            value='Counts may not be accurate if the bot has been stopped at any point during the day.',
            inline=False,
            )
        daily_msg[guild_id].clear()
        daily_usr[guild_id].clear()
        await guild_config.log(
            guild, 'modlog',
            admin.mention if admin_id == CONST_ADMINS[1] else '',
            embed=embed,
            )

@post_dailies.before_loop
async def post_dailies_start_delay():
    now = datetime.utcnow()
    await aio.sleep(
        (datetime.combine(now.date() + timedelta(1), datetime.min.time()) - now).seconds
        )
