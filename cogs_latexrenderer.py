# Latex Rendering Cog.
# GuildConfig contains channel metadata regarding which channels enable this feature to avoid spamming the server.
import io
import json
import ssl
import aiohttp
import certifi
from datetime import datetime

import discord as dc
from discord.ext import commands, tasks

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot, CogtextManager
import cogs_guildconfig


class LatexRenderer(commands.Cog):
    default_preamble = (
        r'\documentclass{standalone}\usepackage{color}\usepackage{amsmath}'
        r'\color{white}\begin{document}\begin{math}\displaystyle '
        )
    default_postamble = r'\end{math}\end{document}'

    def __init__(self, bot):
        self.bot = bot
        self.guild_config = bot.get_cog('GuildConfiguration')
        if self.guild_config is None:
            raise RuntimeError(response_bank.unexpected_state)

        self.preamble = self.default_preamble
        self.postamble = self.default_postamble

    @staticmethod
    async def grab_latex(raw_latex, preamble=default_preamble, postamble=default_postamble):
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        conn = aiohttp.TCPConnector(ssl=ssl_context)

        async with aiohttp.ClientSession(connector=conn) as session:
            resp = await session.post(
                url_bank.latex_parser,
                data={'format': 'png', 'code': preamble+raw_latex+postamble},
                )
            resp = await resp.text() # Awaiting loading of the raw text data and unicode parsing
            resp = json.loads(resp)
            if (resp['status'] != 'success'):
                return None
            return await session.get(f'{url_bank.latex_parser}/{resp["filename"]}')

    @commands.command(name='latex', aliases=['l'])
    @commands.bot_has_permissions(send_messages=True)
    async def render_latex(self, ctx, *, raw_latex=''):
        if not raw_latex:
            return
        if not self.guild_config.channel_toggles.check_enabled(ctx.message, 'enablelatex'):
            return
        with ctx.channel.typing():
            if (image := await self.grab_latex(raw_latex, self.preamble, self.postamble)) is None:
                await ctx.send(response_bank.render_latex_args_error)
                return
            # Send the image to the latex channel and embed.
            latex_channel = bot.get_channel(773594582175973376)
            msg_id = f'{self.guild_config.global_metadata.get_record_id("latex_count"):x}'
            await latex_channel.send(
                f'`@{ctx.author}`: UID {ctx.author.id}: MID {msg_id}',
                file=dc.File(io.BytesIO(await image.read()), 'latex.png')
                )
            async for msg in latex_channel.history(limit=16):
                if msg.content.split()[-1] == msg_id:
                    latex_att = msg.attachments[0]
                    break
            embed = dc.Embed(
                color=ctx.author.color,
                timestamp=datetime.utcnow(),
                )
            embed.set_author(
                name=response_bank.render_latex_head.format(ctx=ctx),
                icon_url=url_bank.latex_icon,
                )
            embed.set_image(url=latex_att.url)
            await ctx.send(embed=embed)
        await ctx.message.delete()

    @render_latex.error
    async def render_latex_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            return
        raise error


bot.add_cog(LatexRenderer(bot))
