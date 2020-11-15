def callback(): # Lambdas can't be pickled, but named functions can.
    return {
    'usrlog': None, 'msglog': None, 'modlog': None,
    'autoreact': set(), 'star_wars': {}, 'ignoreplebs': set(), 'enablelatex': set(),
    }

def guild_callback():
    return {'first_join': None, 'last_seen': None, 'last_roles': []}

def member_callback():
    return defaultdict(guild_callback, {'avatar_count': 0, 'latex_count': 0})

def dictgrabber():
    return defaultdict(dict)

def category_callback():
    return defaultdict(set)
