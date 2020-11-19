# Bot text bank
import re

queries = {
    "affirmation": {
        "thanks arquius",
        "good job arquius",
        "good work arquius",
        },
    }

quirked_responses = {
    "bot_startup": "ArquiusBot verision {version} started, beginning startup tasks...\n",
    "ready_prompt": "At your command.\n",
    "verify_whitelist_complete": "Whitelist verified.",
    "tasks_started": "All continuous tasks started.",
    "process_reacts": "Handling leftover reactions...",
    "process_reacts_complete": "Finished with leftover reactions.\n",
    "online_status": "A beautiful stallion.",
    "affirmation_response": "😎",
    "mention_self": "{ctx.author.mention}",
    "help_header": (
        "It seems you have asked about the *Homestuck and Hiveswap Discord Utility Bot*™."
        "This is a bot designed to cater to the server's moderation, utility, and statistic "
        "tracking needs. If the commands herein described are not performing to the degree "
        "that is claimed, please direct your attention to **Wizard of Chaos#2459** or **virtuNat#7998**.\n\n"
        "**Command List:**"
        ),
    "search_bot": "Do you wish to check out my strong muscles?",
    "search_user": "It seems you're a bit of a stalker, aren't you?",
    "search_self": "I understand the need to look at yourself in the mirror.",
    "allow_reacts": "❤️",
    "deny_reacts": "💔",
    "allow_users": "I shall listen only to blue blooded commands.",
    "deny_users": "Unfortunately, I must now listen to the lower classes.",
    "allow_latex": "Rendering latex is now allowed.",
    "deny_latex": "Take your latex elsewhere.",
    "render_latex_head": "Latex render for {ctx.author}",
    "render_latex_args_error": "Your latex code is beneighth contempt. Try again.",
    "dice_roller_parse_error": "Use your words, straight from the horse's mouth.",
    "dice_roller_args_error": "That math is unacceptable. I strongly suggest you try again.",
    "dice_roller_text_overflow": (
        "Woah there pardner, it seems you put too many dice "
        "or a few too large a die. I strongly recommend smaller values."
        ),
    "channel_usage": (
        "Usage of the channel command: `channel (ban|unban) <user>`\n\n"
        "`channel ban <user>`: Apply lowest available channel mute role to user.\n"
        "`channel unban <user>`: Revoke lowest available channel mute role from user.\n"
        "<user> can be the user id, mention, or name."
        ),
    "channel_ban_confirm": "Abberant {member} has been crushed by my strong hooves.",
    "role_usage_format": (
        'Usage of the role command: `role (subcommand) [args...]`\n\n'
        '`role list`: List all valid roles under their categories.\n'
        '`role add <role_name>`: Adds a specified role if valid.\n'
        '`role del <role_name>`: Removes a specified role if valid.\n'
        ),
    "role_remove_react_error": "Reaction {react} missing from roledata table at {msg.jump_url}.",
    "role_addcategory_confirm": "Added the roles to category {category}.",
    "role_addcategory_error": "Role {role} not found.",
    "role_delcategory_confirm": "Removed category {category}.",
    "role_delcategory_error": "Unable to remove category. Perhaps... it was never there?",
    "reactrole_usage_format": (
        'Usage of the reactrole command: `reactrole (subcommand) [args...]`\n\n'
        '`reactrole grant <message_link> <emoji> <role>`: Add roles from a message manually.\n'
        '`reactrole add <message_link> <emoji> <role>`: Add a role-bound reaction to a message to toggle a role.\n'
        '`reactrole del <message_link> <emoji>`: Delete a role-bound reaction and associated data.\n'
        ),
    "reactrole_grant_confirm": "I have successfully granted the roles.",
    "reactrole_add_confirm": "I have successfully added the react for the {role.name} role.",
    "reactrole_add_error": "I was unable to react to the specified message. Try again.",
    "fat_husky_head": "A corpulent canine.",
    "positive_flex_head": "I strongly agree.",
    "positive_flex_desc": (
        "It seems you have strongly requested to gaze upon my beautiful body, "
        "and who am I to refuse such a request?"
        ),
    "negative_flex_head": (
        "No.",
        "Begone.",
        "I deny you.",
        ),
    "negative_flex_desc": (
        "I would never stoop so low as to entertain the likes of this. "
        "You are strongly recommended to instead gaze upon my beautiful body as presented."
        ),
    "freeze_channel_head": "「ザ・ワールド」!!",
    "freeze_channel_desc": (
        "The time is nigh; your foolish actions shall face strong consequences, "
        "**#{ctx.channel}**! It is __***USELESS***__ to resist!"
        ),
    "unfreeze_channel_head": "時は動きです。",
    "unfreeze_channel_desc": "Time resumes in **#{ctx.channel}**.",
    "purge_channel_head": "「ザ・ハンド」!!",
    "purge_channel_desc": (
        "I shall show you the magnificent strength of my hand, **#{ctx.channel}**!"
        ),
    "star_wars_punish_confirm": "It will be done, my lord.",
    "star_wars_punish_args_error": "Vocalize your command strongly, my lord.",
    "star_wars_punish_perms_error": "Only the senate may execute this order, {ctx.author.name}.",
    "star_wars_punish_completion": "It is done, my lord.",
    "star_wars_ban_head": "Forbidden.",
    "star_wars_ban_desc": (
        "It seems that **{ctx.author.name}** has mentioned that which "
        "has been expressly forbidden by the powers that be, and has thus been "
        "strongly punished accordingly."
        ),
    "config_args_error": "It seems that {log} is not a valid status log type.",
    "stats_busy": (
        "It seems that I am currently in the middle of something. "
        "I strongly suggest that you wait for me to finish."
        ),
    "woc_counter_search_begin": "Searching for slurs...",
    "woc_counter_search_milestone": "Searching #{channel}...",
    "woc_counter_confirm_linky": (
        "Are you sure you want to know that, Master Linky? "
        "Regardless of your answer, I shall tell you, though I STRONGLY suggest you wait."
        ),
    "woc_counter_completion": (
        "Wizard of Chaos has slurred {tards} times in this server, {ctx.author.mention}."
        ),
    "preedit_overflow": "The pre-edit message is too long to contain, use this:",
    "postedit_overflow": "The post-edit message is too long to contain, use this:",
    "args_error": (
        "You made a mistake. Redos are free, so try again.",
        "It seems you made a mistake in your command. Please try again.",
        ),
    "perms_error": (
        "Nay.",
        "Nay, plebian.",
        "Nay, pathetic user.",
        "It seems you have insufficient permission elevations.",
        "It seems that you don't have the appropriate permissions for this command. "
        "I strongly recommend you back off or get bucked off, broseph.",
        ),
    "channel_perms_error": (
        "{ctx.channel} does not support the required permissions."
        ),
    "user_error": "It seems that user can't be found. Check your spelling.",
    "message_error": "It seems that your message can't be found. Check your link.",
    "role_error": "It seems that your role can't be found. Check for the name.",
    "react_error": "It seems that your react can't be found. Check the emoji name.",
    "unexpected_state": (
        "We could not have predicted this tomfoolery. Try again.",
        ),
    }

unquirked_responses = {
    "role_usage_extension": (
        '`role addcategory <category> [<role_name1> <role_name2> ...]`: Add roles to a category.\n'
        '`role delcategory <category>`: Delete a category and related role data.\n'
        ),
    "generator_extension": (
        'Generates fortunes, names for your tabletop games, stands, and ships. \n'
        '`generate fortune`: A fortune, just for you. \n'
        '`generate stand`: Your personal STAND! \n'
        '`generate dungeon`: A dungeon name. \n'
        '`generate ryder`: A Dave Ryder name, MST3K style. \n'
        '`generate orcname`: Gibberish. Actual gibberish. \n'
        ),
    "dungeons": (
        'Dungeon', 'Temple', 'Cave', 'Ravine', 'Tent', 'Church', 'Shrine', 'Sanctum', 'Cavern', 'Castle',
        'Lookout', 'Prison', 'Hole', 'Ruin', 'Wyvern-Infested Mountains', 'Mountains', 'Desert', 'Forest',
        'Mountain', 'Cliffs',' Crypt', 'Burrow', 'Tower', 'Vault', 'Cloister', 'Clown Pit', 'Lair',
        ),
    "descriptors": (
        'Doom', 'Rage', 'Hate', 'Horror', 'Terror', 'Vile Things', 'Death', 'Life', 'Toil', 'Despair',
        'Hardships', 'Trials', 'Punching', 'Unholy Beings', 'Battle', 'Darkness', 'Bad', 'Evil', 'Neutrality',
        'Knives', 'Chains', 'Fire', 'Blood', 'Tentacles', 'Ice', 'Lacerations', 'Bones', 'Flesh', 'Hell',
        'Hatred', 'Screaming', 'Blades', 'Arrows', 'the Hunter', 'He-Who-Rends-And-Tears', 'Ancient Gods',
        ),
    "daves": (
        ),
    "ryders": (
        ),
    }


def apply_quirk(response: str) -> str:
    response = re.sub(r'[xX]', '%', response)
    response = re.sub(r'(loo|lou|lue|lew)', '100', response)
    response = re.sub(r'(ool|oul|ewl)', '001', response)
    response = re.sub(r'\b(nay|nigh)\b', 'neigh', response)
    response = re.sub(
        r'\b(strength|strong\w+|crush\w+)\b',
        lambda m: m[0].upper(),
        response,
        )
    return f'D--> {response}'
