import pickle
import discord as dc

class GuildConfig(object):
    def __init__(self, bot, fname):
        self.bot = bot
        self.fname = fname
        self.load()

    def load(self):
        try:
            with open(self.fname, 'rb') as config_file:
                self.mod_channels = pickle.load(config_file)
        except (OSError, EOFError):
            self.mod_channels = {
                guild.id: {'usrlog': None, 'msglog': None}
                for guild in self.bot.guilds
                }
            self.save()

    def save(self):
        with open(self.fname, 'wb') as config_file:
            pickle.dump(self.mod_channels, config_file)

    def setlog(self, ctx, log):
        try:
            guild = ctx.guild
        except AttributeError:
            return 'Log cannot be set in this channel!'
        try:
            self.mod_channels[guild.id][log] = ctx.channel.id
        except KeyError:
            if log == 'usrlog':
                self.mod_channels[guild.id] = {'usrlog': ctx.channel.id, 'msglog': None}
            elif log == 'msglog':
                self.mod_channels[guild.id] = {'usrlog': None, 'msglog': ctx.channel.id}
            else:
                raise ValueError(f'Invalid log channel type {log}')
        self.save()
        return 'Log channel has been set and saved!'
