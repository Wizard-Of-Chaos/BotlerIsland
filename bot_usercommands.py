# For most public commands.
import io
import re
import json
import random
from datetime import datetime

import asyncio as aio
import aiohttp

import discord as dc
from discord.ext import commands

from cogs_textbanks import query_bank, response_bank
from bot_common import (
    bot, CONST_ADMINS, CONST_AUTHOR,
    guild_config, member_stalker, stored_suggestions,
    )

def get_name(member_id):
    return str(bot.get_user(int(member_id[1])))

async def grab_latex(preamble, postamble, raw_latex):
    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            'https://rtex.probablyaweb.site/api/v2',
            data={'format':'png','code':preamble+raw_latex+postamble},
            )
        resp = await resp.text() # Awaiting loading of the raw text data and unicode parsing
        resp = json.loads(resp)
        if (resp['status'] != 'success'):
            return None
        return await session.get(f'https://rtex.probablyaweb.site/api/v2/{resp["filename"]}')

@bot.command(name='help')
@commands.bot_has_permissions(send_messages=True)
async def userhelp(ctx):
    await ctx.send(embed=dc.Embed(
        description=f'D--> It seems you have asked about the *Homestuck and Hiveswap Discord Utility Bot*:tm:.'
            f'This is a bot designed to cater to the server\'s moderation, utility, and statistic '
            f'tracking needs. If the functions herein described are not performing to the degree '
            f'that is claimed, please direct your attention to **Wizard of Chaos#2459** or **virtuNat#7998**.\n\n'
            f'**Command List:**',
        color=ctx.author.color,
        timestamp=ctx.message.created_at,
        ).set_author(
        name='Help message'
        ).add_field(
        name='`help`',
        value='Display this message.',
        inline=False,
        ).add_field(
        name='`info [user]`',
        value='Grabs user information. Leave user field empty to get your own info.',
        inline=False,
        ).add_field(
        name='`role (subcommand) [args...]`',
        value='Provides help for the role command group.',
        inline=False,
        ).add_field(
        name='`ping`',
        value='Pings the user.',
        inline=False,
        ).add_field(
        name='`fle%`',
        value='Provides you with STRONG eye candy.',
        inline=False,
        ).add_field(
        name='`husky`',
        value='Provides you with an image of a corpulent canine.',
        inline=False,
        ).add_field(
        name='`roll <n>d<f>[(+|-)<m>]`',
        value='Try your luck! Roll n f-faced dice, and maybe add a modifier m!',
        inline=False,
        ).add_field(
        name='`latex <latex_code>`',
        value='Presents a pretty little image for your latex code.',
        inline=False,
        ).add_field(
        name='`linky`',
        value='<:drewkas:684981372678570023>',
        inline=False,
        ))

@userhelp.error
async def userhelp_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command()
@commands.bot_has_permissions(send_messages=True)
async def info(ctx, *, name=None):
    if name is None:
        member = ctx.author
    elif (member := await commands.MemberConverter().convert(ctx, name)) is None:
        await ctx.send('D--> It seems that user can\'t be found. Please check your spelling.')
        return
    now = datetime.utcnow()
    firstjoin = member_stalker.get('first_join', member) or member.joined_at
    embed = dc.Embed(color=member.color, timestamp=now)
    embed.set_author(name=f'Information for {member}')
    embed.set_thumbnail(url=member.avatar_url)
    if ctx.author != member and ctx.author != bot.user:
        lastseen = member_stalker.get('last_seen', member)
        if lastseen is not None:
            lastseenmsg = (
                f'This user was last seen on `{lastseen.strftime("%d/%m/%Y %H:%M:%S")}` '
                f'({max(0, (now-lastseen).days)} days ago)'
                )
        else:
            lastseenmsg = 'This user has not spoken to my knowledge!'
        embed.add_field(name='Last Seen:', value=lastseenmsg, inline=False)
    embed.add_field(
        name='Account Created On:',
        value=f"`{member.created_at.strftime('%d/%m/%Y %H:%M:%S')}` "
        f'({(now-member.created_at).days} days ago)'
        )
    embed.add_field(
        name='Guild Last Joined On:',
        value=f"`{member.joined_at.strftime('%d/%m/%Y %H:%M:%S')}` "
        f'({(now-member.joined_at).days} days ago, {(now-firstjoin).days} days since first recorded join)'
        )
    embed.add_field(name='User ID:', value=f'`{member.id}`', inline=False)
    embed.add_field(
        name='Roles:',
        value=', '.join(f'`{role.name}`' for role in member.roles[1:]) or None,
        inline=False
        )
    if bot.user == member:
        msg = 'D--> Do you wish to check out my STRONG muscles?'
    elif ctx.author != member:
        msg = 'D--> It seems you\'re a bit of a stalker, aren\'t you?'
    else:
        msg = 'D--> I understand the need to look at yourself in the mirror.'
    await ctx.send(msg, embed=embed)

@info.error
async def info_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command(name='fle%')
@commands.bot_has_permissions(send_messages=True)
async def flex(ctx):
    await ctx.send(
        embed=dc.Embed(
            color=ctx.guild.get_member(bot.user.id).color,
            description='D--> It seems you have STRONGLY requested to gaze upon my beautiful body, '
            'and who am I to refuse such a request?'
            ).set_author(
            name='D--> I STRONGLY agree.', icon_url=bot.user.avatar_url
            ).set_image(
            url='https://cdn.discordapp.com/attachments/'
            '390337910244769792/704686351228076132/arquius_smooth.gif'
            ))

@flex.error
async def flex_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command(name='tag', aliases=['tc', 'tt'])
@commands.bot_has_permissions(send_messages=True)
async def deny_old_tags(ctx):
    await ctx.send(
        embed=dc.Embed(
            color=ctx.guild.get_member(bot.user.id).color,
            description='D--> I would never stoop so low as to entertain the likes of this. '
            'You are STRONGLY recommended to instead gaze upon my beautiful body.'
            ).set_author(
            name='D--> No.', icon_url=bot.user.avatar_url
            ).set_image(
            url='https://cdn.discordapp.com/attachments/'
            '152981670507577344/664624516370268191/arquius.gif'
            ))

@deny_old_tags.error
async def deny_old_tags_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command(name='husky', aliases=['fathusky', 'fatHusky'])
@commands.bot_has_permissions(send_messages=True)
async def post_fat_husky(ctx):
    await ctx.send(
        embed=dc.Embed(
            color=ctx.guild.get_member(bot.user.id).color,
            ).set_author(
            name='D--> A corpulent canine.', 
            icon_url='https://cdn.discordapp.com/attachments/'
            '663453347763716110/773577148577480754/unknown.png',
            ).set_image(
            url='https://cdn.discordapp.com/attachments/'
            '663453347763716110/773574707231457300/dogress.png',
            ))

@post_fat_husky.error
async def post_fat_husky_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command(name='ping', aliases=['p'])
@commands.bot_has_permissions(send_messages=True)
async def reflect_ping(ctx):
    await ctx.send(f'D--> {ctx.author.mention}')

@reflect_ping.error
async def reflect_ping_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command(name='roll', aliases=['r'])
@commands.bot_has_permissions(send_messages=True)
async def dice_roller(ctx, *, args):
    if not (match := re.match(r'(\d+)\s*d\s*(\d+)\s*(?:([-+])\s*(\d+))?$', args.strip())):
        await ctx.send('D--> Use your words, straight from the horse\'s mouth.')
        return
    ndice, nfaces, sign, mod = (group or '0' for group in match.groups())
    ndice, nfaces = int(ndice), int(nfaces)
    # Stop people from doing the 0 dice 0 faces bullshit
    if ndice <= 0 or nfaces <= 0:
        await ctx.send('D--> That doesn\'t math very well. I STRONGLY suggest you try again.')
        return
    modnum = int(sign + mod)
    # Precalc minimum length to see if roll should go
    if modnum:
        bfr = f'{ctx.author.mention} **rolled {ndice}d{nfaces}{sign}{mod}:** `('
        aft = f') {sign} {mod} = '
    else:
        bfr = f'{ctx.author.mention} **rolled {ndice}d{nfaces}:** `('
        aft = f') = '
    if len(bfr+aft) + 3*(ndice-1) > 2000:
        await ctx.send(
            'D--> Woah there pardner, that\'s a few too many dice '
            'or a few too large a die. Try again with something smaller.'
            )
        return
    # Do the rolls
    if ndice == nfaces == 8 and ctx.author.id == CONST_AUTHOR[0]:
        rolls = [8] * 8
    else:
        rolls = [random.randint(1, nfaces) for _ in range(ndice)]
    msg = f'{bfr}{" + ".join(map(str, rolls))}{aft}{sum(rolls) + modnum}`'
    if len(msg) > 2000:
        await ctx.send(
            'D--> Woah there pardner, that\'s a few too many dice '
            'or a few too large a die. Try again with something smaller.'
            )
        return
    embed = dc.Embed(
        color=dc.Color(0x005682),
        description=f'`Min: {min(rolls)}; Max: {max(rolls)}; '
            f'Mean: {sum(rolls) / ndice:0.2f}; 1st Mode: {max(set(rolls), key=rolls.count)}`',
        )
    embed.set_author(
        name='Roll Statistics:',
        icon_url='https://cdn.discordapp.com/attachments/'
            '663453347763716110/711985889680818266/unknown.png',
        )
    await ctx.send(msg, embed=embed)

@dice_roller.error
async def dice_roller_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

default_preamble = (
    r'\documentclass{standalone}\usepackage{color}\usepackage{amsmath}'
    r'\color{white}\begin{document}\begin{math}\displaystyle '
    )
default_postamble = r'\end{math}\end{document}'

@bot.command(name='latex', aliases=['l'])
@commands.bot_has_permissions(send_messages=True)
async def render_latex(ctx, *, raw_latex=''):
    if not guild_config.getltx(ctx) or not raw_latex:
        return
    with ctx.channel.typing():
        if (image := await grab_latex(default_preamble, default_postamble, raw_latex)) is None:
            await ctx.send('D--> Your latex code is beneighth contempt. Try again.')
            return
        # Send the image to the latex channel and embed.
        latex_channel = bot.get_channel(773594582175973376)
        msg_id = hex(member_stalker.member_data['latex_count'])[2:]
        member_stalker.member_data['latex_count'] += 1
        await latex_channel.send(
            f'`@{ctx.author}`: UID {ctx.author.id}: MID {msg_id}',
            file=dc.File(io.BytesIO(await image.read()), 'latex.png')
            )
        async for msg in latex_channel.history(limit=16):
            if msg.content.split()[-1] == msg_id:
                latex_image_url = msg.attachments[0].url
                break
        embed = dc.Embed(
            color=ctx.author.color,
            timestamp=datetime.utcnow(),
            )
        embed.set_author(
            name=f'D--> Latex render for {ctx.author}',
            icon_url='https://cdn.discordapp.com/attachments/'
            '663453347763716110/773600642752839700/stsmall507x507-pad600x600f8f8f8.png',
            )
        embed.set_image(url=latex_image_url)
        await ctx.send(embed=embed)
        await ctx.message.delete()

@render_latex.error
async def render_latex_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command(name='linky', aliases=['8ball'])
@commands.bot_has_permissions(send_messages=True)
async def magic_8ball(ctx, *, query=''):
    await aio.sleep(0)
    msg = re.sub(r'<@!(\d{18,})>', get_name, guild_config.random_linky(ctx.message.content))
    msg = re.sub(r'(?<!<)(https?://[^\s]+)(?!>)', r'<\1>', msg)
    admin = ctx.guild.get_member(CONST_ADMINS[1])
    embed = dc.Embed(
        color=admin.color if admin else dc.Color.green(),
        description=msg,
        )
    embed.set_author(
        name=f'{admin.name if admin else "Linky"} says:',
        icon_url=admin.avatar_url if admin else (
            'https://cdn.discordapp.com/attachments/'
            '663453347763716110/776420647625949214/Linky.gif'
            ),
        )
    await ctx.send(embed=embed)

@magic_8ball.error
async def magic_8ball_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command(name='suggest')
@commands.bot_has_permissions(send_messages=True)
async def suggest_to_dev(ctx, *, suggestion: str):
    suggestions = bot.get_channel(777555413213642772)
    suggest_id = ctx.message.id
    embed = dc.Embed(
        color=dc.Color.red(),
        description=suggestion,
        timestamp=datetime.utcnow(),
        )
    embed.set_author(
        name=f'{ctx.author} suggests:'
        )
    embed.add_field(
        name='**Message ID:**',
        value=f'`{suggest_id}`',
        inline=False,
        )
    await suggestions.send(embed=embed)
    await ctx.send(f'D--> Your suggestion has been noted.')
    stored_suggestions.add_suggestion(suggest_id, ctx.author.id, ctx.channel.id) 

@suggest_to_dev.error
async def suggest_to_dev_error(ctx, error):
    raise error

@bot.command(name='respond')
@commands.bot_has_permissions(send_messages=True)
async def response_from_dev(ctx, msg_id: int, *, response: str):
    if ctx.author.id not in CONST_AUTHOR:
        return
    try:
        channel, member = stored_suggestions.get_suggestion(bot, msg_id)
    except KeyError:
        await ctx.send('D--> Suggestion does not exist.')
        return
    async for msg in bot.get_channel(777555413213642772).history(limit=None):
        if msg.author.id != bot.user.id:
            continue
        if not msg.embeds:
            continue
        embed = msg.embeds[0]
        suggestion = embed.description
        if not embed.fields:
            continue
        if embed.fields[0].value == f'`{msg_id}`':
            break
    embed = dc.Embed(
        color=member.color,
        description=response,
        timestamp=datetime.utcnow(),
        )
    embed.set_author(
        name='D--> In response to your suggestion, the devs say:',
        icon_url=bot.user.avatar_url,
        )
    embed.add_field(
        name='Suggestion:',
        value=suggestion,
        inline=False,
        )
    await channel.send(f'{member.mention}', embed=embed)
    stored_suggestions.remove_suggestion(msg_id)

@response_from_dev.error
async def response_from_dev_error(ctx, error):
    raise error
