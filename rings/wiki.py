from __future__ import annotations

import asyncio
import datetime
import re
import urllib
from typing import TYPE_CHECKING

import discord
from bs4 import BeautifulSoup
from discord.ext import commands
from fuzzywuzzy import process

from rings.utils.utils import BotError

if TYPE_CHECKING:
    from bot import NecroBot


def _check_error_response(response: dict, query: str):
    """check for default error messages and throw correct exception"""
    if "error" in response:
        http_error = ["HTTP request timed out.", "Pool queue is full"]
        geo_error = [
            "Page coordinates unknown.",
            "One of the parameters gscoord, gspage, gsbbox is required",
            "Invalid coordinate provided",
        ]
        err = response["error"]["info"]

        if err in http_error:
            raise ValueError(query)
        if err in geo_error:
            raise ValueError(err)
        raise ValueError(err)


class Wiki(commands.Cog):
    """A series of wikia-related commands. Used to search the biggest fan-made database of \
    information."""

    def __init__(self, bot: NecroBot):
        self.bot = bot
        self.API_URL = "http://tolkiengateway.net/w/api.php"
        self.FANDOM_API_URL = "https://{sub_wikia}.fandom.com/api.php"
        self.RATE_LIMIT = False
        self.RATE_LIMIT_MIN_WAIT = None
        self.RATE_LIMIT_LAST_CALL: datetime.datetime = None
        self.USER_AGENT = "necrobot (https://github.com/ClementJ18/necrobot)"
        self.LANG = ""

    #######################################################################
    ## Functions
    #######################################################################

    async def _wiki_request(self, params: dict, fandom: str):
        """
        Make a request to the Wikia API using the given search parameters.
        Returns a parsed dict of the JSON response.
        """
        if fandom is not None:
            api_url = self.FANDOM_API_URL.format(sub_wikia=fandom)
        else:
            api_url = self.API_URL

        params["format"] = "json"
        headers = {"User-Agent": self.USER_AGENT}

        if (
            self.RATE_LIMIT
            and self.RATE_LIMIT_LAST_CALL
            and self.RATE_LIMIT_LAST_CALL + self.RATE_LIMIT_MIN_WAIT
            > datetime.datetime.now(datetime.timezone.utc)
        ):

            # it hasn't been long enough since the last API call
            # so wait until we're in the clear to make the request

            wait_time = (self.RATE_LIMIT_LAST_CALL + self.RATE_LIMIT_MIN_WAIT) - datetime.datetime.now(
                datetime.timezone.utc
            )
            await asyncio.sleep(int(wait_time.total_seconds()))

        async with self.bot.session.get(api_url, params=params, headers=headers) as resp:
            r = await resp.json()

        if self.RATE_LIMIT:
            self.RATE_LIMIT_LAST_CALL = datetime.datetime.now(datetime.timezone.utc)

        return r

    async def search(self, query, fandom=None):
        search_params = {
            "action": "query",
            "generator": "search",
            "prop": "info",
            "gsrsearch": query,
        }

        request = await self._wiki_request(search_params, fandom)
        _check_error_response(request, query)

        return list(request["query"]["pages"].values())

    async def page(self, page_id, fandom=None):
        query_params = {
            "action": "query",
            "prop": "info",
            "rvprop": "content",
            "redirects": "",
            "inprop": "url",
            "rvlimit": 1,
            "rvsection": 0,
            "pageids": page_id,
        }

        request = await self._wiki_request(query_params, fandom)
        _check_error_response(request, page_id)
        result = request["query"]["pages"][str(page_id)]

        return result

    async def parse(self, page_id, fandom=None):
        query_params = {
            "action": "parse",
            "pageid": page_id,
            "prop": "text|images",
            "section": 0,
        }

        request = await self._wiki_request(query_params, fandom)
        _check_error_response(request, page_id)
        return request

    async def get_sections(self, page_id, fandom=None):
        query_params = {
            "action": "parse",
            "pageid": page_id,
            "prop": "sections",
        }

        request = await self._wiki_request(query_params, fandom)
        _check_error_response(request, page_id)
        return request

    async def mediawiki_handler(self, ctx: commands.Context[NecroBot], article: str, fandom: str = None):

        if fandom is not None:
            base = f"https://{fandom}.wikia.com"
            name = fandom.title() + " Wiki"
        else:
            name = "Tolkien Gateway"
            base = "http://tolkiengateway.net"

        if article is None:
            return await ctx.send(f"<{base}>")

        results = await self.search(article, fandom)
        if not results:
            raise BotError("Could not find any article matching the query on that wiki")

        names = []
        ids = []
        for x in results:
            names.append(x["title"])
            ids.append(x["pageid"])

        e = process.extract(article, names, limit=len(names))
        page_id = ids.pop(names.index(e.pop(0)[0]))

        page = await self.page(page_id, fandom)

        msg = f"List of results: {', '.join([x[0] for x in e])}"
        url = page["fullurl"]

        parsed = await self.parse(page_id, fandom)

        soup = BeautifulSoup(parsed["parse"]["text"]["*"], "html.parser")
        description = [x for x in soup.find_all("p") if "aside" not in str(x) and x.text.strip()]
        if not description:
            description = "No description found"
        else:
            description = description[0].text

        thumbnail = soup.find("img")

        embed = discord.Embed(
            title=page["title"],
            colour=self.bot.bot_color,
            url=url,
            description=re.sub(r"\[.*?\]", "", description),
        )

        if thumbnail is not None:
            thumbnail = thumbnail["src"]
            if not thumbnail.startswith("http"):
                thumbnail = base + thumbnail

            embed.set_thumbnail(url=thumbnail)

        icon = "https://i.imgur.com/lPPQzRg.png"
        embed.set_author(name=name, url=base, icon_url=icon)
        embed.set_footer(**self.bot.bot_footer)

        await ctx.send(msg, embed=embed)

    #######################################################################
    ## Commands
    #######################################################################

    @commands.command()
    async def edain(self, ctx: commands.Context[NecroBot], *, article: str = None):
        """Performs a search on the Edain Mod Wiki for the give article name. If an article is found then it will \
        return a rich embed of it, else it will return a list of a related articles and an embed of the first related article.

        {usage}

        __Example__
        `{pre}edain Castellans` - print a rich embed of the Castellans page
        `{pre}edain Battering Ram` - prints a rich embed of the Battering Ram disambiguation page"""
        async with ctx.typing():
            await self.mediawiki_handler(ctx, article, "edain")

    @commands.command()
    async def faq(self, ctx: commands.Context[NecroBot], *, question: str = None):
        """Replies with up to 5 links from the Edain FAQ that have matched close to the initial question.

        {usage}

        __Example__
        `{pre}faq mirkwood faction` - will reply with links on why Mirkwood isn't its own faction
        """
        await self.faq_handler("edain", ctx, question)

    async def faq_handler(self, mod: str, ctx: commands.Context[NecroBot], question: str):
        base = f"https://{mod}.wikia.com/wiki/Frequently_Asked_Questions"
        if question is None:
            return await ctx.send(base)

        sections = await self.get_sections("3908", mod)
        questions = [
            re.sub(r"<.+?>", "", x["line"]) for x in sections["parse"]["sections"] if x["toclevel"] == 2
        ]
        matches = process.extract(question, questions, limit=5)
        message = []

        for section in matches:
            if section[1] < 55:
                continue

            section = section[0]
            url = urllib.parse.quote(section.replace(" ", "_"), safe="/:").replace("%", ".")
            message.append(f"[{section}]({base}#{url})")

        if not message:
            raise BotError("Sorry, didn't find anything")

        embed = discord.Embed(
            title="Frequently Asked Questions",
            colour=self.bot.bot_color,
            url=base,
            description="\n".join(message),
        )

        embed.set_footer(**self.bot.bot_footer)

        await ctx.send(embed=embed)

    @commands.command()
    async def aotr(self, ctx: commands.Context[NecroBot], *, article: str = None):
        """Performs a search on the Age of the Ring Wiki for the give article name. If an article is found then it will \
        return a rich embed of it, else it will return a list of a related articles and an embed of the first related article.

        {usage}

        __Example__
        `{pre}aotr Castellans` - print a rich embed of the Castellans page
        `{pre}aotr Battering Ram` - prints a rich embed of the Battering Ram disambiguation page"""
        async with ctx.typing():
            await self.mediawiki_handler(ctx, article, "aotr")

    @commands.command()
    async def wiki(self, ctx: commands.Context[NecroBot], sub_wiki, *, article: str = None):
        """Performs a search on the given wiki (if valid) for the given article name. If an article is found then it \
        will return a rich embed of it, else it will return a list of a related articles and an embed of the first related article.

        {usage}

        __Example__
        `{pre}wiki disney Donald Duck` - creates a rich embed of the Donald Duck page
        `{pre}wiki transformers Optimus` - searches for the 'Optimus Page' and returns a list of search results and a \
        rich embed of the first one."""
        async with ctx.typing():
            await self.mediawiki_handler(ctx, article, sub_wiki)

    @commands.command()
    async def lotr(self, ctx: commands.Context[NecroBot], *, article_name: str = None):
        """Performs a search on the Tolkien Gateway for the give article name. If an article is found then it \
        will return a rich embed of it, else it will return a list of a related articles and an embed of the first related article.

        {usage}

        __Example__
        `{pre}lotr Finrod` - creates an embed of Finrod Felagund
        `{pre}lotr Fellowship` - searches for 'Fellowship' and returns the first result"""
        async with ctx.typing():
            await self.mediawiki_handler(ctx, article_name)


async def setup(bot: NecroBot):
    await bot.add_cog(Wiki(bot))
