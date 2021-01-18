# The BanManager Cog, which handles channel mute functions.
import re
import os
import pickle
from datetime import datetime, timedelta
from collections import defaultdict
from heapq import heapify, heappush, heappop

import discord as dc
from discord.ext import commands, tasks

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot, CogtextManager, guild_config

_unit_dict = {'h': 1, 'd': 24, 'w': 168, 'm': 732, 'y': 8766}
def _parse_length(length):
    if length == 'perma':
        return None
    if (match := re.match(r'(\d+)([hdwmy])$', length)):
        return int(match[1]) * _unit_dict[match[2]]
    raise commands.BadArgument(f'Invalid duration argument: "{length}"')


class BanManager(CogtextManager):
    @staticmethod
    def _generate_empty():
        return []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print(response_bank.process_mutelist)
        self.manage_mutelist.start()

    def cog_unload(self):
        super().cog_unload()
        self.manage_mutelist.cancel()

    def push(self, id_tuple, unban_dt):
        for entry in self.data:
            if entry[1] == id_tuple:
                entry[0] = unban_dt
                heapify(self.data)
                break
        else:
            heappush(self.data, [unban_dt, id_tuple])

    def remove(self, id_tuple):
        for idx, (_, ids) in enumerate(self.data):
            if ids == id_tuple:
                self.data[idx], self.data[-1] = self.data[-1], self.data[idx]
                del self.data[-1]
                heapify(self.data)
                break

    @tasks.loop(minutes=30)
    async def manage_mutelist(self):
        now = datetime.utcnow()
        while self.data and self.data[0][0] <= now:
            _, (guild_id, member_id, role_id) = heappop(self.data)
            guild = self.bot.get_guild(guild_id)
            if guild is None: continue
            try:
                member = await guild.fetch_member(member_id)
            except (dc.Forbidden, dc.HTTPException) as exc:
                continue
            if (role := guild.get_role(role_id)) is None:
                if guild_config.getlog(guild, 'modlog'):
                    await guild_config.log(guild, 'modlog',
                        response_bank.manage_mutelist_role_error.format(role=role)
                        )
                continue
            try:
                await member.remove_roles(role, reason='Channel mute timeout')
            except (dc.Forbidden, dc.HTTPException) as exc:
                if guild_config.getlog(guild, 'modlog'):
                    await guild_config.log(guild, 'modlog',
                        response_bank.manage_mutelist_unban_error.format(member=member, role=role)
                        )
            else:
                if guild_config.getlog(guild, 'modlog'):
                    embed = dc.Embed(
                        color=bot.user.color,
                        timestamp=now,
                        description=f'{member.mention} reached timeout for **{role}**.'
                        )
                    embed.add_field(name='**User ID:**', value=member.id)
                    embed.set_author(
                        name=f'@{bot.user} Undid Channel Ban:',
                        icon_url=bot.user.avatar_url,
                        )
                    await guild_config.log(ctx.guild, 'modlog', embed=embed)

    @manage_mutelist.before_loop
    async def prepare_mutelist(self):
        await self.bot.wait_until_ready()
        print(response_bank.process_mutelist_complete)

    @commands.group(name='channel')
    @commands.has_guild_permissions(send_messages=True, manage_roles=True)
    async def role_mute(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.message.delete()
            await ctx.send(response_bank.channel_usage)
            await aio.sleep(4)
            async for msg in ctx.channel.history(limit=128):
                if msg.author.id == bot.user.id and msg.content == response_bank.channel_usage:
                    await msg.delete()
                    break

    @role_mute.error
    async def role_mute_error(self, ctx, error):
        if isinstance(error,
            (commands.MissingPermissions, commands.BotMissingPermissions)
            ):
            return
        raise error

    @role_mute.command(name='ban')
    async def role_mute_apply(self, ctx, member: dc.Member, length: _parse_length, *, reason='None specified.'):
        # ALRIGHT HUNGOVER WIZARD OF CHAOS CODE IN THE HIZ-OUSE
        # WE GONNA WRITE SOME MOTHERFUCKING BAN COMMANDS; INITIALIZE THAT SHIT
        if not member: # WE'RE GRABBING A MEMBER WE GIVE NO SHITS
            return
        if member.id == bot.user.id:
            await ctx.send('<:professionalism:778997791829000203>')
            return
        src_perms = ctx.author.guild_permissions
        tgt_perms = member.guild_permissions
        if ((not src_perms.manage_nicknames and tgt_perms.manage_roles)
            or (not src_perms.manage_channels and tgt_perms.manage_nicknames)
            ):
            await ctx.send(response_bank.channel_ban_deny_horizontal)
            return
        # WE'RE GONNA FIND THE FIRST FUCKING ROLE THAT HAS NO PERMS IN THIS CHANNEL
        # AND GUESS HOW WE DO THAT? THAT'S RIGHT, CURSED IF STATEMENT
        for role in ctx.guild.roles:
            if ctx.channel.overwrites_for(role).pair()[1].send_messages: # BOOM LOOK AT THAT SHIT SUCK MY DICK
                await member.add_roles(role)
                break
        else:
            await ctx.send(response_bank.channel_ban_role_error)
            return
        lenstr = 'Until further notice.' if length is None else f'{length} hours.'
        if length is not None:
            self.push((ctx.guild.id, member.id, role.id), datetime.utcnow() + timedelta(hours=length))
        await ctx.message.delete()
        await ctx.send(response_bank.channel_ban_confirm.format(
            member=member.mention, length=lenstr, reason=reason,
            ))
        # OH BUT NOW SOMEONES GONNA WHINE THAT WE DIDNT LOG IT? HOLD YOUR ASS TIGHT BECAUSE WE'RE ABOUT TO
        if guild_config.getlog(ctx.guild, 'modlog'): # OHHHHHHH! HE DID IT! THE FUCKING MADMAN!
            embed = dc.Embed(
                color=ctx.author.color,
                timestamp=ctx.message.created_at,
                description=f'{member.mention} has been banned in **#{ctx.channel}**'
                )
            embed.add_field(name='**Role Granted:**', value=f'`{role}`')
            embed.add_field(name='**Duration:**', value=lenstr)
            embed.add_field(name='**Reason:**', value=reason)
            embed.add_field(name='**User ID:**', value=member.id, inline=False)
            embed.set_author(
                name=f'@{ctx.author} Issued Channel Ban:',
                icon_url=ctx.author.avatar_url,
                )
            await guild_config.log(ctx.guild, 'modlog', embed=embed)
            # BOOM! SUUUUUUUUCK - IT!

    @role_mute_apply.error
    async def role_mute_apply_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.send(response_bank.channel_member_error.format(
                member=error.args[0].split()[1]
                ))
            return
        if isinstance(error, commands.BadArgument):
            await ctx.send(response_bank.channel_ban_duration_error.format(
                length=error.args[0].split()[-1]
                ))
            return
        raise error

    @role_mute.command(name='unban')
    async def role_mute_revoke(self, ctx, member: dc.Member, *, reason=''):
        if not member: return
        if member.id == self.bot.user.id:
            await ctx.send('<:professionalism:778997791829000203>')
            return
        for role in member.roles:
            if ctx.channel.overwrites_for(role).pair()[1].send_messages:
                await member.remove_roles(role)
                break
        else:
            await ctx.send(response_bank.channel_unban_role_error)
            return
        self.remove((ctx.guild.id, member.id, role.id))
        if guild_config.getlog(ctx.guild, 'modlog'):
            embed = dc.Embed(
                color=ctx.author.color,
                timestamp=ctx.message.created_at,
                description=f'{member.mention} has been unbanned in **#{ctx.channel}**'
                )
            embed.add_field(name='**Role Revoked:**', value=f'`{role}`')
            embed.add_field(name='**Reason:**', value=reason or 'None specified.')
            embed.add_field(name='**User ID:**', value=member.id)
            embed.set_author(
                name=f'@{ctx.author} Undid Channel Ban:',
                icon_url=ctx.author.avatar_url,
                )
            await guild_config.log(ctx.guild, 'modlog', embed=embed)

    @role_mute_revoke.error
    async def role_mute_revoke_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.send(response_bank.channel_member_error.format(
                member=error.args[0].split()[1]
                ))
            return
        raise error


bot.add_cog(BanManager(bot))
