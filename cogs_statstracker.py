# Statistics data classes
import os
import pickle
from collections import Counter, defaultdict

import discord as dc

from cogs_textbanks import query_bank, response_bank

CONST_WOC_ID = 125433170047795200

def callback():
    return defaultdict(dict, {})

class StatsTracker(object):
    stat_funcs = {'woc_counter'}

    def __init__(self, fname):
        self.fname = os.path.join('data', fname)
        self.locked = False
        self.locked_msg = response_bank.stats_busy
        self.load()

    def __enter__(self):
        return self

    def __exit__(self, etype, evalue, etrace):
        self.save()

    def save(self):
        with open(self.fname, 'wb') as role_file:
            pickle.dump(self.stats, role_file)

    def load(self):
        try:
            with open(self.fname, 'rb') as role_file:
                self.stats = pickle.load(role_file)
            self.stats = defaultdict(callback, self.stats)
        except (OSError, EOFError):
            self.stats = defaultdict(callback, defaultdict(dict, {}))
            self.save()

    async def take(self, stat, ctx, args):
        if self.locked:
            await ctx.send(self.locked_msg)
            return None
        self.locked = True
        if stat in self.stat_funcs:
            value = await getattr(self, stat)(ctx, args)
        else:
            raise AttributeError(f'Invalid statistic function: {stat}')
        self.save()
        self.locked = False
        return value

    async def woc_counter(self, ctx, args):
        wocstat = self.stats[ctx.guild.id]['woc']
        if not wocstat:
            wocstat['value'] = 0
            wocstat['lastcall'] = None
        print(response_bank.woc_counter_search_begin)
        for channel in ctx.guild.text_channels:
            print(response_bank.woc_counter_search_milestone)
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
        return wocstat['value']

    async def insecurity(self, ctx, args):
        pass

    async def member_count(self, ctx, args):
        pass
