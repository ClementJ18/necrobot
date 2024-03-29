from __future__ import annotations

import functools
import itertools
import random
import re
from io import BytesIO
from typing import TYPE_CHECKING, Any, Dict, List

import aiohttp
import discord
import matplotlib
import matplotlib.pyplot as plt
import pandas as pds
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

from rings.utils.checks import guild_only, has_perms
from rings.utils.converters import UserConverter
from rings.utils.ui import Confirm, Paginator
from rings.utils.utils import POSITIVE_CHECK, BotError

matplotlib.use("agg")
import matplotlib.pyplot as plt

from .ui import HungerGames, MatchupView

if TYPE_CHECKING:
    from bot import NecroBot


class Misc(commands.Cog):
    """A cog for all bunch commands that don't have a specific category they can stick to."""

    def __init__(self, bot: NecroBot):
        self.bot = bot
        self.faction_regex = r"(gondor|rohan|isengard|mordor|ered luin|angmar|erebor|iron hills|lothlorien|imladris|misty mountains)"

    #######################################################################
    ## Functions
    #######################################################################

    async def setup_table(self):
        for faction in MatchupView.faction_options:
            for enemy in MatchupView.faction_options:
                await self.bot.db.query(
                    "INSERT INTO necrobot.InternalRanked VALUES ($1, $2, 0, 0) ON CONFLICT DO NOTHING",
                    faction,
                    enemy,
                )

    #######################################################################
    ## Commands
    #######################################################################

    @commands.command(enabled=False)
    @commands.cooldown(3, 5, BucketType.channel)
    async def cat(self, ctx: commands.Context[NecroBot]):
        """Posts a random cat picture from random.cat

        {usage}"""
        async with self.bot.session.get("http://aws.random.cat/meow") as r:
            try:
                res = await r.json()
                await ctx.send(embed=discord.Embed().set_image(url=res["file"]))
                self.bot.cat_cache.append(res["file"])
            except aiohttp.ClientResponseError as e:
                if self.bot.cat_cache:
                    await ctx.send(
                        "API overloading, have a cached picture instead.",
                        embed=discord.Embed(colour=self.bot.bot_color).set_image(
                            url=random.choice(self.bot.cat_cache)
                        ),
                    )
                else:
                    raise BotError(
                        "API overloading and cache empty, looks like you'll have to wait for now."
                    ) from e

    @commands.command()
    async def dog(self, ctx: commands.Context[NecroBot]):
        """Posts a random dog picture from random.dog

        {usage}"""
        async with self.bot.session.get("https://random.dog/woof.json", ssl=False) as r:
            res = await r.json()
            await ctx.send(embed=discord.Embed().set_image(url=res["url"]))

    @commands.command()
    async def fight(self, ctx: commands.Context[NecroBot], *, tributes: str):
        """Takes in a list of tributes separated by `,` and simulates a hunger games based on Bransteele's Hunger Game \
        Simulator. More than one tribute needs to be supplied. Duplicate names will be supressed.

        {usage}

        __Example__
        `{pre}fight john , bob , emilia the trap` - starts a battle between tributes john, bob and emilia the trap"""
        tributes_list = list(set([f"**{x.strip()}**" for x in tributes.split(",")]))
        if len(tributes_list) < 2:
            raise BotError("Please provide at least two names separated by `,`")

        if len(tributes_list) > 32:
            raise BotError("Please provide no more than 32 names separated by `,`.")

        hg = HungerGames(self.bot, tributes_list, ctx.author)
        embed = hg.prepare_next_phase(hg.get_next_phase())
        hg.message = await ctx.send(embed=embed, view=hg)
        await hg.wait()

    @commands.group(invoke_without_command=True, aliases=["matchup"])
    @guild_only(496617962334060545)
    async def matchups(self, ctx: commands.Context[NecroBot], *, arguments=None):
        """Get data about the results of matchups stored in the bot. You can pass either a faction name, a sorting key \
        or both.

        Factions Names:
            - Misty Mountains
            - Gondor
            - Rohan
            - Isengard
            - Mordor
            - Ered Luin
            - Iron Hills
            - Erebor
            - Angmar
            - Lothlorien
            - Imladris

        Sort Key:
            - winrate
            - played
            - victories
            - defeats

        {usage}

        __Examples__
        `{pre}matchups Mordor defeats` - show the stats for Mordor sorted by the enemies they have the least victories against
        `{pre}matchups played` - show the stats for all the factions sorted by the enemies they battled the most
        `{pre}matchups Mordor` - show the stats for Mordor (sorted alphabetically by default)
        `{pre}matchups` - show the stats for all the factions (sorted alphabetically by default)


        """

        def embed_maker(view: Paginator, entries: List[Dict[str, Any]]):
            entries.sort(**sort.get(sort_key, sort["name"]))
            description = ""
            intro = ""

            wins = 0
            games = 0

            for entry in entries:
                emoji = discord.PartialEmoji.from_str(MatchupView.faction_options[entry[1]]["emoji"])

                if entry["enemy"] == entry["faction"]:
                    intro = f'{emoji} {MatchupView.faction_options[entry[1]]["message"]} {emoji}\n\n'
                    continue

                total = entry[3] + entry[2]
                percent = entry[3] / total if total > 0 else 0
                description += (
                    f"{emoji} **{entry['enemy']}** - {entry['victories']}/{total} ({int(percent*100)}%)\n"
                )

                wins += entry[3]
                games += total

            embed = discord.Embed(
                title=entries[0]["faction"],
                description=intro + description,
                colour=self.bot.bot_color,
            )
            embed.set_footer(**self.bot.bot_footer)

            avg_wr = wins / games if games > 0 else 0
            avg_wr_str = f"- Average Winrate: {int(avg_wr*100)}% ({wins}/{games})"

            embed.add_field(name="Stats", value="\n".join([avg_wr_str]), inline=False)
            return embed

        sort = {
            "winrate": {
                "key": lambda x: x["victories"] / (x["victories"] + x["defeats"])
                if x["victories"] + x["defeats"] > 0
                else -1,
                "reverse": True,
            },
            "name": {"key": lambda x: x[1], "reverse": False},
            "played": {"key": lambda x: x["victories"] + x["defeats"], "reverse": True},
            "victories": {"key": lambda x: x["victories"], "reverse": True},
            "defeats": {
                "key": lambda x: x["defeats"] if x["victories"] + x["defeats"] > 0 else -1,
                "reverse": True,
            },
        }

        factions = None
        sort_key = "name"
        if arguments:
            arguments = arguments.lower()
            factions = re.findall(self.faction_regex, arguments)
            arguments = re.sub(self.faction_regex, "", arguments).strip()
            sort_key = arguments if arguments != "" else sort_key

        if factions:
            faction = factions[0]
            stats = await self.bot.db.query(
                "SELECT * FROM necrobot.InternalRanked WHERE LOWER(faction) = $1 ORDER BY enemy",
                faction,
            )
            if not stats:
                raise BotError("No results")

            await ctx.send(embed=embed_maker(None, stats))
        else:
            stats = await self.bot.db.query("SELECT * FROM necrobot.InternalRanked")

            stats.sort(key=lambda x: x["faction"])
            stats = itertools.groupby(stats, lambda x: x["faction"])
            await Paginator(1, [list(y) for _, y in stats], ctx.author, embed_maker=embed_maker).start(ctx)

    @matchups.command(name="reset")
    @guild_only(496617962334060545)
    @commands.check_any(
        commands.has_role(497009979857960963), has_perms(6)
    )  # has Admin role on server or is Bot Admin
    async def matchups_reset(self, ctx: commands.Context[NecroBot]):
        """Reset the counters

        {usage}
        """
        view = Confirm(
            ctx.author,
            confirm_msg=f"{POSITIVE_CHECK} | All counters reset",
        )

        view.message = await ctx.send(
            "Do you want to reset the counters for the factions?",
            view=view,
        )
        await view.wait()

        if view.value:
            await self.bot.db.query("UPDATE necrobot.InternalRanked SET defeats = 0, victories = 0")

    @matchups.command(name="logs")
    @guild_only(496617962334060545)
    @commands.check_any(
        commands.has_role(497009979857960963), has_perms(6)
    )  # has Admin role on server or is Bot Admin
    async def matchups_logs(self, ctx: commands.Context[NecroBot], *, args=None):
        """Check who submitted what results, can be filtered using arguments.

        user=[user]
        winner=[faction]
        loser=[faction]

        {usage}

        __Examples__
        `{pre}matchups logs winner=Isengard` - get the logs of all the matches where isengard won
        `{pre}matchups user=@Necrobot` - get the logs of all the matches where necrobot won
        """

        def embed_maker(view: Paginator, entries: List[Dict[str, Any]]):
            description = ""
            for entry in entries:
                submitter = self.bot.get_user(entry["user_id"])
                if submitter is None:
                    name = f"User Left ({entry['user_id']})"
                else:
                    name = submitter.mention

                time = entry[4].strftime("%Y-%m-%d %H:%M")
                description += f"- {name}: **{entry['faction']}** won against **{entry['enemy']}** at {time} (ID: **{entry['id']}**)\n"

            embed = discord.Embed(
                title=f"Logs ({view.page_string})",
                description=description,
                colour=self.bot.bot_color,
            )
            embed.set_footer(**self.bot.bot_footer)
            return embed

        def check_entry(entry):
            user = filters.get("user")
            if user is not None and entry["user_id"] != user:
                return False

            winner = filters.get("winner")
            if winner is not None and entry["faction"].lower() != winner:
                return False

            loser = filters.get("loser")
            if loser is not None and entry["enemy"].lower() != loser:
                return False

            return True

        async def user(u):
            user_id = (await UserConverter().convert(ctx, u)).id
            return user_id

        async def winner(w):
            f = re.findall(self.faction_regex, w.lower())
            if not f:
                raise BotError("No a valid faction")

            return f[0]

        async def loser(l):
            f = re.findall(self.faction_regex, l.lower())
            if not f:
                raise BotError("No a valid faction")

            return f[0]

        filter_check = {"user": user, "winner": winner, "loser": loser}

        logs = await self.bot.db.query("SELECT * FROM necrobot.InternalRankedLogs ORDER BY log_date DESC")

        filters = {}
        if args is not None:
            filters_r = re.findall(r"(user|winner|loser)=(.*?)(?=user|winner|loser|$)", args)
            for key, value in filters_r:
                filters[key] = await filter_check[key](value)

            logs = [log for log in logs if check_entry(log)]

        await Paginator(15, logs, ctx.author, embed_maker=embed_maker).start(ctx)

    @matchups.command(name="message")
    @commands.is_owner()
    async def matchups_message(self, ctx: commands.Context[NecroBot]):
        """Send and set the message for registering matchups. Only one such message can exist per server.

        {usage}
        """
        msg = await ctx.send(
            "Use this message to register victories and losses for factions in 1v1 games you have played. Select a winner, a loser and then click confirm.",
            view=MatchupView(),
        )
        self.bot.settings["matchup_views"][ctx.guild.id] = msg.id

    @matchups.command(name="delete")
    @guild_only(496617962334060545)
    @commands.check_any(
        commands.has_role(497009979857960963), has_perms(6)
    )  # has Admin role on server or is Bot Admin
    async def matchups_delete(self, ctx: commands.Context[NecroBot], log_id: int):
        """Delete a log to remove the entry and remove it from the counters. Get the log_id
        from the `matchup logs` command.

        {usage}"""
        log = await self.bot.db.query(
            "DELETE FROM necrobot.InternalRankedLogs WHERE id=$1 RETURNING (faction, enemy)",
            log_id,
            fetchval=True,
        )

        if not log:
            raise BotError("No log with that ID")

        await self.bot.db.query(
            "UPDATE necrobot.InternalRanked SET victories = victories - 1 WHERE faction = $1 AND enemy = $2",
            log[0],
            log[1],
        )

        await self.bot.db.query(
            "UPDATE necrobot.InternalRanked SET defeats = defeats - 1 WHERE enemy = $1 AND faction = $2",
            log[0],
            log[1],
        )

        await ctx.send(f"{POSITIVE_CHECK} | Log removed, counters adjusted.")

    def compile_stats(self, logs, faction):
        title = logs[0]["faction"] if logs[0]["faction"].lower() == faction else logs[0]["enemy"]
        emoji = discord.PartialEmoji.from_str(MatchupView.faction_options[title]["emoji"])
        intro = f'{emoji} {MatchupView.faction_options[title]["message"]} {emoji}\n\n'

        faction_data = {
            key: [(0, 0, logs[0]["log_date"], key)]
            for key in MatchupView.faction_options
            if key.lower() != faction
        }
        for log in logs:
            if log["faction"].lower() == faction:
                key = "enemy"
                victory = int(log["faction_won"])
            else:
                key = "faction"
                victory = int(not log["faction_won"])

            previous = faction_data[log[key]][-1]
            faction_data[log[key]].append((previous[0] + 1, previous[1] + victory, log["log_date"], log[key]))

        entries = [value for tup in faction_data.values() for value in tup]
        df = pds.DataFrame.from_records(entries, columns=["Total Matches", "Victories", "Date", "Faction"])
        df = df.reset_index(drop=True).set_index("Date")
        df["percent"] = (df["Victories"] / df["Total Matches"]) * 100
        df = (
            df.pivot_table(index="Date", columns="Faction", values="percent")
            .resample("M")
            .mean()
            .ffill()
            .fillna(0)
        )

        df.plot(alpha=0.7)
        plt.ylim(ymin=0)
        plt.ylabel("Win Rate (%)")
        plt.legend(
            bbox_to_anchor=(0, 1.02, 1, 0.2),
            loc="lower left",
            mode="expand",
            borderaxespad=0,
            ncol=3,
            fancybox=True,
            shadow=True,
        )
        plt.tight_layout()
        plt.grid(which="both", linestyle="dashed")

        figfile = BytesIO()
        plt.savefig(figfile, format="png")
        figfile.seek(0)
        ifile = discord.File(filename=f"graph_{faction}.png", fp=figfile)

        return title, intro, ifile

    @matchups.command(name="stats")
    @guild_only(496617962334060545)
    async def matchups_stats(self, ctx: commands.Context[NecroBot], *, arguments: str):
        """Get specific stats over time for a faction W/L

        {usage}
        """
        arguments = arguments.lower()
        factions = re.findall(self.faction_regex, arguments)
        if not factions:
            raise BotError("No faction detected in input string.")

        async with ctx.typing():
            faction = factions[0]
            logs = await self.bot.db.query(
                "SELECT * FROM necrobot.InternalRankedLogs WHERE LOWER(faction) = $1 OR LOWER(enemy) = $1 ORDER BY log_date DESC;",
                faction,
            )

            func = functools.partial(self.compile_stats, logs, faction)
            title, intro, ifile = await self.bot.loop.run_in_executor(None, func)

        await ctx.send(f"**__W/L {title}__**\n{intro}", file=ifile)
