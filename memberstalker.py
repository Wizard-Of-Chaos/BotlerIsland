from collections import defaultdict
import pickle
import discord as dc

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
