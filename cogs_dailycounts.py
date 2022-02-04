# The DailyCounter Cog, posting daily statistics.
from datetime import datetime, timedelta
from collections import Counter

import asyncio as aio

import discord as dc
from discord.ext import commands, tasks

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot, sql_engine, sql_metadata, guild_whitelist, CONST_ADMINS, CONST_AUTHOR
import cogs_guildconfig
import cogs_userdatalogger
import cogs_chandatalogger

class DailyCounter(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
        self.guild_config = bot.get_cog('GuildConfiguration')
        self.user_datalogger = bot.get_cog('UserDataLogger')
        self.chan_datalogger = bot.get_cog('ChanDataLogger')
        if not (self.guild_config and self.user_datalogger and self.chan_datalogger):
            raise RuntimeError(response_bank.unexpected_state)

    def cog_unload(self):
        self.post_dailies.cancel()

    def create_embed(self, guild_data, guild, author, msg):
        msg_counts = "\n".join(
            f'`{guild.get_channel(chan_id)}:` '
            f'**{counts["MessagesAdded"]}** | '
            f'**{counts["MessagesEdited"]}** | '
            f'**{counts["MessagesDeleted"]}**'
            for chan_id, counts in sorted(guild_data.items(), key=lambda i: -i[1]['MessagesAdded'])
            )
        embed = dc.Embed(
            color=author.color,
            timestamp=datetime.utcnow(),
            description=f'**Message counts (added, edited, deleted) since midnight UTC or bot start:**\n{msg_counts}',
            )
        user_logs = Counter(
            row[2]
            for row in self.user_datalogger.get_joins_on_date(datetime.utcnow().date())
            )
        embed.set_author(name=f'Daily counts for {author}', icon_url=author.avatar_url)
        embed.add_field(name='Users Gained:', value=user_logs['join'])
        embed.add_field(name='Users Lost:', value=user_logs['leave']-user_logs['ban'])
        embed.add_field(name='Users Banned:', value=user_logs['ban'])
        embed.add_field(name='**DISCLAIMER**:', value=msg, inline=False)
        return embed

    @commands.Cog.listener()
    async def on_ready(self):
        print(response_bank.process_dailies)
        self.post_dailies.start()

    @tasks.loop(hours=24)
    async def post_dailies(self):
        guild_data = self.chan_datalogger.get_current_record()
        for guild_id, admin_id in zip(guild_whitelist, (CONST_ADMINS[1], CONST_AUTHOR[0])):
            guild = bot.get_guild(guild_id)
            if guild is None or guild.get_member(bot.user.id) is None:
                continue
            admin = guild.get_member(admin_id)
            embed = self.create_embed(guild_data[guild.id], guild, admin,
                'Counts may not be accurate if the bot has been stopped at any point during the day.',
                )
            await self.guild_config.send_to_log_channel(
                guild, 'modlog',
                admin.mention if admin_id == CONST_ADMINS[1] else '',
                embed=embed,
                )
        self.chan_datalogger.update_records()

    @post_dailies.before_loop
    async def post_dailies_start_delay(self):
        await self.bot.wait_until_ready()
        print(response_bank.process_dailies_complete)
        now = datetime.utcnow()
        await aio.sleep(
            (datetime.combine(now.date() + timedelta(1), datetime.min.time()) - now).seconds
            )

    @commands.command(name='daily')
    @commands.has_guild_permissions(manage_roles=True)
    async def force_daily_post(self, ctx):
        guild_data = self.chan_datalogger.get_current_record()[ctx.guild.id]
        await self.guild_config.send_to_log_channel(
            ctx.guild, 'modlog', ctx.author.mention,
            embed=self.create_embed(guild_data, ctx.guild, ctx.author,
                'Counts may not be accurate if the bot has been stopped at any point during the day.\n'
                'Counts will reset upon midnight UTC, upon which an automated message will display.',
                )
            )

    @force_daily_post.error
    async def force_daily_post_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        raise error


bot.add_cog(DailyCounter(bot))
