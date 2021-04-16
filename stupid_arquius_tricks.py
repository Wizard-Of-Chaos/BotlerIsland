#Really, really stupid commands.
import random
import discord as dc
from discord.ext import commands
import os

from cogs_textbanks import query_bank, response_bank
from bot_common import bot

class BullshitGenerator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

consonants = "BCDFGHJKLMNPQRSTVXZ"
vowels = "AEIOUWY"
weights = ((7, 19), (3, 1), (7, 15), (2, 9), (7, 2), (3, 7))
def generate_troll_name():
    return ' '.join(
        ''.join(
            random.choice(random.choices((vowels, consonants), i)[0])
            for i in weights
            ).capitalize()
        for _ in range(2)
        )

@bot.command(name='interlinked')
@commands.bot_has_permissions(send_messages=True)
async def interlinked(ctx):
	interlinks = open(_interlinks).read().splitlines()
	baseline = random.choice(interlinks) + ' Interlinked.'

	await ctx.send(embed=dc.Embed(
		color=ctx.guild.get_member(bot.user.id).color,
		description = baseline
		).set_author(
		name='Baseline:', icon_url=bot.user.avatar_url
		))

@bot.group()
@commands.bot_has_permissions(send_messages=True)
async def generate(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(response_bank.generator_extension)
    
@generate.error
async def generate_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
        
@generate.command(name='ryder')
@commands.bot_has_permissions(send_messages=True)
async def rydergen(ctx):
    firsts = open(_daves).read().splitlines()
    lasts = open(_ryders).read().splitlines()
    count = 0
    ryders = ''
    while count < 10:
        ryders = ryders + random.choice(firsts) + ' ' + random.choice(lasts) + '\n'
        count = count +1

    await ctx.send(embed=dc.Embed(
        color=ctx.guild.get_member(bot.user.id).color,
        description = ryders
        ).set_author(
        name='Your MST3K Ryder names:', icon_url=bot.user.avatar_url
        ))
        
@generate.command(name='dungeon')
@commands.bot_has_permissions(send_messages=True)
async def dungeongen(ctx):
    names = open(_dungeons).read().splitlines()
    descriptors = open(_descriptors).read().splitlines()
    count = 0
    dungeons = ''
    while count < 10:
        dungeons = dungeons + random.choice(names) + ' of ' + random.choice(descriptors) + '\n'
        count = count +1

    await ctx.send(embed=dc.Embed(
        color=ctx.guild.get_member(bot.user.id).color,
        description = dungeons
        ).set_author(
        name='Your dungeon names:', icon_url=bot.user.avatar_url
        ))
        
@generate.command(name='group')
@commands.bot_has_permissions(send_messages=True)        
async def cultgen(ctx):
    adjectives = open(_adjectives).read().splitlines()
    group = open(_groups).read().splitlines()
    figures = open(_figures).read().splitlines()
    count = 0
    groups = ''
    while count < 10:
        groups = groups + random.choice(adjectives) + ' ' + random.choice(group) + ' of the ' + random.choice(figures) + '\n'
        count = count +1

    await ctx.send(embed=dc.Embed(
        color=ctx.guild.get_member(bot.user.id).color,
        description = groups
        ).set_author(
        name='Your cult names:', icon_url=bot.user.avatar_url
        ))

@generate.command(name='tavern')
@commands.bot_has_permissions(send_messages=True)
async def taverngen(ctx):
    animals = open(_animals).read().splitlines()
    verbs = open(_verbs).read().splitlines()
    count = 0
    taverns = ''
    while count < 10:
        taverns = taverns + random.choice(verbs) + 'ing ' + random.choice(animals) + '\n'
        count = count +1

    await ctx.send(embed=dc.Embed(
        color=ctx.guild.get_member(bot.user.id).color,
        description = taverns
        ).set_author(
        name='Your tavern names:', icon_url=bot.user.avatar_url
        ))
        
@generate.command(name='trollname')
@commands.bot_has_permissions(send_messages=True) 
async def trollgen(ctx):

    count = 0
    trolls = ''
    while count < 10:
        trolls = trolls + generate_troll_name() + '\n'
        count = count +1
        
    await ctx.send(embed=dc.Embed(
        color=ctx.guild.get_member(bot.user.id).color,
        description = trolls
        ).set_author(
        name='Your troll names:', icon_url=bot.user.avatar_url
        ))

@generate.command(name='actionmovie')
@commands.bot_has_permissions(send_messages=True)
async def moviegen(ctx):
    names = open(_dungeons).read().splitlines()
    descriptors = open(_descriptors).read().splitlines()
    firsts = open(_daves).read().splitlines()
    lasts = open(_ryders).read().splitlines()
    count = 0
    movies = ''
    while count < 10:
        movies = movies + random.choice(firsts) + ' ' + random.choice(lasts) + ' in the ' + random.choice(names) + ' of ' + random.choice(descriptors) + '! \n'
        count = count +1
        
    await ctx.send(embed=dc.Embed(
        color=ctx.guild.get_member(bot.user.id).color,
        description = movies
        ).set_author(
        name='Your sick movie names:', icon_url=bot.user.avatar_url
        ))