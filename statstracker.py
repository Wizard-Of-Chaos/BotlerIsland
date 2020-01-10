from collections import defaultdict
import pickle
import discord as dc

CONST_WOC_ID = 125433170047795200

def callback():
    return defaultdict(dict, {})

class StatsTracker(object):
    def __init__(self, fname):
        self.fname = fname
        self.lock = False
        self.load()

    def __enter__(self):
        self.lock = True
        return self

    def __exit__(self, exc_type, exc_val, trace):
        self.lock = False

    def load(self):
        try:
            with open(self.fname, 'rb') as role_file:
                self.stats = pickle.load(role_file)
        except (OSError, EOFError):
            self.stats = defaultdict(callback, {})
            self.save()

    def save(self):
        with open(self.fname, 'wb') as role_file:
            pickle.dump(self.stats, role_file)

    async def woc_counter(self, ctx):
        wocstat = self.stats[ctx.guild.id]['woc']
        if not wocstat:
            wocstat['value'] = 0
            wocstat['lastcall'] = None
        print('D--> Searching for slurs...')
        for channel in ctx.guild.text_channels:
            print(f'D--> Searching #{channel}:')
            try:
                history = channel.history(
                    limit=None,
                    before=ctx.message.created_at,
                    after=wocstat['lastcall'],
                    )
            except dc.Forbidden:
                continue
            async for msg in history:
                if msg.author.id == CONST_WOC_ID and 'retard' in msg.content:
                    wocstat['value'] += 1
        wocstat['lastcall'] = ctx.message.created_at
        print(f'D--> Done. Total count: {wocstat["value"]}\n')
        return wocstat['value']

    async def take(self, ctx, stat):
        if self.lock:
            await ctx.send(
                'D--> I am currently in the middle of something. Try again later.'
                )
            return
        if stat == 'woc':
            value = await self.woc_counter(ctx)
        else:
            raise ValueError(f'Invalid stat type {stat}')
        self.save()
        return value
