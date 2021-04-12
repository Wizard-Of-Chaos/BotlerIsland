# The RoleManager Cog, which handles role categories and role assignment commands.
import os
import pickle
from collections import defaultdict

import discord as dc
from discord.ext import commands

from cogs_textbanks import url_bank, query_bank, response_bank
from bot_common import bot, CogtextManager

class RoleManager(CogtextManager):
    @staticmethod
    def _generate_empty():
        return defaultdict(dict)

    async def purge_category(self, role: dc.Role, member: dc.Member) -> bool:
        """
        Removes all roles from a guild member that are in the same category as the given role.
        Additionally, returns True if the role is in any categories, and False otherwise.
        """
        for category in self.data[role.guild.id].values():
            if role.id in category:
                break
        else:
            return False
        for member_role in member.roles:
            if member_role.id in category:
                await member.remove_roles(member_role)
        return True

    @commands.group()
    @commands.bot_has_permissions(send_messages=True, manage_roles=True)
    async def role(self, ctx):
        if ctx.invoked_subcommand is None:
            if ctx.author.guild_permissions.manage_roles:
                await ctx.send(
                    response_bank.role_usage_format
                    + response_bank.role_usage_extension
                    )
            else:
                await ctx.send(response_bank.role_usage_format)

    @role.error
    async def role_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            print(response_bank.channel_perms_error.format(ctx=ctx))
            return
        raise error

    @role.command(name='list')
    async def role_list(self, ctx, category: str):
        pass

    @role_list.error
    async def role_list_error(self, ctx, error):
        raise error

    @role.command(name='add')
    async def role_add(self, ctx, role: dc.Role):
        if role in ctx.author.roles:
            await ctx.send('D--> You already have this role.')
            return
        if not await self.purge_category(role, ctx.author):
            await ctx.send('D--> You are not allowed to self-assign this role.')
            return
        await ctx.author.add_roles(role)
        await ctx.send(f'D--> The role {role} has been granted.')

    @role_add.error
    async def role_add_error(self, ctx, error):
        if isinstance(error, commands.RoleNotFound):
            await ctx.send(response_bank.role_error)
            return
        raise error

    @role.command(name='del')
    async def role_del(self, ctx, role: dc.Role):
        if role not in ctx.author.roles:
            await ctx.send('D--> You do not have this role.')
            return
        if not await self.purge_category(role, ctx.author):
            await ctx.send('D--> You are not allowed to self-remove this role.')
            return
        await ctx.send(f'D--> The role {role} has been removed.')

    @role_del.error
    async def role_del_error(self, ctx, error):
        if isinstance(error, commands.RoleNotFound):
            await ctx.send(response_bank.role_error)
            return
        raise error

    @role.command('addcategory')
    @commands.has_permissions(manage_roles=True)
    async def role_addcategory(self, ctx, category: str, *roles):
        # I'm going full mONKE!!!!
        converter = commands.RoleConverter().convert
        category_data = self.data[ctx.guild.id][category]
        for role_text in roles:
            try:
                role = await converter(ctx, role_text)
            except commands.RoleNotFound:
                await ctx.send(
                    response_bank.role_addcategory_error.format(role=role)
                    )
                continue
            category_data.add(role.id)
        self.data_save()
        await ctx.send(
            response_bank.role_addcategory_confirm.format(category=category)
            )
        
    @role_addcategory.error
    async def role_addcategory_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        raise error

    @role.command('delcategory')
    @commands.has_permissions(manage_roles=True)
    async def role_delcategory(self, ctx, category: str):
        try:
            del self.data[ctx.guild.id][category]
        except KeyError:
            await ctx.send(response_bank.role_delcategory_error)
            return
        self.data_save()
        await ctx.send(
            response_bank.role_delcategory_confirm.format(category=category)
            )                   

    @role_delcategory.error
    async def role_delcategory_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(response_bank.perms_error)
            return
        raise error


bot.add_cog(RoleManager(bot))
