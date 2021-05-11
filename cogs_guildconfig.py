# Guild Configuration Cog, for managing guild settings and bot features.
import os

import discord as dc
from discord.ext import commands, tasks

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot, CogtextManager

modref = dc.Permissions(
    administrator=True, manage_channels=True,
    manage_roles=True, manage_nicknames=True,
    )


class GuildConfiguration(CogtextManager):

    @staticmethod
    def generate_empty():
        return {
            'usrlog': None, 'msglog': None, 'modlog': None,
            'autoreact': set(), 'ignoreplebs': set(), 'enablelatex': set(),
            }

    def cleanup_on_load(self):
        try:
            with open(self.fname, 'rb') as config_file:
                self.mod_channels = pickle.load(config_file)
        except (OSError, EOFError):
            self.mod_channels = defaultdict(callback)
            self.save()
        else:
            self.mod_channels.default_factory = callback
            for guild_id, config in self.mod_channels.copy().items():
                if guild_id not in guild_whitelist:
                    del self.mod_channels[guild_id]
                    continue
            self.save()

    async def log(self, guild, log, *args, **kwargs):
        channel_id = self.mod_channels[guild.id][log]
        await self.bot.get_channel(channel_id).send(*args, **kwargs)

    def getlog(self, guild, log):
        return self.mod_channels[guild.id][log]

    def getcmd(self, ctx):
        perms = ctx.author.guild_permissions
        return ((perms.value & modref.value)
            or ctx.channel.id not in self.mod_channels[ctx.guild.id]['ignoreplebs']
            )

    def getltx(self, ctx):
        perms = ctx.author.guild_permissions
        return ((perms.value & modref.value)
            or ctx.channel.id in self.mod_channels[ctx.guild.id]['enablelatex']
            )

    async def setlog(self, ctx, log):
        if log not in ('usrlog', 'msglog', 'modlog'):
            await ctx.send(response_bank.config_args_error.format(log=log))
            return
        self.mod_channels[ctx.guild.id][log] = ctx.channel.id
        self.save()
        await ctx.send(response_bank.config_completion.format(log=log))

    def toggle(self, ctx, field):
        config = self.mod_channels[ctx.guild.id][field]
        channel_id = ctx.channel.id
        if channel_id in config:
            config.remove(channel_id)
            return False
        else:
            config.add(channel_id)
            return True

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.has_guild_permissions(manage_channels=True)
    async def config(ctx, log: str):
        await guild_config.setlog(ctx, log)

    @config.error
    async def config_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        elif isinstance(error, commands.BotMissingPermissions):
            return
        raise error

    @commands.command()
    @commands.bot_has_permissions(add_reactions=True, read_message_history=True)
    @commands.has_guild_permissions(manage_messages=True)
    async def autoreact(ctx):
        if guild_config.toggle(ctx, 'autoreact'):
            await ctx.send('D--> ❤️')
        else:
            await ctx.send('D--> 💔')

    @autoreact.error
    async def autoreact_error(ctx, error):
        if isinstance(error, BotMissingPermissions):
            return
        elif isinstance(error, MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        raise error

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.has_guild_permissions(manage_roles=True)
    async def ignoreplebs(ctx):
        if guild_config.toggle(ctx, 'ignoreplebs'):
            await ctx.send('D--> I shall listen only to b100 b100ded commands.')
        else:
            await ctx.send('D--> Unfortunately, I must now listen to the lower classes.')

    @ignoreplebs.error
    async def ignoreplebs_error(ctx, error):
        if isinstance(error, MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        raise error

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.has_guild_permissions(manage_roles=True)
    async def togglelatex(ctx):
        if guild_config.toggle(ctx, 'enablelatex'):
            await ctx.send('D--> Latex functions have been enabled.')
        else:
            await ctx.send('D--> Latex functions have been disabled.')
            
    @togglelatex.error
    async def togglelatex_error(ctx, error):
        if isinstance(error, MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        raise error


bot.add_cog(GuildConfiguration(bot))
