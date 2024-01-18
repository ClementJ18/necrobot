from __future__ import annotations
import re

from typing import TYPE_CHECKING, List, Literal, get_args

import discord
from discord.ext import commands
from rapidfuzz import process
from unidecode import unidecode

from rings.utils.utils import time_converter

if TYPE_CHECKING:
    from bot import NecroBot


class MemberConverter(commands.MemberConverter):
    """Member converter but case insensitive"""

    async def convert(self, ctx: commands.Context[NecroBot], argument: str) -> discord.Member:
        try:
            basic_member = await super().convert(ctx, argument)
        except commands.BadArgument:
            pass
        else:
            return basic_member

        for attr in ["display_name", "name"]:
            result = [
                (m[2], m[1])
                for m in process.extract(
                    argument,
                    {r: unidecode(getattr(r, attr)) for r in ctx.guild.members},
                    limit=None,
                    score_cutoff=75,
                )
            ]
            if result:
                break
        else:
            raise commands.BadArgument(f'Member "{argument}" not found.')

        sorted_result = sorted(result, key=lambda m: m[1], reverse=True)
        return sorted_result[0][0]


class UserConverter(commands.UserConverter):
    """User converter but case insensitive"""

    async def convert(self, ctx: commands.Context[NecroBot], argument: str) -> discord.User:
        try:
            basic_user = await super().convert(ctx, argument)
        except commands.BadArgument:
            pass
        else:
            return basic_user

        for attr in ["display_name", "name"]:
            result = [
                (m[2], m[1])
                for m in process.extract(
                    argument,
                    {r: unidecode(getattr(r, attr)) for r in ctx.bot.users},
                    limit=None,
                    score_cutoff=75,
                )
            ]
            if result:
                break
        else:
            raise commands.BadArgument(f'User "{argument}" not found.')

        sorted_result = sorted(result, key=lambda m: m[1], reverse=True)
        return sorted_result[0][0]


class RoleConverter(commands.RoleConverter):
    """Converts to a role but case insensitive"""

    async def convert(self, ctx: commands.Context[NecroBot], argument) -> discord.Role:
        try:
            basic_role = await super().convert(ctx, argument)
        except commands.BadArgument:
            pass
        else:
            return basic_role

        result = [
            (m[2], m[1])
            for m in process.extract(
                argument,
                {r: unidecode(r.name) for r in ctx.guild.roles},
                limit=None,
                score_cutoff=75,
            )
        ]
        if not result:
            raise commands.BadArgument(f'Role "{argument}" not found.')

        sorted_result = sorted(result, key=lambda m: m[1], reverse=True)
        return sorted_result[0][0]


class GuildConverter(commands.IDConverter[discord.Guild]):
    async def convert(self, ctx: commands.Context[NecroBot], argument: str):
        result = None
        bot = ctx.bot
        guilds = bot.guilds

        result = discord.utils.find(lambda g: g.name.lower() == argument.lower(), guilds)

        if result:
            return result

        if argument.isdigit():
            result = bot.get_guild(int(argument))

            if result:
                return result

        raise commands.BadArgument(f'Guild "{argument}" not found.')


class BadgeConverter(commands.Converter[dict]):
    async def convert(self, ctx: commands.Context[NecroBot], argument: str):
        badge = await ctx.bot.db.get_badge_from_shop(name=argument)

        if not badge:
            raise commands.BadArgument(f'Badge "{argument}" not found.')

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
            raise commands.BadArgument(f"Please select a number between **{min_v}** and **{max_v}**")

        return value

    return check


class Grudge(commands.Converter[dict]):
    async def convert(self, ctx: commands.Context[NecroBot], argument: str):
        if not argument.isdigit():
            raise commands.BadArgument("Please supply a valid id")

        grudge = await ctx.bot.db.query("SELECT * FROM necrobot.Grudges WHERE id = $1", int(argument))

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


class WritableChannelConverter(commands.TextChannelConverter):
    async def convert(self, ctx: commands.Context[NecroBot], argument: str):
        result = await super().convert(ctx, argument)
        if not result.permissions_for(result.guild.me).send_messages:
            raise commands.BadArgument(f"I cannot send messages in {result.mention}")

        return result


CharacterType = Literal["character", "weapon", "artefact", "enemy"]


class GachaCharacterConverter(commands.Converter[dict]):
    def __init__(
        self,
        *,
        respect_obtainable: bool = False,
        allowed_types: List[CharacterType] = None,
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
        self.allowed_types = allowed_types if allowed_types is not None else []
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
                raise commands.BadArgument(f"You do not own this {query[0]['type']}.")

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


async def transform_mentions(ctx: commands.Context[NecroBot], message: str | None):
    if message is None:
        return None

    for converter, regex in (
        (MemberConverter(), r"(?<!\<)@(\w*)(?!\>)"),
        (RoleConverter(), r"(?<!\<)@(\w*)(?!\>)"),
        (commands.GuildChannelConverter(), r"(?<!\<)#([a-z0-9-_]*)(?!\>)"),
    ):
        message = await _transform_mentions(ctx, message, converter, regex)

    return message


async def _transform_mentions(
    ctx: commands.Context[NecroBot], message: str, converter: commands.Converter, regex: str
):
    new_string = ""
    last_index = 0

    for match in re.finditer(regex, message):
        try:
            member = (await converter.convert(ctx, match.group(1))).mention
        except commands.BadArgument:
            member = match.group(0)

        new_string += message[last_index : match.start()]
        new_string += member

        last_index = match.end()

    new_string += message[last_index:]
    return new_string
