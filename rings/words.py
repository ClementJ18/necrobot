import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

from rings.utils.config import dictionnary_key
from rings.utils.utils import BotError
from rings.utils.ui import paginate

import random
import aiohttp


class Literature(commands.Cog):
    """Commands related to words and literature"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ud", aliases=["urbandictionary"])
    async def udict(self, ctx: commands.Context, *, word: str):
        """Searches for the given word on urban dictionnary

        {usage}

        __Example__
        `{pre}ud pimp` - searches for pimp on Urban dictionnary"""
        async with self.bot.session.get(
            f"http://api.urbandictionary.com/v0/define?term={word.lower()}"
        ) as r:
            definitions = (await r.json())["list"]

        if not definitions:
            raise BotError("No definition found for this word.")

        def embed_maker(view, entry):
            definition = entry["definition"][:2048].replace("[", "").replace("]", "")
            embed = discord.Embed(
                title=f"{word.title()} ({view.page_number}/{view.page_count})",
                url="http://www.urbandictionary.com/",
                colour=self.bot.bot_color,
                description=definition,
            )

            if entry["example"]:
                embed.add_field(
                    name="Examples",
                    value=entry["example"][:2048].replace("[", "").replace("]", ""),
                    inline=False,
                )

            return embed

        await paginate(ctx, definitions, 1, embed_maker)

    async def get_def(self, word):
        url = f"https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}?key={dictionnary_key}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                definition = await resp.json()

        return definition

    @commands.command()
    @commands.cooldown(3, 60, BucketType.user)
    async def define(self, ctx: commands.Context, *, word: str):
        """Defines the given word, a high cooldown command so use carefully.

        {usage}

        __Example__
        `{pre}define sand` - defines the word sand
        `{pre}define life` - defines the word life"""
        word = word.lower()
        definitions = await self.get_def(word)

        if isinstance(definitions, str):
            word = f"{word} ({definitions})"
            definitions = await self.get_def(definitions)

        if not definitions:
            raise BotError("Could not find the word or any similar matches.")

        if isinstance(definitions[0], str):
            raise BotError(f"Could not find the word, similar matches: {', '.join(definitions)}")

        def embed_maker(view, entry):
            description = "\n -".join(entry["shortdef"])
            embed = discord.Embed(
                title=f"{word.title()} ({view.page_number}/{view.page_count})",
                url="https://www.merriam-webster.com/",
                colour=self.bot.bot_color,
                description=f"-{description}",
            )
            embed.set_footer(**self.bot.bot_footer)

            return embed

        await paginate(ctx, definitions, 1, embed_maker)

    @commands.command()
    async def shuffle(self, ctx: commands.Context, *, sentence):
        """Shuffles every word in a sentence

        {usage}

        __Examples__
        `{pre}shuffle Fun time` - uFn imet
        """
        if not sentence:
            raise BotError("Please provide a sentence to shuffle")

        shuffled = []
        sentence = sentence.split()
        for word in sentence:
            new_word = list(word)
            random.shuffle(new_word)
            shuffled.append("".join(new_word))

        await ctx.send(" ".join(shuffled))


async def setup(bot):
    await bot.add_cog(Literature(bot))
