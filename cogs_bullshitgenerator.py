# Really, really stupid commands.
import os
import random

import discord as dc
from discord.ext import commands

from cogs_textbanks import query_bank, response_bank
from bot_common import bot

_daves = os.path.join('text', 'daves.txt')
_ryders = os.path.join('text', 'ryders.txt')
_dungeons = os.path.join('text', 'dungeons.txt')
_descriptors = os.path.join('text', 'descriptors.txt')
_figures = os.path.join('text', 'figures.txt')
_adjectives = os.path.join('text', 'adjectives.txt')
_groups = os.path.join('text', 'groups.txt')
_animals = os.path.join('text', 'animals.txt')
_verbs = os.path.join('text', 'verbs.txt')
_interlinks = os.path.join('text', 'interlinked.txt')

DEFAULT_TOTAL = 8


@bot.command(name='interlinked')
@commands.bot_has_permissions(send_messages=True)
async def interlinked(ctx):
    with open(_interlinks) as respfile:
        interlinks = random.choice(list(respfile)).strip()
        await ctx.send(embed=dc.Embed(
            color=ctx.guild.get_member(bot.user.id).color,
            description=f'{interlinks}\n\n**Interlinked.**',
            ).set_author(
            name='Baseline:',
            icon_url=bot.user.avatar_url,
            ))

@interlinked.error
async def interlinked_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error


def limit_pulls(limit=DEFAULT_TOTAL):
    def wrapped(total):
        return min(DEFAULT_TOTAL, int(total))
    return wrapped

class BullshitGenerator(commands.Cog):
    __slots__ = ('bot', 'embed')

    trollgen_cons = "BCDFGHJKLMNPQRSTVXZ"
    trollgen_vows = "AEIOUWY"
    trollgen_weights = ((7, 19), (4, 1), (15, 7), (4, 9), (8, 3), (1, 1))

    def __init__(self, bot):
        self.bot = bot

    def sample(self, pools, total):
        return zip(*(random.sample([l.strip() for l in pool], total) for pool in pools))

    @classmethod
    def troll_name(cls):
        return ''.join(
            random.choice(random.choices((cls.trollgen_vows, cls.trollgen_cons), w)[0])
            for w in cls.trollgen_weights
            ).capitalize()

    async def send(self, ctx, title, desc):
        client = self.bot.user
        await ctx.send(embed=dc.Embed(
            color=ctx.guild.get_member(client.id).color,
            description=desc,
            ).set_author(
            name=title,
            icon_url=client.avatar_url,
            ))

    @commands.Cog.listener()
    async def on_ready(self):
        print('D--> READY TO SHIT.')
        # self.embed = dc.Embed().set_author(icon_url=bot.user.avatar_url)

    @commands.group()
    @commands.bot_has_permissions(send_messages=True)
    async def generate(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(response_bank.generator_usage_format)

    @generate.error
    async def generate_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            return
        raise error

    @generate.command(name='ryder')
    @commands.bot_has_permissions(send_messages=True)
    async def generate_ryder(self, ctx, total: limit_pulls()=DEFAULT_TOTAL):
        with open(_daves) as daves, open(_ryders) as ryders:
            pools = self.sample((daves, ryders), total)
            embed_desc = '\n'.join(f'{d} {r}' for d, r in pools)
        await self.send(ctx, 'Your MST3K Ryder names:', embed_desc)

    @generate_ryder.error
    async def generate_ryder_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            return
        raise error

    @generate.command(name='dungeon')
    @commands.bot_has_permissions(send_messages=True)
    async def generate_dungeon(self, ctx, total: limit_pulls()=DEFAULT_TOTAL):
        with open(_dungeons) as dungeons, open(_descriptors) as descriptors:
            pools = self.sample((dungeons, descriptors), total)
            embed_desc = '\n'.join(f'{n} of {d}' for n, d in pools)
        await self.send(ctx, 'Your dungeon names:', embed_desc)

    @generate_dungeon.error
    async def generate_dungeon_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            return
        raise error
            
    @generate.command(name='group', aliases=['cult'])
    @commands.bot_has_permissions(send_messages=True)        
    async def generate_cult(self, ctx, total: limit_pulls()=DEFAULT_TOTAL):
        with open(_adjectives) as adjectives, open(_groups) as groups, open(_figures) as figures:
            pools = self.sample((adjectives, groups, figures), total)
            embed_desc = '\n'.join(f'{a} {g} of the {f}' for a, g, f in pools)
        await self.send(ctx, 'Your cult names:', embed_desc)

    @generate_cult.error
    async def generate_cult_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            return
        raise error

    @generate.command(name='tavern')
    @commands.bot_has_permissions(send_messages=True)
    async def generate_tavern(self, ctx, total: limit_pulls()=DEFAULT_TOTAL):
        with open(_animals) as animals, open(_verbs) as verbs:
            pools = self.sample((verbs, animals), total)
            embed_desc = '\n'.join(f'{v}ing {a}' for v, a in pools)
        await self.send(ctx, 'Your tavern names:', embed_desc)

    @generate_tavern.error
    async def generate_tavern_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            return
        raise error

    @generate.command(name='nrevat', aliases=['rtavern', 'revtavern', 'reversetavern'])
    @commands.bot_has_permissions(send_messages=True)
    async def generate_reverse_tavern(self, ctx, total: limit_pulls()=DEFAULT_TOTAL):
        with open(_animals) as animals, open(_verbs) as verbs:
            pools = self.sample((animals, verbs), total)
            embed_desc = '\n'.join(f'{a}ing {v}' for a, v in pools)
        await self.send(ctx, 'Your tavern names:', embed_desc)

    @generate_tavern.error
    async def generate_reverse_tavern_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            return
        raise error

    @generate.command(name='actionmovie', aliases=['movie', 'movies', 'movietitle'])
    @commands.bot_has_permissions(send_messages=True)
    async def generate_movie(self, ctx, total: limit_pulls()=DEFAULT_TOTAL):
        with open(_dungeons) as names, open(_descriptors) as descriptors, open(_daves) as firsts, open(_ryders) as lasts:
            pools = self.sample((names, descriptors, firsts, lasts), total)
            embed_desc = '\n'.join(
                f'{f} {l} in the {n} of {d}{"! "[random.randrange(2)]}'
                for n, d, f, l in pools
                )
        await self.send(ctx, 'Your sick movie names:', embed_desc)

    @generate_movie.error
    async def generate_movie_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            return
        raise error

    @generate.command(name='trollname', aliases=['trollnames', 'troll', 'trolls'])
    @commands.bot_has_permissions(send_messages=True) 
    async def generate_troll_names(self, ctx, total: limit_pulls(12)=12):
        names = (self.troll_name() for _ in range(2*total))
        embed_desc = '\n'.join(f'{f} {l}' for f, l in zip(*[names] * 2))
        await self.send(ctx, 'Your troll names:', embed_desc)

    @generate_troll_names.error
    async def generate_troll_names_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            return
        raise error


bot.add_cog(BullshitGenerator(bot))
