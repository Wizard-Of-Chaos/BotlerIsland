# The actual script you run directly.
from bot_common import main
import bot_events
import bot_modcommands
import bot_usercommands

import cogs_logmanager
import cogs_guildconfig
import cogs_latexrenderer
import cogs_userdatalogger
import cogs_chandatalogger
import cogs_dailycounts
import cogs_banmanager
import cogs_rolemanager
import cogs_reactroletagger
import cogs_batchcmds
import cogs_linkyaicore
import cogs_bullshitgenerator

if __name__ == '__main__':
    main()
