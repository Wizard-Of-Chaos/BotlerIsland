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

DEFAULT_TOTAL = 10

consonants = "BCDFGHJKLMNPQRSTVXZ"
vowels = "AEIOUWY"
weights = ((7, 19), (1, 4), (15, 7), (2, 9), (3, 8), (1, 1))
def generate_troll_name():
    return ' '.join(
        ''.join(
            random.choice(random.choices((vowels, consonants), i)[0])
            for i in weights
            ).capitalize()
        for _ in range(2)
        )

class BullshitGenerator(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

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
            icon_url=bot.user.avatar_url.
            ))

@interlinked.error
async def interlinked_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.group()
@commands.bot_has_permissions(send_messages=True)
async def generate(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(response_bank.generator_usage_format)
    
@generate.error
async def generate_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error
        
@generate.command(name='ryder')
@commands.bot_has_permissions(send_messages=True)
async def rydergen(ctx, total=DEFAULT_TOTAL):
    firsts = open(_daves).read().splitlines()
    lasts = open(_ryders).read().splitlines()
    ryders = ''
    for _ in range(total):
        ryders = ryders + random.choice(firsts) + ' ' + random.choice(lasts) + '\n'
    await ctx.send(embed=dc.Embed(
        color=ctx.guild.get_member(bot.user.id).color,
        description=ryders,
        ).set_author(
        name='Your MST3K Ryder names:',
        icon_url=bot.user.avatar_url,
        ))
        
@generate.command(name='dungeon')
@commands.bot_has_permissions(send_messages=True)
async def dungeongen(ctx, total=DEFAULT_TOTAL):
    names = open(_dungeons).read().splitlines()
    descriptors = open(_descriptors).read().splitlines()
    dungeons = ''
    for _ in range(total):
        dungeons = dungeons + random.choice(names) + ' of ' + random.choice(descriptors) + '\n'
    await ctx.send(embed=dc.Embed(
        color=ctx.guild.get_member(bot.user.id).color,
        description=dungeons,
        ).set_author(
        name='Your dungeon names:',
        icon_url=bot.user.avatar_url,
        ))
        
@generate.command(name='group')
@commands.bot_has_permissions(send_messages=True)        
async def cultgen(ctx, total=DEFAULT_TOTAL):
    adjectives = open(_adjectives).read().splitlines()
    group = open(_groups).read().splitlines()
    figures = open(_figures).read().splitlines()
    groups = ''
    for _ in range(total):
        groups = groups + random.choice(adjectives) + ' ' + random.choice(group) + ' of the ' + random.choice(figures) + '\n'
    await ctx.send(embed=dc.Embed(
        color=ctx.guild.get_member(bot.user.id).color,
        description=groups,
        ).set_author(
        name='Your cult names:',
        icon_url=bot.user.avatar_url,
        ))

@generate.command(name='tavern')
@commands.bot_has_permissions(send_messages=True)
async def taverngen(ctx, total=DEFAULT_TOTAL):
    animals = open(_animals).read().splitlines()
    verbs = open(_verbs).read().splitlines()
    taverns = ''
    for _ in range(total):
        taverns = taverns + random.choice(verbs) + 'ing ' + random.choice(animals) + '\n'
    await ctx.send(embed=dc.Embed(
        color=ctx.guild.get_member(bot.user.id).color,
        description=taverns,
        ).set_author(
        name='Your tavern names:',
        icon_url=bot.user.avatar_url,
        ))
        
@generate.command(name='trollname', aliases=['trollnames'])
@commands.bot_has_permissions(send_messages=True) 
async def trollgen(ctx, total=DEFAULT_TOTAL):
    trolls = '\n'.join(generate_troll_name() for _ in range(total))
    await ctx.send(embed=dc.Embed(
        color=ctx.guild.get_member(bot.user.id).color,
        description=trolls,
        ).set_author(
        name='Your troll names:',
        icon_url=bot.user.avatar_url,
        ))

@generate.command(name='actionmovie', alieases=['movie'])
@commands.bot_has_permissions(send_messages=True)
async def moviegen(ctx, total=DEFAULT_TOTAL):
    names = open(_dungeons).read().splitlines()
    descriptors = open(_descriptors).read().splitlines()
    firsts = open(_daves).read().splitlines()
    lasts = open(_ryders).read().splitlines()
    movies = ''
    for _ in range(total):
        movies = movies + random.choice(firsts) + ' ' + random.choice(lasts) + ' in the ' + random.choice(names) + ' of ' + random.choice(descriptors) + '! \n'
    await ctx.send(embed=dc.Embed(
        color=ctx.guild.get_member(bot.user.id).color,
        description=movies,
        ).set_author(
        name='Your sick movie names:',
        icon_url=bot.user.avatar_url,
        ))
