# The TenseiBot Cog.
import os
from random import randrange, choices, sample
from itertools import islice

import discord as dc
from discord.ext import commands, tasks

from chainproofrhg import ChainProofRHG as RHG

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot, CONST_ADMINS, guild_config

CONST_SRC = 191265659936702464

_response_pool = os.path.join('text', 'noir.txt')


class TenseiBotAI(commands.Cog):
    __slots__ = ('bot',)

    def __init__(self, bot):
        self.bot = bot
    
    def generate_msg(self, msg):
        try:
            with open(_response_pool, 'r', encoding='utf-8') as respfile:
                lcount = sum(1 for _ in respfile)
                respfile.seek(0)
                return next(islice(respfile, randrange(lcount), None))
        except FileNotFoundError:
            with open(_response_pool, 'w', encoding='utf-8') as respfile:
                respfile.write("what's going on in /biz/?\n")
            return "what's going on in /biz/?\n"

    @commands.Cog.listener()
    async def on_ready(self):
        print('D--> Time to procrastinate on that Noir album.')

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.id == CONST_SRC:
            channel = msg.channel
            if (channel.id == guild_config.getlog(msg.guild, 'modlog')
                or channel.category_id == 360676396172836867
                ):
                return
            with open(_response_pool, 'a', encoding='utf-8') as respfile:
                respfile.write(msg.clean_content.strip() + '\n')

    # @commands.command(name='tensei')
    # @commands.bot_has_permissions(send_messages=True)
    # async def respond(self, ctx, *, query=''):
    #     src = ctx.guild.get_member(CONST_SRC)
    #     embed = dc.Embed(
    #         color=src.color if src else dc.Color(0xFF661F),
    #         )
    #     embed.set_author(
    #         name=f'{src.name if src else "TenseiBot"} says:',
    #         icon_url=src.avatar_url if src else url_bank.tensei_icon,
    #         )
    #     embed.description = self.generate_msg(ctx.message.clean_content[11:])
    #     await ctx.send(embed=embed)

    @respond.error
    async def respond_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            return
        raise error

#bot.add_cog(TenseiBotAI(bot))
