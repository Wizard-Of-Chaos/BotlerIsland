# The actual script you run directly.
from bot_common import main, bot
import bot_events
import bot_modcommands
import bot_usercommands

import cogs_logmanager
import cogs_guildconfig
import cogs_latexrenderer
import cogs_dailycounts
import cogs_banmanager
import cogs_rolemanager
import cogs_reactroletagger
import cogs_batchcmds
import cogs_linkyaicore
import cogs_bullshitgenerator

import asyncio    
    
if __name__ == '__main__':
    asyncio.run(main())
