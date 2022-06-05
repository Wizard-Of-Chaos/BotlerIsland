from datetime import datetime, timedelta
from collections import Counter

import asyncio as aio

import discord as dc
from discord.ext import commands, tasks

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot, guild_whitelist, CONST_ADMINS, CONST_AUTHOR

class DailyCounter(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
        self.guild_config = bot.get_cog('GuildConfiguration')
        self.daily_msg = {guild_id: Counter() for guild_id in guild_whitelist}
        self.daily_usr = {
            guild_id: Counter({'join': 0, 'leave': 0, 'ban': 0})
            for guild_id in guild_whitelist
            }

    def cog_unload(self):
        self.post_dailies.cancel()

    def create_embed(self, guild, author, msg):
        guild_id = guild.id
        msg_counts = "\n".join(
            f'`{guild.get_channel(chan_id)}:` **{count}**'
            for chan_id, count in self.daily_msg[guild_id].most_common()
            )
        embed = dc.Embed(
            color=author.color,
            timestamp=datetime.utcnow(),
            description=f'**Message counts since midnight UTC or bot start:**\n{msg_counts}',
            )
        guild_data = self.daily_usr[guild_id]
        embed.set_author(name=f'Daily counts for {author}', icon_url=author.avatar_url)
        embed.add_field(name='Users Gained:', value=guild_data['join'])
        embed.add_field(name='Users Lost:', value=guild_data['leave']-guild_data['ban'])
        embed.add_field(name='Users Banned:', value=guild_data['ban'])
        embed.add_field(name='**DISCLAIMER**:', value=msg, inline=False)
        return embed

    @commands.Cog.listener()
    async def on_ready(self):
        print(response_bank.process_dailies)
        self.post_dailies.start()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        if guild.id in guild_whitelist:
            self.daily_usr[guild.id]['join'] += 1

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild
        if guild.id in guild_whitelist:
            self.daily_usr[guild.id]['leave'] += 1

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        if guild.id in guild_whitelist:
            self.daily_usr[guild.id]['ban'] += 1

    @commands.Cog.listener()
    async def on_message(self, msg): # Message posted event
        if msg.guild.id in guild_whitelist:
            self.daily_msg[msg.guild.id][msg.channel.id] += 1

    @tasks.loop(hours=24)
    async def post_dailies(self):
        for guild_id, admin_id in zip(guild_whitelist, (CONST_ADMINS[1], CONST_AUTHOR[0])):
            guild = bot.get_guild(guild_id)
            if guild is None or guild.get_member(bot.user.id) is None:
                continue
            admin = guild.get_member(admin_id)
            embed = self.create_embed(guild, admin,
                'Counts may not be accurate if the bot has been stopped at any point during the day.',
                )
            self.daily_msg[guild_id].clear()
            self.daily_usr[guild_id].clear()
            await self.guild_config.log(
                guild, 'modlog',
                admin.mention if admin_id == CONST_ADMINS[1] else '',
                embed=embed,
                )

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
        await self.guild_config.log(
            ctx.guild, 'modlog', ctx.author.mention,
            embed=self.create_embed(ctx.guild, ctx.author,
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


#bot.add_cog(DailyCounter(bot))
