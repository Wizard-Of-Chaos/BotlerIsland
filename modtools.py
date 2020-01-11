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
            self.mod_channels[ctx.guild.id][log] = ctx.channel.id
        except KeyError:
            raise ValueError(f'Invalid log channel type {log}')
        self.save()


class RoleSaver(object):
    def __init__(self, fname):
        self.fname = fname
        self.load()

    def load(self):
        try:
            with open(self.fname, 'rb') as role_file:
                self.user_roles = pickle.load(role_file)
        except (OSError, EOFError):
            self.user_roles = defaultdict(dict, {})
            self.save()

    def save(self):
        with open(self.fname, 'wb') as role_file:
            pickle.dump(self.user_roles, role_file)

    def get_roles(self, member):
        return self.user_roles[member.guild.id][member.id]

    async def load_roles(self, member):
        try:
            roles = self.user_roles[member.guild.id][member.id]
        except KeyError:
            return
        await member.add_roles(
            *map(member.guild.get_role, roles),
            reason='Restore roles'
            )

    def save_roles(self, member):
        self.user_roles[member.guild.id][member.id] = [role.id for role in member.roles[1:]]
        self.save()


class MemberStalker(object):
    def __init__(self, fname):
        self.fname = fname
        self.load()

    def load(self):
        try:
            with open(self.fname, 'rb') as role_file:
                self.last_msgs = pickle.load(role_file)
        except (OSError, EOFError):
            self.last_msgs = defaultdict(dict, {})
            self.save()

    def save(self):
        with open(self.fname, 'wb') as role_file:
            pickle.dump(self.last_msgs, role_file)

    def get(self, member):
        try:
            return self.last_msgs[member.guild.id][member.id]
        except KeyError:
            return None

    def update(self, msg):
        if msg.guild is None:
            return
        self.last_msgs[msg.guild.id][msg.author.id] = msg.created_at
