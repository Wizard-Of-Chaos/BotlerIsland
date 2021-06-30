# The actual script you run directly.
from bot_common import main
import bot_events
import bot_modcommands
import bot_usercommands

import cogs_logmanager
import cogs_dailycounts
import cogs_banmanager
import cogs_rolemanager
import cogs_reactroletagger
import cogs_batchcmds
import cogs_linkyaicore
# import cogs_tenseibot
import cogs_bullshitgenerator

if __name__ == '__main__':
    main()
