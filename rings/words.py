import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

from rings.utils.utils import react_menu
from rings.utils.config import define_headers

import re
import random
import aiohttp
import asyncio
import googletrans
import urbandictionary as ud

translator = googletrans.Translator()

class Literature():
    """Commands related to words and literature"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ud", aliases=["urbandictionary"])
    async def udict(self, ctx, *, word : str):
        """Searches for the given word on urban dictionnary

        {usage}

        __Example__
        `{pre}ud pimp` - searches for pimp on Urban dictionnary"""
        async with self.bot.session.get(f"http://api.urbandictionary.com/v0/define?term={word.lower()}") as r:
            try:
                definitions = await r.json()   
            except asyncio.TimeoutError:
                return         

        try:
            definition = random.choice(definitions["list"])
        except IndexError:
            await ctx.send(":negative_squared_cross_mark: | Sorry, I didn't find a definition for this word.")
            return

        embed = discord.Embed(title=word.title(), url="http://www.urbandictionary.com/", colour=discord.Colour(0x277b0), description=definition["definition"][:2048].replace("[", "").replace("]", ""))
        embed.add_field(name="__Examples__", value=definition["example"][:2048].replace("[", "").replace("]", ""))

        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    async def translate(self, ctx, lang : str, *, sentence : str):
        """Auto detects the language of the sentence you input and translates it to the desired language.

        {usage}

        __Example__
        `{pre}translate en Bonjour` - detects french and translates to english
        `{pre}translate ne Hello` - detects english and translates to dutch"""
        try:
            translated = translator.translate(sentence, dest=lang)
            await ctx.send(f"Translated `{translated.origin}` from {translated.src} to {translated.dest}: **{translated.text}**")
        except ValueError:
            await ctx.send(":negative_squared_cross_mark: | No such language, do `n!translate list` for all languages (Warning: Big text blob)")
        except AttributeError:
            await ctx.send(":negative_squared_cross_mark: | Goolge API being mean again, please wait for another fix to be patched through.")

    @translate.command(name="list")
    async def translate_list(self, ctx):
        """Use to display all possible languages to translate from

        {usage}"""
        text = ", ".join([f"**{googletrans.LANGUAGES[lang]}**: {lang}" for lang in googletrans.LANGUAGES])
        await ctx.send(text[:-2])

    @commands.command()
    @commands.cooldown(3, 60, BucketType.user)
    async def define(self, ctx, word : str):
        """Defines the given word, a high cooldown command so use carefully.

        {usage}

        __Example__
        `{pre}define sand` - defines the word sand
        `{pre}define life` - defines the word life"""
        word = word.lower()
        language = "en"
        async with aiohttp.ClientSession(headers=define_headers) as session:
            async with session.get(f'https://od-api.oxforddictionaries.com/api/v1/inflections/{language}/{word}') as resp:
                word = await resp.json()
                word = word["results"][0]["lexicalEntries"][0]["inflectionOf"][0]["id"]                
            async with session.get(f"https://od-api.oxforddictionaries.com/api/v1/entries/{language}/{word}") as resp:
                definition = await resp.json()

        def _embed_maker(index):
            description = definition["results"][0]["lexicalEntries"][0]["entries"][index]["etymologies"][0]
            embed = discord.Embed(title=word.title(), url="https://en.oxforddictionaries.com/", colour=discord.Colour(0x277b0), description=description)
            bot_ico = "https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128"
            embed.set_footer(text="Generated by NecroBot", icon_url=bot_ico)
            for entry in definition["results"][0]["lexicalEntries"]:
                form = entry["lexicalCategory"]
                message = ""
                try:
                    for entry_b in entry["entries"][index]["senses"]:
                        message += f'{entry["entries"][index]["senses"].index(entry_b) + 1}. {entry_b["definitions"][0]}\n - *{entry_b["examples"][0]["text"]}*\n'
                    embed.add_field(name=form, value=message)
                except (IndexError, KeyError):
                    pass

            return embed

        await react_menu(self.bot, ctx, len(definition["results"][0]["lexicalEntries"][0]["entries"])-1, _embed_maker)

    @commands.command()
    async def shuffle(self, ctx, *sentence):
        """Shuffles every word in a sentence

        {usage}

        __Examples__
        `{pre}shuffle Fun time` - uFn imet
        """
        new_sentence = []
        for word in sentence:
            new_word = list(word)
            random.shuffle(new_word)
            new_sentence.append("".join(new_word))


        await ctx.send(" ".join(new_sentence))


def setup(bot):
    bot.add_cog(Literature(bot))