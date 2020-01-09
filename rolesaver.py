import pickle
import discord as dc

class RoleSaver(object):
    def __init__(self, bot, fname):
        self.bot = bot
        self.fname = fname
        self.load()

    def load(self):
        try:
            with open(self.fname, 'rb') as role_file:
                self.user_roles = pickle.load(role_file)
        except (OSError, EOFError):
            self.user_roles = {guild.id: {} for guild in self.bot.guilds}
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
        try:
            guild_roles = self.user_roles[member.guild.id]
        except KeyError:
            guild_roles = self.user_roles[member.guild.id] = {}
        guild_roles[member.id] = [role.id for role in member.roles[1:]]
        self.save()
