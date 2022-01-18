# Moderation data classes
import os
import pickle
from datetime import datetime
from collections import defaultdict

import discord as dc
from discord.ext import commands

from cogs_textbanks import query_bank, response_bank

guild_whitelist = (
    152981670507577344, 663452978237407262, 402880303065989121, 431698070510501891,
    )

class CogtextManager(commands.Cog):

    @staticmethod
    def _generate_empty():
        return None

    def __init__(self, bot):
        self._fname = os.path.join('data', self.__class__.__name__+'.pkl')
        self.bot = bot
        self.data_load()

    def cleanup_on_save(self):
        """
        This function is called to clean up empty entries to minimize space.
        """

    def cleanup_on_load(self):
        """
        This function is called to modify data structure between refactors to ensure continuity.
        """

    def data_save(self):
        """
        Save the data file. Currently uses pickle, which isn't the smartest format.
        This will work for now.
        """
        self.cleanup_on_save()
        with open(self._fname, 'wb') as data_file:
            pickle.dump(self.data, data_file)

    def data_load(self):
        """Load from the data file."""
        try:
            with open(self._fname, 'rb') as data_file:
                self.data = pickle.load(data_file)
        except (OSError, EOFError):
            self.data = self._generate_empty()
            with open(self._fname, 'wb') as data_file:
                pickle.dump(self.data, data_file)
        else:
            self.cleanup_on_load()

    def cog_unload(self):
        """Ensures saving of the updated data."""
        self.data_save()


class Singleton(object):
    _self_instance_ref = None
    def __new__(cls, *args, **kwargs):
        if cls._self_instance_ref is None:
            cls._self_instance_ref = super().__new__(cls)
        return cls._self_instance_ref


def callback(): # Lambdas can't be pickled, but named functions can.
    return {
        'usrlog': None, 'msglog': None, 'modlog': None,
        'autoreact': set(), 'ignoreplebs': set(), 'enablelatex': set(),
        }

# modref = dc.Permissions(
#     administrator=True, manage_channels=True,
#     manage_roles=True, manage_nicknames=True,
#     )

# class GuildConfig(Singleton):
#     def __init__(self, bot, fname):
#         self.bot = bot
#         self.fname = os.path.join('data', fname)
#         self.load()

#     def __enter__(self):
#         return self

#     def __exit__(self, etype, evalue, etrace):
#         self.save()

#     def save(self):
#         with open(self.fname, 'wb') as config_file:
#             pickle.dump(self.mod_channels, config_file)

#     def load(self):
#         try:
#             with open(self.fname, 'rb') as config_file:
#                 self.mod_channels = pickle.load(config_file)
#         except (OSError, EOFError):
#             self.mod_channels = defaultdict(callback)
#             self.save()
#         else:
#             self.mod_channels.default_factory = callback
#             for guild_id, config in self.mod_channels.copy().items():
#                 if guild_id not in guild_whitelist:
#                     del self.mod_channels[guild_id]
#                     continue
#             self.save()

#     async def log(self, guild, log, *args, **kwargs):
#         channel_id = self.mod_channels[guild.id][log]
#         await self.bot.get_channel(channel_id).send(*args, **kwargs)

#     def getlog(self, guild, log):
#         return self.mod_channels[guild.id][log]

#     def getcmd(self, ctx):
#         perms = ctx.author.guild_permissions
#         return ((perms.value & modref.value)
#             or ctx.channel.id not in self.mod_channels[ctx.guild.id]['ignoreplebs']
#             )

#     def getltx(self, ctx):
#         perms = ctx.author.guild_permissions
#         return ((perms.value & modref.value)
#             or ctx.channel.id in self.mod_channels[ctx.guild.id]['enablelatex']
#             )

#     async def setlog(self, ctx, log):
#         if log not in ('usrlog', 'msglog', 'modlog'):
#             await ctx.send(response_bank.config_args_error.format(log=log))
#             return
#         self.mod_channels[ctx.guild.id][log] = ctx.channel.id
#         self.save()
#         await ctx.send(response_bank.config_completion.format(log=log))

#     def toggle(self, ctx, field):
#         config = self.mod_channels[ctx.guild.id][field]
#         channel_id = ctx.channel.id
#         if channel_id in config:
#             config.remove(channel_id)
#             return False
#         else:
#             config.add(channel_id)
#             return True


def guild_callback():
    return {'first_join': None, 'last_seen': None, 'last_roles': ()}

def member_callback():
    return defaultdict(guild_callback)

class MemberStalker(Singleton):
    def __init__(self, fname):
        self.fname = os.path.join('data', fname)
        self.load()

    def __enter__(self):
        return self

    def __exit__(self, etype, evalue, etrace):
        self.save()

    def save(self):
        with open(self.fname, 'wb') as member_file:
            pickle.dump(self.member_data, member_file)

    def load(self):
        try:
            with open(self.fname, 'rb') as member_file:
                self.member_data = pickle.load(member_file)
        except (OSError, EOFError):
            self.member_data = defaultdict(member_callback, {'avatar_count': 0, 'latex_count': 0})
        else:
            self.member_data.default_factory = member_callback
        self.save()

    def get(self, field, member):
        return self.member_data[member.id][member.guild.id][field]

    def update(self, field, data):
        if field == 'first_join': # data is a discord.Member instance
            member_data = self.member_data[data.id][data.guild.id]
            if not member_data[field]:
                member_data[field] = data.joined_at
        elif field == 'last_seen': # data is a discord.Message instance
            self.member_data[data.author.id][data.guild.id][field] = data.created_at
        elif field == 'last_roles': # data is a discord.Member instance
            self.member_data[data.id][data.guild.id][field] = tuple(role.id for role in data.roles[1:])

    async def load_roles(self, member):
        await member.add_roles(
            *map(member.guild.get_role, self.member_data[member.id][member.guild.id]['last_roles']),
            reason='Restore last roles'
            )

    
class Suggestions(Singleton):
    def __init__(self, fname):
        self.fname = os.path.join('data', fname)
        self.load()

    def __enter__(self):
        return self

    def __exit__(self, etype, evalue, etrace):
        self.save()
        
    def load(self):
        try:
            with open(self.fname, 'rb') as suggests:
                self.suggestions = pickle.load(suggests)
            if isinstance(self.suggestions, defaultdict):
                self.suggestions = dict(self.suggestions)
        except (OSError, EOFError):
            self.suggestions = {}
            self.save()

    def save(self):
        with open(self.fname, 'wb') as suggests:
            pickle.dump(self.suggestions, suggests)
            
    def add_suggestion(self, msg_id, author, channel):
        self.suggestions[msg_id] = (channel, author)
        self.save()

    def get_suggestion(self, ctx, msg_id):
        chn_id, usr_id = self.suggestions[msg_id]
        channel = ctx.get_channel(chn_id)
        return (channel, channel.guild.get_member(usr_id))
        
    def remove_suggestion(self, msg_id):
        removed = self.suggestions.pop(msg_id)
