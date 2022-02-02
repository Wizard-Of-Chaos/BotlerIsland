# Moderation data classes
import os
import pickle
from datetime import datetime
from collections import defaultdict

import discord as dc
from discord.ext import commands

from cogs_textbanks import query_bank, response_bank

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

def guild_callback():
    return {'first_join': None, 'last_seen': None, 'last_roles': ()}

def member_callback():
    return defaultdict(guild_callback)

    
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
