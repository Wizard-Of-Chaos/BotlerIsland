from datetime import datetime, timedelta
from collections import defaultdict, deque
from random import randrange
from itertools import islice
import re
import os
import pickle
import discord as dc
from discord.ext import tasks, commands

guild_whitelist = (152981670507577344, 663452978237407262)

def callback(): # Lambdas can't be pickled, but named functions can.
    return {
    'usrlog': None, 'msglog': None, 'modlog': None,
    'autoreact': set(), 'star_wars': {}, 'ignoreplebs': set(),
    }

class Singleton(object):
    _self_instance_ref = None
    def __new__(cls, *args, **kwargs):
        if cls._self_instance_ref is None:
            cls._self_instance_ref = super().__new__(cls)
        return cls._self_instance_ref


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
            for guild, config in self.mod_channels.copy().items():
                if guild not in guild_whitelist:
                    del self.mod_channels[guild]
                    continue
                self.mod_channels[guild] = {**callback(), **config}
        except (OSError, EOFError):
            self.mod_channels = defaultdict(callback)
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

    def getcmd(self, ctx):
        perms = ctx.author.guild_permissions
        return (
            perms.administrator or perms.view_audit_log or perms.manage_guild or perms.manage_roles
            or ctx.channel.id not in self.mod_channels[ctx.guild.id]['ignoreplebs']
            )

    def setlog(self, ctx, log):
        if log not in {'usrlog', 'msglog', 'modlog'}:
            raise ValueError(f'Invalid log channel type {log}')
        self.mod_channels[ctx.guild.id][log] = ctx.channel.id
        self.save()

    def toggle_reacts(self, ctx):
        config = self.mod_channels[ctx.guild.id]['autoreact']
        channel_id = ctx.channel.id
        if channel_id in config:
            config.remove(channel_id)
            return False
        else:
            config.add(channel_id)
            return True

    def toggle_cmd(self, ctx):
        config = self.mod_channels[ctx.guild.id]['ignoreplebs']
        channel_id = ctx.channel.id
        if channel_id in config:
            config.remove(channel_id)
            return False
        else:
            config.add(channel_id)
            return True

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
        
    def log_linky(self, msg):
        with open('spat.txt', 'a', encoding='utf-8') as lfile:
            lfile.write(msg.content.strip() + '\n')
    
    def random_linky(self, msg):
        try:
            with open('spat.txt', 'r', encoding='utf-8') as lfile:
                lcount = sum(1 for _ in lfile)
                lfile.seek(0)
                return next(islice(lfile, randrange(lcount), None))
        except FileNotFoundError:
            with open('spat.txt', 'w', encoding='utf-8') as lfile:
                lfile.write('i love dirt so much\n')
            return 'i love dirt so much\n'


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


def guild_callback():
    return {'first_join': None, 'last_seen': None, 'last_roles': []}

def member_callback():
    return defaultdict(guild_callback)

class MemberStalker(Singleton):
    def __init__(self, fname):
        self.fname = fname
        self.load()

    def load(self):
        with open(self.fname, 'rb') as member_file:
            self.member_data = pickle.load(member_file)

    def save(self):
        with open(self.fname, 'wb') as member_file:
            pickle.dump(self.member_data, member_file)

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
            self.member_data[data.id][data.guild.id][field] = [role.id for role in data.roles[1:]]

    async def load_roles(self, member):
        await member.add_roles(
            *map(member.guild.get_role, self.member_data[member.id][member.guild.id]['last_roles']),
            reason='Restore last roles'
            )
