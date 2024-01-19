from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List

import discord
import moddb
from bs4 import BeautifulSoup
from discord.ext import commands
from fuzzywuzzy import process

from rings.utils.ui import Paginator
from rings.utils.utils import BotError

if TYPE_CHECKING:
    from bot import NecroBot


class Modding(commands.Cog):
    """This module is used to connect to the various modding communities and allow to link and showcase work using \
    commands that determine which modding community to piggy back off and then subcommands which decide \
    what you want to show.
    """

    def __init__(self, bot: NecroBot):
        self.bot = bot

    #######################################################################
    ## Commands
    #######################################################################

    @commands.command()
    async def game(self, ctx: commands.Context[NecroBot], *, name: str):
        """This command takes in a game name from ModDB and returns a rich embed of it. Due to the high variety of \
        game formats, embed appearances will vary but it should always return one as long as it is given the name of \
        an existing game

        {usage}

        __Example__
        `{pre}game battle for middle earth` - creates a rich embed of the BFME ModDB page"""

        async with ctx.typing():
            await self._game(ctx, name)

    async def _game(self, ctx: commands.Context[NecroBot], *, name: str):
        def embed_maker(view: Paginator, entries: List[Dict[str, str]]):
            page = view.page_number
            embed = discord.Embed(
                title=game.name,
                colour=self.bot.bot_color,
                url=url,
                description=game.summary,
            )

            embed.set_author(
                name="ModDB",
                url="http://www.moddb.com",
                icon_url="http://i.imgur.com/aExydLm.png",
            )
            embed.set_footer(**self.bot.bot_footer)

            sections = ["Articles", "Reviews", "Downloads", "Videos", "Images"]
            nav_bar = [f"[{x}]({url}/{x.lower()})" for x in sections]
            embed.add_field(name="Navigation", value=" - ".join(nav_bar), inline=False)

            if page == 1:
                for article in game.articles[:4]:
                    embed.add_field(
                        name=article.name,
                        value=f"{article.summary}... [Link]({article.url})",
                        inline=False,
                    )
            elif page == 2:
                embed.add_field(
                    name="\u200b",
                    value=" ".join([f"[#{tag}]({url})" for tag, url in game.tags.items()]),
                    inline=False,
                )
                embed.add_field(
                    name="Misc: ",
                    value=f"{game.rating}/10 \n{game.profile.release.strftime('%d-%b-%Y')}\n[{game.profile.engine.name}]({game.profile.engine.url})\n**[Comment]({game.url}#commentform)**  -  **[Follow]({game.profile.follow})**",
                    inline=False,
                )
                embed.add_field(
                    name="Stats",
                    value=f"Rank: {game.stats.rank}/{game.stats.total}\nVisits: {game.stats.today}\nFiles:  {game.stats.files}\nArticles: {game.stats.articles}\nReviews: {game.stats.reviews}",
                    inline=False,
                )
            elif page == 3:
                suggestion_list = [
                    f"[{suggestion.name}]({suggestion.url})" for suggestion in game.suggestions
                ]
                embed.add_field(
                    name="You may also like",
                    value=" -" + " \n- ".join(suggestion_list),
                    inline=False,
                )

            return embed

        async with self.bot.session.get(
            f"https://www.moddb.com/games?filter=t&kw={name.replace(' ', '+')}&released=&genre=&theme=&indie=&players=&timeframe="
        ) as resp:
            soup = BeautifulSoup(await resp.text(), "html.parser")

        try:
            search_return = process.extract(
                name, [x.string for x in soup.find("div", class_="table").findAll("h4")]
            )[0][0]
        except IndexError as e:
            raise BotError("No game with that name found") from e

        url = moddb.utils.join(soup.find("div", class_="table").find("h4", string=search_return).a["href"])

        async with self.bot.session.get(url) as resp:
            soup = BeautifulSoup(await resp.text(), "html.parser")

        game = moddb.pages.Game(soup)
        await Paginator(1, [1, 2, 3], ctx.author, embed_maker=embed_maker).start(ctx)

    @commands.command()
    async def mod(self, ctx: commands.Context[NecroBot], *, name: str):
        """This command takes in a mod name from ModDB and returns a rich embed of it. Due to the high variety of \
        mod formats, embed appearances will vary but it should always return one as long as it is given the name of \
        an existing mod

        {usage}

        __Example__
        `{pre}mod edain mod` - creates a rich embed of the Edain Mod ModDB page"""

        async with ctx.typing():
            await self._mod(ctx, name)

    async def _mod(self, ctx: commands.Context[NecroBot], *, name: str):
        def embed_maker(view: Paginator, entries: List[Dict[str, str]]):
            page = view.page_number
            embed = discord.Embed(
                title=mod.name,
                colour=self.bot.bot_color,
                url=url,
                description=mod.summary,
            )

            embed.set_author(
                name="ModDB",
                url="http://www.moddb.com",
                icon_url="http://i.imgur.com/aExydLm.png",
            )
            embed.set_footer(**self.bot.bot_footer)

            sections = ["Articles", "Reviews", "Downloads", "Videos", "Images"]
            nav_bar = [f"[{x}]({url}/{x.lower()})" for x in sections]
            embed.add_field(name="Navigation", value=" - ".join(nav_bar), inline=False)

            if page == 1:
                for article in mod.articles[:4]:
                    embed.add_field(
                        name=article.name,
                        value=f"{article.summary}... [Link]({article.url})",
                        inline=False,
                    )
            elif page == 2:
                embed.add_field(
                    name="\u200b",
                    value=" ".join([f"[#{tag}]({url})" for tag, url in mod.tags.items()]),
                    inline=False,
                )
                embed.add_field(
                    name="Misc: ",
                    value=f"{mod.rating}/10 \n{mod.profile.release.strftime('%d-%b-%Y')}\n[{mod.profile.game.name}]({mod.profile.game.url})\n**[Comment]({mod.url}#commentform)**  -  **[Follow]({mod.profile.follow})**",
                    inline=False,
                )
                embed.add_field(
                    name="Stats",
                    value=f"Rank: {mod.stats.rank}/{mod.stats.total}\nVisits: {mod.stats.today}\nFiles:  {mod.stats.files}\nArticles: {mod.stats.articles}\nReviews: {mod.stats.reviews}",
                    inline=False,
                )
            elif page == 3:
                suggestion_list = [f"[{suggestion.name}]({suggestion.url})" for suggestion in mod.suggestions]
                embed.add_field(
                    name="You may also like",
                    value=" -" + " \n- ".join(suggestion_list),
                    inline=False,
                )

            return embed

        async with self.bot.session.get(
            f"http://www.moddb.com/mods?filter=t&kw={name.replace(' ', '+')}&released=&genre=&theme=&players=&timeframe=&mod=&sort=visitstotal-desc"
        ) as resp:
            soup = BeautifulSoup(await resp.text(), "html.parser")

        try:
            search_return = process.extract(
                name, [x.string for x in soup.find("div", class_="table").findAll("h4")]
            )[0][0]
        except IndexError as e:
            raise BotError("No mod with that name found") from e

        url = moddb.utils.join(soup.find("div", class_="table").find("h4", string=search_return).a["href"])

        async with self.bot.session.get(url) as resp:
            soup = BeautifulSoup(await resp.text(), "html.parser")

        mod = moddb.pages.Mod(soup)
        await Paginator(1, [1, 2, 3], ctx.author, embed_maker=embed_maker).start(ctx)


async def setup(bot: NecroBot):
    await bot.add_cog(Modding(bot))
