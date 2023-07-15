from __future__ import annotations

import re
from typing import TYPE_CHECKING, Callable, List, Literal, Optional, get_args

import discord
from discord.ext import commands
from discord.ext.commands.converter import _get_from_guilds

from rings.utils.utils import BotError, time_converter

if TYPE_CHECKING:
    from bot import NecroBot

utils = discord.utils
_utils_get = utils.get


def get_member_named(members, name) -> Optional[discord.Member]:
    username, _, discriminator = name.rpartition("#")
    if discriminator == "0" or (len(discriminator) == 4 and discriminator.isdigit()):
        return utils.find(
            lambda m: m.name.lower() == username.lower() and m.discriminator == discriminator,
            members,
        )

    def pred(m: discord.Member) -> bool:
        return (
            m.nick.lower() == name.lower()
            or m.global_name.lower() == name.lower()
            or m.name.lower() == name.lower()
        )

    return utils.find(pred, members)


def get_member(guild: discord.Guild, user_id: int) -> Optional[discord.Member]:
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


def _get_from_guilds(bot: NecroBot, getter: str, argument: str):
    result = None
    for guild in bot.guilds:
        result = getattr(guild, getter)(argument)
        if result:
            return result
    return result


_utils_get = discord.utils.get


class MemberConverter(commands.IDConverter[discord.Member]):
    """Member converter but case insensitive"""

    ctx_attr = "author"

    async def query_member_named(
        self, guild: discord.Guild, argument: str
    ) -> Optional[discord.Member]:
        cache = guild._state.member_cache_flags.joined
        username, _, discriminator = argument.rpartition("#")
        if discriminator == "0" or (len(discriminator) == 4 and discriminator.isdigit()):
            lookup = username.lower()
            predicate: Callable[[discord.Member], bool] = (
                lambda m: m.name.lower() == username.lower() and m.discriminator == discriminator
            )
        else:
            lookup = argument.lower()
            predicate: Callable[[discord.Member], bool] = (
                lambda m: m.nick.lower() == argument.lower()
                or m.global_name.lower() == argument.lower()
                or m.name.lower() == argument.lower()
            )

        members = await guild.query_members(lookup, limit=100, cache=cache)
        return discord.utils.find(predicate, members)

    async def query_member_by_id(
        self, bot: NecroBot, guild: discord.Guild, user_id: int
    ) -> Optional[discord.Member]:
        ws = bot._get_websocket(shard_id=guild.shard_id)
        cache = guild._state.member_cache_flags.joined
        if ws.is_ratelimited():
            # If we're being rate limited on the WS, then fall back to using the HTTP API
            # So we don't have to wait ~60 seconds for the query to finish
            try:
                member = await guild.fetch_member(user_id)
            except discord.HTTPException:
                return None

            if cache:
                guild._add_member(member)
            return member

        # If we're not being rate limited then we can use the websocket to actually query
        members = await guild.query_members(limit=1, user_ids=[user_id], cache=cache)
        if not members:
            return None
        return members[0]

    async def convert(self, ctx: commands.Context[NecroBot], argument: str) -> discord.Member:
        bot = ctx.bot
        match = self._get_id_match(argument) or re.match(r"<@!?([0-9]{15,20})>$", argument)
        guild = ctx.guild
        result = None
        user_id = None

        if match is None:
            # not a mention...
            if guild:
                result = get_member_named(guild.members, argument)
            else:
                result = _get_from_guilds(bot, "get_member_named", argument)
        else:
            user_id = int(match.group(1))
            if guild:
                result = guild.get_member(user_id) or _utils_get(ctx.message.mentions, id=user_id)
            else:
                result = _get_from_guilds(bot, "get_member", user_id)

        if not isinstance(result, discord.Member):
            if guild is None:
                raise discord.errors.MemberNotFound(argument)

            if user_id is not None:
                result = await self.query_member_by_id(bot, guild, user_id)
            else:
                result = await self.query_member_named(guild, argument)

            if not result:
                raise commands.MemberNotFound(argument)

        return result


class UserConverter(commands.IDConverter[discord.User]):
    """User converter but case insensitive"""

    ctx_attr = "author"

    async def convert(self, ctx: commands.Context[NecroBot], argument: str) -> discord.User:
        match = self._get_id_match(argument) or re.match(r"<@!?([0-9]{15,20})>$", argument)
        result = None
        state = ctx._state

        if match is not None:
            user_id = int(match.group(1))
            result = ctx.bot.get_user(user_id) or _utils_get(ctx.message.mentions, id=user_id)
            if result is None:
                try:
                    result = await ctx.bot.fetch_user(user_id)
                except discord.HTTPException:
                    raise commands.UserNotFound(argument) from None

            return result  # type: ignore

        username, _, discriminator = argument.rpartition("#")
        if discriminator == "0" or (len(discriminator) == 4 and discriminator.isdigit()):
            predicate: Callable[[discord.User], bool] = (
                lambda u: u.name.lower() == username.lower() and u.discriminator == discriminator
            )
        else:
            predicate: Callable[[discord.User], bool] = (
                lambda u: u.global_name.lower() == argument.lower()
                or u.name.lower() == argument.lower()
            )

        result = discord.utils.find(predicate, state._users.values())
        if result is None:
            raise commands.UserNotFound(argument)

        return result


class RoleConverter(commands.IDConverter[discord.Role]):
    """Converts to a role but case insensitive"""

    async def convert(self, ctx: commands.Context[NecroBot], argument):
        guild = ctx.guild
        if not guild:
            raise commands.NoPrivateMessage()

        match = self._get_id_match(argument) or re.match(r"<@&([0-9]+)>$", argument)
        if match:
            result = guild.get_role(int(match.group(1)))
        else:
            result = discord.utils.find(
                lambda r: r.name.lower() == argument.lower(), guild._roles.values()
            )

        if result is None:
            raise commands.BadArgument(f'Role "{argument}" not found.')

        if result.managed:
            raise commands.BadArgument(f"Cannot use a managed role.")

        return result


class GuildConverter(commands.IDConverter[discord.Guild]):
    async def convert(self, ctx: commands.Context[NecroBot], argument: str):
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


class BadgeConverter(commands.Converter[dict]):
    async def convert(self, ctx: commands.Context[NecroBot], argument: str):
        badge = await ctx.bot.db.get_badge_from_shop(name=argument)

        if not badge:
            raise commands.CheckFailure("Could not find a badge with this name")

        return badge[0]


class TimeConverter(commands.Converter[int]):
    async def convert(self, ctx: commands.Context[NecroBot], argument):
        return time_converter(argument)


class MoneyConverter(commands.Converter[int]):
    async def convert(self, ctx: commands.Context[NecroBot], argument):
        if not argument.isdigit():
            raise commands.BadArgument("Not a valid integer")

        argument = int(argument)

        if argument < 0:
            raise commands.BadArgument("Amount must be a positive integer")

        money = await ctx.bot.db.get_money(ctx.author.id)
        if money >= argument:
            return argument

        raise commands.BadArgument("You do not have enough money")


class FlowerConverter(commands.Converter[int]):
    async def convert(self, ctx: commands.Context[NecroBot], argument):
        if not argument.isdigit():
            raise commands.BadArgument("Not a valid integer")

        argument = int(argument)

        if argument < 0:
            raise commands.BadArgument("Amount must be a positive integer")

        money = await ctx.bot.get_cog("Flowers").get_flowers(ctx.guild.id, ctx.author.id)
        if money >= argument:
            return argument

        raise commands.BadArgument("You do not have enough flowers")


def RangeConverter(min_v: int, max_v: int):
    def check(argument: str) -> bool:
        if not argument.isdigit():
            raise commands.BadArgument("Not a valid integer")

        value = int(argument)
        if not max_v >= value >= min_v:
            raise commands.CheckFailure(
                f"Please select a number between **{min_v}** and **{max_v}**"
            )

        return value

    return check


class Grudge(commands.Converter[dict]):
    async def convert(self, ctx: commands.Context[NecroBot], argument: str):
        if not argument.isdigit():
            raise commands.BadArgument("Please supply a valid id")

        grudge = await ctx.bot.db.query(
            "SELECT * FROM necrobot.Grudges WHERE id = $1", int(argument)
        )

        if not grudge:
            raise commands.BadArgument("No grudge with such id")

        return grudge[0]


class CoinConverter(commands.Converter[str]):
    async def convert(self, ctx: commands.Context[NecroBot], argument: str):
        if argument.lower() in ["h", "head"]:
            return "h"
        if argument.lower() in ["t", "tail"]:
            return "t"

        raise commands.BadArgument("Choices must be one of: `t`, `tail`, `h` or `head`")


class Tag(commands.Converter[dict]):
    async def convert(self, ctx: commands.Context[NecroBot], argument: str):
        argument = argument.lower()
        tag = await ctx.bot.db.query(
            """
            SELECT t.name, t.content, t.owner_id, t.uses, t.created_at FROM necrobot.Tags t, necrobot.Aliases a 
            WHERE t.name = a.original AND a.alias = $1 AND a.guild_id = $2 AND t.guild_id = $2
            """,
            argument,
            ctx.guild.id,
        )

        if not tag:
            raise commands.BadArgument(f"Tag {argument} not found.")

        return tag[0]


class WritableChannelConverter(commands.Converter[discord.TextChannel]):
    async def convert(self, ctx: commands.Context[NecroBot], argument: str):
        result = await commands.TextChannelConverter().convert(ctx, argument)
        if not result.permissions_for(result.guild.me).send_messages:
            raise BotError(f"I cannot send messages in {result.mention}")

        return result


CharacterType = Literal["character", "weapon", "artefact", "enemy"]


class GachaCharacterConverter(commands.Converter[dict]):
    def __init__(
        self,
        *,
        respect_obtainable: bool = False,
        allowed_types: List[CharacterType] = (),
        is_owned: bool = False,
    ):
        """
        Params
        ------
        respect_obtainable: bool
            Only search in the list of characters currently toggled on
        allowed_types: List[CharacterType]
            Types of entities that are valid
        is_owned: bool
            Only consider characters that are owned by the author
        """
        self.respect_obtainable = respect_obtainable
        self.allowed_types = allowed_types
        self.is_owned = is_owned

    async def convert(self, ctx: commands.Context[NecroBot], argument: str):
        allowed_types = self.allowed_types if self.allowed_types else get_args(CharacterType)
        char_id = 0
        if argument.isdigit():
            char_id = int(argument)

        query = await ctx.bot.db.query(
            "SELECT * FROM necrobot.Characters WHERE (LOWER(name)=$1 OR id=$2) AND type = ANY($3)",
            argument.lower(),
            char_id,
            allowed_types,
        )

        if not query:
            query = await ctx.bot.db.query(
                "SELECT * FROM necrobot.Characters WHERE LOWER(name) LIKE $1 AND type = ANY($2);",
                f"%{argument.lower()}%",
                allowed_types,
            )

        if not query:
            raise commands.BadArgument(f"Character **{argument}** could not be found.")

        if self.respect_obtainable and not query[0]["obtainable"]:
            raise commands.BadArgument(
                f"Characters **{query[0]['name']}** cannot currently be added to a banner"
            )

        if self.is_owned:
            owned = await ctx.bot.db.query(
                "SELECT char_id FROM necrobot.RolledCharacters WHERE char_id = $1 LIMIT 1;",
                query[0]["id"],
            )
            if not owned:
                raise BotError(f"You do not own this {query[0]['type']}.")

        return query[0]


class GachaBannerConverter(commands.Converter[dict]):
    def __init__(self, respect_ongoing: bool = True):
        self.respect_ongoing = respect_ongoing

    async def convert(self, ctx: commands.Context[NecroBot], argument: str):
        banner_id = 0
        if argument.isdigit():
            banner_id = int(argument)

        query = await ctx.bot.db.query(
            "SELECT * FROM necrobot.Banners WHERE (LOWER(name)=$1 OR id=$2) AND guild_id = $3",
            argument.lower(),
            banner_id,
            ctx.guild.id,
        )

        if not query:
            query = await ctx.bot.db.query(
                "SELECT * FROM necrobot.Banners WHERE LOWER(name) LIKE $1 AND guild_id = $2;",
                f"%{argument.lower()}%",
                ctx.guild.id,
            )

        if not query:
            raise commands.BadArgument(f"Banner **{argument}** could not be found.")

        if self.respect_ongoing and not query[0]["ongoing"]:
            raise commands.BadArgument(f"Banner **{query[0]['name']}** is not ongoing")

        return query[0]
