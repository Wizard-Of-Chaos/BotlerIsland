from datetime import datetime, timedelta
from collections import defaultdict, deque
import re
import pickle
import discord as dc
from discord.ext import tasks, commands

def callback(): # Lambdas can't be pickled, but named functions can.
    return {'usrlog': None, 'msglog': None, 'modlog': None, 'star_wars': None} #Added an additional log for bans applied.

class Singleton(object):
    instance = None
    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance


class GuildConfig(Singleton):
    def __init__(self, bot, fname):
        StarWarsPunisher.bot = bot
        self.bot = bot
        self.fname = fname
        self.punishers = {}
        self.load()

    def load(self):
        try:
            with open(self.fname, 'rb') as config_file:
                self.mod_channels = pickle.load(config_file)
            for guild, config in self.mod_channels.items():
                if 'modlog' not in config:
                    config['modlog'] = None
            self.save()
        except (OSError, EOFError):
            self.mod_channels = defaultdict(callback, {})
        self.save()

    def save(self):
        for guild_id, config in self.mod_channels.items():
            try:
                config['star_wars'] = self.punishers[guild_id].dump()
            except KeyError:
                if 'star_wars' not in config:
                    config['star_wars'] = None
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

    def set_containment(self, ctx):
        guild_id = ctx.guild.id
        star_wars = self.mod_channels[guild_id]['star_wars']
        if star_wars is None:
            self.punishers[guild_id] = StarWarsPunisher(guild_id)
            self.save()
        elif guild_id not in self.punishers:
            self.punishers[guild_id] = StarWarsPunisher(
                guild_id, star_wars['banlist'], star_wars['lastcall']
                )
        self.punishers[guild_id].monitor(ctx)

    def detect_star_wars(self, msg):
        if msg.guild.id not in self.punishers:
            return False
        return self.punishers[msg.guild.id].detect(msg)

    async def punish_star_wars(self, msg):
        dt = await self.punishers[msg.guild.id].punish(msg)
        self.save()
        return dt


triggers = [*map(re.compile, (
    r'\bstar\s*wars?\b', r'\bskywalker\b', r'\banakin\b', r'\bjedi\b',
    r'\bpod racing\b', r'\byoda\b', r'\bdarth\b', r'\bvader\b',
    r'\bewoks?\b', r'\bwookiee?s?\b', r'\bchewbacca\b', r'\bdeath star\b',
    r'\bmandalorian\b', r'\bobi wan( kenobi)?\b', r'\b(ha|be)n solo\b', r'\bkylo ren\b',
    r'\bforce awakens?\b', r'\bempire strikes? back\b', r'\bat[- ]st\b', r'\bgeorge lucas\b',
    r'\bgeneral grievous\b', r'\bsheev( palpatine)?\b', r'\b(emperor )?palpatine\b',
    ))]

class StarWarsPunisher(commands.Cog):
    def __init__(self, guild_id, banlist=None, lastcall=None):
        self.guild = self.bot.get_guild(guild_id)
        self.banlist = banlist or deque([])
        self.lastcall = lastcall
        self.order66 = None
        self.role = dc.utils.find(
            lambda r: 'star wars' in r.name.lower(),
            self.guild.roles
            )

    def dump(self):
        return {
            'guild': self.guild.id,
            'banlist': self.banlist,
            'lastcall': self.lastcall,
            }

    def monitor(self, ctx):
        if self.order66 is None:
            self.manage_bans.start()
        self.order66 = (ctx.channel.id, ctx.message.created_at+timedelta(minutes=5))

    def detect(self, msg):
        content = msg.content.lower()
        return bool(self.order66
            and msg.channel.id == self.order66[0]
            and (msg.author.id == 207991389613457408
                or any(pattern.search(content) for pattern in triggers)
                ))

    async def punish(self, msg):
        await msg.author.add_roles(self.role, reason='Star Wars.')
        self.banlist.append((msg.author.id, msg.created_at+timedelta(minutes=30)))
        if self.lastcall is None:
            dt = None
        else:
            dt = msg.created_at - self.lastcall
        self.lastcall = msg.created_at
        return dt

    @tasks.loop(seconds=5.0)
    async def manage_bans(self):
        if self.banlist and self.banlist[0][1] < datetime.utcnow():
            await self.guild.get_member(self.banlist.popleft()[0]).remove_roles(
                self.role, reason='Star Wars timeout.'
                )
        if self.order66 is not None:
            if self.order66[1] < datetime.utcnow():
                await self.bot.get_channel(self.order66[0]).send(
                    'D--> It is done, my lord.'
                    )
                self.order66 = None
        elif not self.banlist:
            self.manage_bans.cancel()


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


def data_callback():
    return {'last_seen': None, 'first_join': None}

def member_callback():
    return defaultdict(data_callback, {})

class MemberStalker(object):
    def __init__(self, fname):
        self.fname = fname
        self.load()

    def load(self):
        try:
            with open(self.fname, 'rb') as role_file:
                self.member_data = pickle.load(role_file)
            self.member_data = defaultdict(member_callback, self.member_data)
            for guild, members in self.member_data.items():
                if isinstance(members, dict): continue
                for member, data in members.items():
                    members[member] = {'last_seen': data, 'first_join': None}
            self.save()
        except (OSError, EOFError):
            self.member_data = defaultdict(member_callback, defaultdict(data_callback, {}))
            self.save()

    def save(self):
        with open(self.fname, 'wb') as role_file:
            pickle.dump(self.member_data, role_file)

    def get(self, log, member):
        return self.member_data[member.guild.id][member.id][log]

    def update(self, log, msg):
        member_data = self.member_data[msg.guild.id][msg.author.id]
        if log == 'first_join' and member_data[log]:
            return
        member_data[log] = msg.created_at
