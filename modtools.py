from collections import defaultdict
import pickle
import discord as dc

triggers = (
    'star wars', 'starwars', 'star war', 'starwar',
    'ewok', 'wookie', 'wookiee', 'chewbacca', 'pod racing', 'skywalker',
    )

def callback(): # Lambdas can't be pickled, but named functions can.
    return {'usrlog': None, 'msglog': None, 'star_wars': None}

class GuildConfig(object):
    def __init__(self, bot, fname):
        self.bot = bot
        self.fname = fname
        self.load()

    def load(self):
        try:
            with open(self.fname, 'rb') as config_file:
                self.mod_channels = pickle.load(config_file)
            for guild in self.mod_channels.values():
                if 'star_wars' not in guild:
                    guild['star_wars'] = None
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

    def set_containment(self, ctx, role):
        channel = ctx.channel
        self.mod_channels[channel.guild.id]['star wars'] = {
            'sentinel': channel.id,
            'role': role.id,
            'lastcall': None,
            }
        self.save()

    def detect_star_wars(self, msg):
        star_wars = self.mod_channels[msg.guild.id]['star wars']
        if star_wars is None:
            return False
        return (msg.channel.id == star_wars['sentinel'] 
            and any(map(msg.content.lower().__contains__, triggers))
            )

    async def punish_star_wars(self, msg):
        star_wars = self.mod_channels[msg.guild.id]['star wars']
        await msg.author.add_roles(
            msg.guild.get_role(star_wars['role']),
            reason='Star Wars.',
            )
        if star_wars['lastcall'] is None:
            dt = None
        else:
            dt = msg.created_at - star_wars['lastcall']
        star_wars['lastcall'] = msg.created_at
        self.save()
        return dt


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
