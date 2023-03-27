import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

from rings.utils.utils import BotError
from rings.utils.checks import has_perms, guild_only
from rings.utils.converters import UserConverter
from rings.utils.ui import Confirm, paginate, HungerGames

import re
import random
import asyncio
import aiohttp
import itertools
from io import BytesIO
from bs4 import BeautifulSoup

class Misc(commands.Cog):
    """A cog for all bunch commands that don't have a specific category they can stick to."""

    def __init__(self, bot):
        self.bot = bot
        self.faction_regex = r"(gondor|rohan|isengard|mordor|ered luin|angmar|erebor|iron hills|lothlorien|imladris|misty mountains)"

    #######################################################################
    ## Functions
    #######################################################################

    async def setup_table(self):
        for faction in self.bot.settings["messages"]["factions"]:
            for enemy in self.bot.settings["messages"]["factions"]:
                await self.bot.db.query(
                    "INSERT INTO necrobot.InternalRanked VALUES ($1, $2, 0, 0) ON CONFLICT DO NOTHING",
                    faction,
                    enemy,
                )

    #######################################################################
    ## Commands
    #######################################################################

    @commands.command()
    @commands.cooldown(3, 5, BucketType.channel)
    async def cat(self, ctx : commands.Context):
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
    async def dog(self, ctx : commands.Context):
        """Posts a random dog picture from random.dog

        {usage}"""
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False)
        ) as cs:
            async with cs.get("https://random.dog/woof.json") as r:
                res = await r.json()
                await ctx.send(embed=discord.Embed().set_image(url=res["url"]))

    @commands.command()
    async def fight(self, ctx : commands.Context, *, tributes):
        """Takes in a list of tributes separated by `,` and simulates a hunger games based on Bransteele's Hunger Game
        Simulator. More than one tribute needs to be supplied. Duplicate names will be supressed.

        {usage}

        __Example__
        `{pre}fight john , bob , emilia the trap` - starts a battle between tributes john, bob and emilia the trap"""
        tributes_list = list(set([f"**{x.strip()}**" for x in tributes.split(",")]))
        if len(tributes_list) < 2:
            await ctx.send(
                ":negative_squared_cross_mark: | Please provide at least two names separated by `,`"
            )
            return

        if len(tributes_list) > 32:
            await ctx.send(
                ":negative_squared_cross_mark: | Please provide no more than 32 names separated by `,`."
            )

        hg = HungerGames(self.bot, tributes_list)
        embed = hg.prepare_next_phase(hg.get_next_phase())
        hg.message = await ctx.send(embed=embed, view=hg)
        await hg.wait()

    @commands.group(invoke_without_command=True, aliases=["matchup"])
    @guild_only(496617962334060545)
    async def matchups(self, ctx : commands.Context, *, arguments=None):
        """Get data about the results of matchups stored in the bot. You can pass either a faction name, a sorting key
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

        def embed_maker(view, entries):
            entries.sort(**sort.get(sort_key, sort["name"]))
            description = ""
            intro = ""

            wins = 0
            games = 0

            for entry in entries:
                index = self.bot.settings["messages"]["factions"].index(entry[1])
                emoji_id = self.bot.settings["messages"]["emotes"][index]
                emoji = self.bot.get_emoji(emoji_id)

                if entry["enemy"] == entry["faction"]:
                    intro = f'{emoji} {self.bot.settings["messages"]["msg"][index]} {emoji}\n\n'
                    continue

                total = entry[3] + entry[2]
                percent = entry[3] / total if total > 0 else 0
                description += f"{emoji} **{entry['enemy']}** - {entry['victories']}/{total} ({int(percent*100)}%)\n"

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
                "key": lambda x: x["defeats"]
                if x["victories"] + x["defeats"] > 0
                else -1,
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
            await paginate(ctx, [list(y) for x, y in stats], 1, embed_maker)

    @matchups.command(name="reset")
    @guild_only(496617962334060545)
    @commands.check_any(
        commands.has_role(497009979857960963), has_perms(6)
    )  # has Admin role on server or is Bot Admin
    async def matchups_reset(self, ctx : commands.Context):
        """Reset the counters

        {usage}
        """
        view = Confirm(
            confirm_msg=":white_check_mark: | All counters reset",
        )

        view.message = await ctx.send(
            "Do you want to delete all the ranked logs and reset the counters for the factions?",
            view=view,
        )
        await view.wait()

        if view.value:
            await self.bot.db.query(
                "UPDATE necrobot.InternalRanked SET defeats = 0, victories = 0"
            )
            await self.bot.db.query("DELETE FROM necrobot.InternalRankedLogs")

    @matchups.command(name="logs")
    @guild_only(496617962334060545)
    @commands.check_any(
        commands.has_role(497009979857960963), has_perms(6)
    )  # has Admin role on server or is Bot Admin
    async def matchups_logs(self, ctx : commands.Context, *, args=None):
        """Check who submitted what results, can be filtered using arguments.

        user=[user]
        winner=[faction]
        loser=[faction]

        {usage}

        __Examples__
        `{pre}matchups logs winner=Isengard` - get the logs of all the matches where isengard won
        `{pre}matchups user=@Necrobot` - get the logs of all the matches where necrobot won
        """

        def embed_maker(view, entries):
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
                title=f"Logs ({view.page_number}/{view.page_count})",
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

        logs = await self.bot.db.query(
            "SELECT * FROM necrobot.InternalRankedLogs ORDER BY log_date DESC"
        )

        filters = {}
        if args is not None:
            filters_r = re.findall(
                r"(user|winner|loser)=(.*?)(?=user|winner|loser|$)", args
            )
            for key, value in filters_r:
                filters[key] = await filter_check[key](value)

            logs = [log for log in logs if check_entry(log)]

        await paginate(ctx, logs, 15, embed_maker)

    @matchups.command(name="delete")
    @guild_only(496617962334060545)
    @commands.check_any(
        commands.has_role(497009979857960963), has_perms(6)
    )  # has Admin role on server or is Bot Admin
    async def matchups_delete(self, ctx : commands.Context, log_id: int):
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

        await ctx.send(":white_check_mark: | Log removed, counters adjusted.")

    # @commands.command()
    async def pdf(self, ctx : commands.Context, *, doi):
        """Get a PDF from a doi using sci-hub

        {usage}
        """

        async with self.bot.session.post(
            "https://sci-hub.mksa.top/",
            params={"sci-hub-plugin-check": "", "request": doi},
        ) as resp:
            soup = BeautifulSoup(await resp.text(), "html.parser")

        pdf_url = soup.find("iframe")["src"]
        print(pdf_url)
        async with self.bot.session.get(pdf_url) as resp:
            pdf = BytesIO(await resp.read())
            pdf.seek(0)
            # not working cause cloudflare protection

        ifile = discord.File(pdf, filename="converted.html")
        await ctx.send(file=ifile)

    #######################################################################
    ## Events
    #######################################################################

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.channel_id != 840220523865702400:
            return

        if not payload.emoji.is_custom_emoji():
            return

        if not payload.emoji.id in self.bot.settings["messages"]["emotes"]:
            return

        g = self.bot.get_guild(payload.guild_id)
        if g.get_role(497009979857960963) in g.get_member(payload.user_id).roles:
            return

        faction_index = self.bot.settings["messages"]["victories"].index(
            payload.message_id
        )
        faction_name = self.bot.settings["messages"]["factions"][faction_index]

        enemy_index = self.bot.settings["messages"]["emotes"].index(payload.emoji.id)
        enemy_name = self.bot.settings["messages"]["factions"][enemy_index]

        def check(pay):
            return (
                pay.user_id == payload.user_id
                and pay.message_id == payload.message_id
                and str(pay.emoji) == "\N{WHITE HEAVY CHECK MARK}"
            )

        try:
            checkmark = await self.bot.wait_for(
                "raw_reaction_add", check=check, timeout=15
            )
        except asyncio.TimeoutError:
            return await self.bot._connection.http.remove_reaction(
                payload.channel_id,
                payload.message_id,
                payload.emoji._as_reaction(),
                payload.user_id,
            )

        await asyncio.sleep(2)
        await self.bot.db.query(
            "UPDATE necrobot.InternalRanked SET victories = victories + 1 WHERE faction = $1 AND enemy = $2",
            faction_name,
            enemy_name,
        )

        await self.bot.db.query(
            "UPDATE necrobot.InternalRanked SET defeats = defeats + 1 WHERE faction = $1 AND enemy = $2",
            enemy_name,
            faction_name,
        )

        await self.bot.db.query(
            "INSERT INTO necrobot.InternalRankedLogs(user_id, faction, enemy, faction_won) VALUES ($1, $2, $3, $4)",
            payload.user_id,
            faction_name,
            enemy_name,
            True,
        )

        await self.bot._connection.http.remove_reaction(
            payload.channel_id,
            payload.message_id,
            payload.emoji._as_reaction(),
            payload.user_id,
        )
        await self.bot._connection.http.remove_reaction(
            payload.channel_id,
            payload.message_id,
            checkmark.emoji._as_reaction(),
            payload.user_id,
        )


async def setup(bot):
    await bot.add_cog(Misc(bot))
