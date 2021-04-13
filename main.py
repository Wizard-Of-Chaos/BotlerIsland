# The actual script you run directly.
from bot_common import main, get_token
import bot_events
import bot_modcommands
import bot_usercommands

import cogs_logmanager
import cogs_dailycounts
import cogs_banmanager
import cogs_rolemanager
import cogs_reactroletagger
import cogs_linkyaicore
import stupid_arquius_tricks

if __name__ == '__main__':
    main(get_token())
