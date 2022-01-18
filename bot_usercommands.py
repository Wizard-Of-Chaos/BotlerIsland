# For most public commands.
import re
import random
from datetime import datetime

import asyncio as aio
import aiohttp

import discord as dc
from discord.ext import commands

from cogs_textbanks import url_bank, query_bank, husky_bank, response_bank, beeger_bank
from bot_common import bot, CONST_ADMINS, CONST_AUTHOR, member_stalker, stored_suggestions

suggest_chid = 777555413213642772

def get_name(member_id):
    return str(bot.get_user(int(member_id[1])))

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

dt_format = '%d/%m/%Y at %H:%M:%S UTC'

@bot.command(aliases=['peek'])
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
                f'```{lastseen.strftime(dt_format)}\n'
                f'{max(0, (now-lastseen).days)} day(s) ago```'
                )
        else:
            lastseenmsg = '```This user has not spoken to my knowledge!```'
        embed.add_field(name='This user was last seen on:', value=lastseenmsg, inline=False)
    embed.add_field(
        name='Account Created On:',
        value=f'```{member.created_at.strftime(dt_format)}\n'
        f'{(now-member.created_at).days} day(s) ago```'
        )
    embed.add_field(
        name='Guild Last Joined On:',
        value=f'```{member.joined_at.strftime(dt_format)}\n'
        f'{(now-member.joined_at).days} day(s) ago,\n'
        f'{(now-firstjoin).days} day(s) since first recorded join```'
        )
    embed.add_field(name='User ID:', value=f'`{member.id}`', inline=False)
    embed.add_field(
        name='Roles:',
        value='```'+(', '.join(role.name for role in member.roles[:0:-1]) or 'No roles.')+'```',
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

@bot.command(aliases=['fle%', 'pose'])
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
            url=url_bank.flexing_bot
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
            url=url_bank.flexing_bot
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
            icon_url=husky_bank.icon,
            ).set_image(
            url=husky_bank.body,
            ))

@bot.command(name='beeger', aliases=['ups to beeger', 'big ups to beeger'])
@commands.bot_has_permissions(send_messages=True)
async def ups_to_beeger(ctx):
    await ctx.send(
        embed=dc.Embed(
            color=ctx.guild.get_member(bot.user.id).color,
            ).set_author(
            name='D--> Big ups to Beeger.', 
            icon_url=beeger_bank.icon,
            ).set_image(
            url=beeger_bank.body,
            ))

@post_fat_husky.error
async def post_fat_husky_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@ups_to_beeger.error
async def ups_to_beeger_error(ctx, error):
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
        icon_url=url_bank.roll_icon,
        )
    await ctx.send(msg, embed=embed)

@dice_roller.error
async def dice_roller_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        return
    raise error

@bot.command(name='github')
@commands.bot_has_permissions(send_messages=True)
async def pull_request(ctx):
    await ctx.send(embed=dc.Embed(
        color=ctx.guild.get_member(bot.user.id).color,
        description=(
            'Do you have a friend or a relative who would '
            'make a valuable contribution to the bot?\n'
            'In that case, tell them to submit a pull request '
            'for their new feature to: <https://github.com/Wizard-Of-Chaos/BotlerIsland>.\n'
            'Botler Island is the beta version of Arquius. '
            'If you want us to include your feature in the bot, send it there.\n'
        )).set_author(
        name='Got a feature?',
        icon_url=bot.user.avatar_url,
        ))

@bot.command(name='suggest')
@commands.bot_has_permissions(send_messages=True)
async def suggest_to_dev(ctx, *, suggestion: str):
    suggestions = bot.get_channel(suggest_chid)
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
    async for msg in bot.get_channel(suggest_chid).history(limit=None):
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
    else:
        await ctx.send('D--> Suggestion does not exist.')
        stored_suggestions.remove_suggestion(msg_id)
        return
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
