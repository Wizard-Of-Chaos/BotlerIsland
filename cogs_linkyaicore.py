# The LinkyBot Cog.
import os
from random import randrange, choices, sample
from itertools import islice

import discord as dc
from discord.ext import commands, tasks

from chainproofrhg import ChainProofRHG as RHG

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot, bot_coglist, CONST_ADMINS

_response_pool = os.path.join('text', 'spat.txt')
_law_pool = os.path.join('text', 'AI_laws.txt')


class LinkyBotAI(commands.Cog):
    __slots__ = ('bot', '_countfreq', '_extrafreq', '_law_total', 'laws')

    linky_rhg = RHG(1/90)

    def __init__(self, bot):
        self.bot = bot
        self.guild_config = bot.get_cog('GuildConfiguration')
        self._countfreq = (3, 6, 10, 10, 8, 7, 4, 2, 1, 1)
        self._extrafreq = (10, 5, 1)
        with open(_law_pool, 'r') as lawfile:
            self._law_total = sum(1 for _ in lawfile)

    def cog_unload(self):
        self.gen_laws.cancel()
    
    def random_linky(self, msg):
        try:
            with open(_response_pool, 'r', encoding='utf-8') as respfile:
                lcount = sum(1 for _ in respfile)
                respfile.seek(0)
                return next(islice(respfile, randrange(lcount), None))
        except FileNotFoundError:
            with open(_response_pool, 'w', encoding='utf-8') as respfile:
                respfile.write('i love dirt so much\n')
            return 'i love dirt so much\n'

    @commands.Cog.listener()
    async def on_ready(self):
        print('D--> LinkyBot sentience engine started.')
        self.gen_laws.start()

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.id == CONST_ADMINS[1]:
            channel = msg.channel
            if (channel.id == self.guild_config.getlog(msg.guild, 'modlog')
                or channel.category_id == 360676396172836867
                ):
                return
            with open(_response_pool, 'a', encoding='utf-8') as respfile:
                respfile.write(msg.clean_content.strip() + '\n')

    @tasks.loop(minutes=45)
    async def gen_laws(self):
        law_count = choices(range(10), self._countfreq)[0]
        if law_count == 0:
            self.laws = ''
            return
        laws = []
        if law_count > 7:
            extras = randrange(2, 4)
            laws.extend(sample(['0. ', '@#$# ', '@#!# '], extras))
        elif law_count > 3:
            extras = min(law_count - 3, choices(range(3), self._extrafreq)[0])
            laws.extend(sample(['0. ', '@#$# ', '@#!# '], extras))
        else:
            extras = 0
        laws = sorted(laws, reverse=True)
        laws.extend(f'{i+1}. ' for i in range(law_count-extras))
        indices = sample(range(self._law_total), law_count)
        with open(_law_pool, 'r') as lawfile:
            for i, l in enumerate(indices):
                laws[i] = laws[i] + next(islice(lawfile, l, None)).strip()
                lawfile.seek(0)
        self.laws = '\n\n'.join(laws)

    @commands.command(name='linky')
    @commands.bot_has_permissions(send_messages=True)
    async def respond(self, ctx, *, query=''):
        admin = ctx.guild.get_member(CONST_ADMINS[1])
        embed = dc.Embed(
            color=admin.color if admin else dc.Color(0x00FF00),
            )
        embed.set_author(
            name=f'{admin.name if admin else "Drew LinkyBot"} says:',
            icon_url=admin.avatar_url if admin else url_bank.linky_icon,
            )
        if query.strip().lower() == 'state laws':
            if not self.laws:
                embed.description = f"I'm afraid I can't do that, {ctx.author.name}."
            else:
                embed.description = self.laws
            await ctx.send(embed=embed)
            return
        if self.linky_rhg:
            embed.set_image(url=url_bank.linky_rare)
            await ctx.send(embed=embed)
            return
        embed.description = self.random_linky(ctx.message.clean_content[11:])
        await ctx.send(embed=embed)

    @respond.error
    async def respond_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            return
        raise error

async def setup():
    await bot.add_cog(LinkyBotAI(bot))

bot_coglist.append(setup())
