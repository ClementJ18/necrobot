import discord
from discord.ext import commands


def has_perms(level):
    async def predicate(ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True

        if await ctx.bot.db.is_admin(ctx.message.author.id):
            return True

        if ctx.guild is None:
            raise commands.CheckFailure("Cannot use this command in DMs")

        perms = await ctx.bot.db.get_permission(ctx.message.author.id, ctx.guild.id)
        if perms < level:
            raise commands.CheckFailure(
                f"You do not have the required NecroBot permissions. Your permission level must be {level}"
            )

        return True

    predicate.level = level
    return commands.check(predicate)


def requires_mute_role():
    def predicate(ctx):
        if ctx.guild is None:
            raise commands.CheckFailure("Cannot use this command in DMs")

        if not ctx.bot.guild_data[ctx.guild.id]["mute"]:
            raise commands.CheckFailure(
                "Please set up the mute role with `n!mute role [rolename]` first."
            )

        return True

    return commands.check(predicate)


def leaderboard_enabled():
    async def predicate(ctx):
        if ctx.guild is None:
            raise commands.CheckFailure("Cannot use this command in DMs")

        settings = await ctx.bot.db.query(
            "SELECT message FROM necrobot.Leaderboards WHERE guild_id=$1",
            ctx.guild.id,
            fetchval=True,
        )
        if settings != "":
            return True

        raise commands.CheckFailure(
            "Leaderboard isn't currently enabled, enable it by setting a message"
        )

    return commands.check(predicate)


def mu_moderator(guild):
    if guild is None:
        return []

    ids = []
    for role in ["Edain Team", "Edain Community Moderator"]:
        obj = discord.utils.get(guild.roles, name=role)
        if not obj is None:
            ids.extend([x.id for x in obj.members])

    return ids


def mu_moderator_check():
    def predicate(ctx):
        ids = mu_moderator(ctx.guild)

        if ctx.author.id not in ids:
            raise commands.CheckFailure("You cannot use this command")

        return True

    return commands.check(predicate)


def guild_only(guild_id):
    def predicate(ctx):
        if ctx.guild is None:
            raise commands.CheckFailure("This command cannot be executed in DMs")

        if ctx.guild.id not in (guild_id, 311630847969198082):
            raise commands.CheckFailure("This command cannot be executed in this server")

        return True

    return commands.check(predicate)
