import discord
from discord.ext import commands
from discord.ext.commands.converter import _get_from_guilds

from rings.utils.utils import time_converter

import re

utils = discord.utils
_utils_get = utils.get

def get_member_named(members, name):
    result = None
    if len(name) > 5 and name[-5] == '#':
        # The 5 length is checking to see if #0000 is in the string,
        # as a#0000 has a length of 6, the minimum for a potential
        # discriminator lookup.
        potential_discriminator = name[-4:]

        # do the actual lookup and return if found
        # if it isn't found then we'll do a full name lookup below.
        result = utils.find(lambda m: name[:-5].lower() == m.name.lower() and potential_discriminator == m.discriminator, members)
        if result is not None:
            return result

    def pred(m):
        nick = None
        
        if m.nick is not None:
            nick = m.nick.lower()
            
        return nick == name.lower() or m.name.lower() == name.lower()

    return utils.find(pred, members)
    
def get_member(guild, user_id):
    """Returns a member with the given ID.

    Parameters
    -----------
    user_id: :class:`int`
        The ID to search for.

    Returns
    --------
    Optional[:class:`Member`]
        The member or ``None`` if not found.
    """
    return guild._members.get(user_id)
        
def _get_from_guilds(bot, func, attr, argument):
    result = None
    for guild in bot.guilds:
        result = func(getattr(guild, attr, []), argument)
        if result:
            return result
    return result

class MemberConverter(commands.IDConverter):
    """Member converter but case insensitive"""
    
    ctx_attr = "author"

    async def convert(self, ctx, argument):
        bot = ctx.bot
        match = self._get_id_match(argument) or re.match(r'<@!?([0-9]+)>$', argument)
        guild = ctx.guild
        result = None
        if match is None:
            # not a mention...
            if guild:
                result = get_member_named(guild.members, argument)
            else:
                result = _get_from_guilds(bot, get_member_named, "members", argument)
        else:
            user_id = int(match.group(1))
            if guild:
                result = guild.get_member(user_id) or _utils_get(ctx.message.mentions, id=user_id)
            else:
                result = _get_from_guilds(bot, get_member, "members", user_id)

        if result is None:
            raise commands.BadArgument('Member "{}" not found'.format(argument))

        return result
        
class UserConverter(commands.IDConverter):
    """User converter but case insensitive"""
    
    ctx_attr = "author"
    
    async def convert(self, ctx, argument):
        match = self._get_id_match(argument) or re.match(r'<@!?([0-9]+)>$', argument)
        result = None
        state = ctx._state

        if match is not None:
            user_id = int(match.group(1))
            result = ctx.bot.get_user(user_id) or _utils_get(ctx.message.mentions, id=user_id)
        else:
            arg = argument

            # Remove the '@' character if this is the first character from the argument
            if arg[0] == '@':
                # Remove first character
                arg = arg[1:]

            # check for discriminator if it exists,
            if len(arg) > 5 and arg[-5] == '#':
                discrim = arg[-4:]
                name = arg[:-5]
                predicate = lambda u: u.name.lower() == name.lower() and u.discriminator == discrim
                result = discord.utils.find(predicate, state._users.values())
                if result is not None:
                    return result

            predicate = lambda u: u.name.lower() == arg.lower()
            result = discord.utils.find(predicate, state._users.values())

        if result is None:
            raise commands.BadArgument('User "{}" not found'.format(argument))

        return result
        
class RoleConverter(commands.IDConverter):
    """Converts to a role but case insensitive"""
    
    async def convert(self, ctx, argument):
        guild = ctx.guild
        if not guild:
            raise commands.NoPrivateMessage()

        match = self._get_id_match(argument) or re.match(r'<@&([0-9]+)>$', argument)
        if match:
            result = guild.get_role(int(match.group(1)))
        else:
            result = discord.utils.find(lambda r: r.name.lower() == argument.lower(), guild._roles.values())

        if result is None:
            raise commands.BadArgument('Role "{}" not found.'.format(argument))
            
        return result

class GuildConverter(commands.IDConverter):
    async def convert(self, ctx, argument):
        result = None
        bot = ctx.bot
        guilds = bot.guilds

        result = discord.utils.get(guilds, name=argument)

        if result:
            return result

        if argument.isdigit():
            result = bot.get_guild(int(argument))

            if result:
                return result

        raise commands.BadArgument("Not a known guild")
        
class BadgeConverter(commands.Converter):
    async def convert(self, ctx, argument):
        badge = await ctx.bot.db.get_badge_from_shop(name=argument)
        
        if not badge:
            raise commands.CheckFailure("Could not find a badge with this name")
            
        return badge[0]

class TimeConverter(commands.Converter):
    async def convert(self, ctx, argument):
        return time_converter(argument)

class MoneyConverter(commands.Converter):
    async def convert(self, ctx, argument):
        if not argument.isdigit():
            raise commands.BadArgument("Not a valid intenger")
        
        argument = int(argument)

        if argument < 0:
            raise commands.BadArgument("Amount must be a positive intenger")
        
        money = await ctx.bot.db.get_money(ctx.message.author.id)
        if money >= argument:
            return argument
        
        raise commands.BadArgument("You do not have enough money")
        
def range_check(min_v, max_v):
    def check(argument):
        if not argument.isdigit():
            raise commands.BadArgument("Not a valid intenger")
            
        value = int(argument)
        if not max_v >= value >= min_v:
            raise commands.CheckFailure(f"Please select a number between **{min_v}** and **{max_v}**")
            
        return value
            
    return check

class Grudge(commands.Converter):
    async def convert(self, ctx, argument):
        if not argument.isdigit():
            raise commands.BadArgument("Please supply a valid id")
        
        grudge = await ctx.bot.db.query(
            "SELECT * FROM necrobot.Grudges WHERE id = $1",
            int(argument)    
        )
        
        if not grudge:
            raise commands.BadArgument("No grudge with such id")
            
        return grudge[0]

class MUConverter(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return await MemberConverter().convert(ctx, argument)
        except commands.BadArgument:
            pass
            
        user_id  = await ctx.bot.db.query(
            "SELECT user_id FROM necrobot.MU_Users WHERE username_lower = $1",
            argument.lower(), fetchval=True
        )
        
        if user_id is None:
            raise commands.BadArgument(f"Member {argument} does not exist")
            
        user = ctx.guild.get_member(user_id)
        if user is None:
            user = object()
            user.id = user_id
            user.display_name = "User Left"
        
        return user

class CoinConverter(commands.Converter):
    async def convert(self, ctx, argument):
        if argument.lower() in ["h", "head"]:
            return "h"
        if argument.lower() in ["t", "tail"]:
            return "t"

        raise commands.BadArgument("Choices must be one of: `t`, `tail`, `h` or `head`")

class Tag(commands.Converter):
    async def convert(self, ctx, argument):
        argument = argument.lower()
        tag = await ctx.bot.db.query("""
            SELECT t.name, t.content, t.owner_id, t.uses, t.created_at FROM necrobot.Tags t, necrobot.Aliases a 
            WHERE t.name = a.original AND a.alias = $1 AND a.guild_id = $2 AND t.guild_id = $2
            """, argument, ctx.guild.id
        )
        
        if not tag:
            raise commands.BadArgument(f"Tag {argument} not found.")
            
        return tag[0]
