# The actual script you run directly.
from bot_common import (
    bot, guild_config, member_stalker, emoji_roles, role_categories,
    )
import task_dailycounts
import bot_events
import bot_rolecommands
import bot_usercommands
import bot_modcommands

def get_token():
    with open('token.dat', 'r') as tokenfile:
        raw = tokenfile.read().strip()
        return ''.join(chr(int(''.join(c), 16)) for c in zip(*[iter(raw)]*2))

if __name__ == '__main__':
    with guild_config, member_stalker, emoji_roles, role_categories:
        bot.run(get_token())
