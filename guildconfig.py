from collections import defaultdict
import pickle
import discord as dc

def callback(): # Lambdas can't be pickled, but named functions can.
    return {'usrlog': None, 'msglog': None}

class GuildConfig(object):
    def __init__(self, bot, fname):
        self.bot = bot
        self.fname = fname
        self.load()

    def load(self):
        try:
            with open(self.fname, 'rb') as config_file:
                self.mod_channels = pickle.load(config_file)
            if not isinstance(self.mod_channels, defaultdict):
                self.mod_channels = defaultdict(callback, self.mod_channels)
                self.save()
        except (OSError, EOFError):
            self.mod_channels = defaultdict(callback, {})
            self.save()

    def save(self):
        with open(self.fname, 'wb') as config_file:
            pickle.dump(self.mod_channels, config_file)

    async def log(self, guild, log, *args, **kwargs):
        await self.bot.get_channel(
            self.mod_channels[guild.id][log]
            ).send(*args, **kwargs)

    def getlog(self, guild, log):
        return self.mod_channels[guild.id][log]

    def setlog(self, ctx, log):
        try:
            guild = ctx.guild
        except AttributeError:
            return 'Log cannot be set in this channel!'
        try:
            self.mod_channels[guild.id][log] = ctx.channel.id
        except KeyError:
            raise ValueError(f'Invalid log channel type {log}')
        self.save()
        return 'Log channel has been set and saved!'
