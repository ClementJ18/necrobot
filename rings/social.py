import discord
from discord.ext import commands

from rings.utils.var import tarot_list, lotr_list, dad_joke, dex, riddle_list, got_quotes
from rings.utils.utils import BotError

import random
import asyncio
from bs4 import BeautifulSoup

class Social(commands.Cog):
    """All of NecroBot's fun commands to keep a user active and entertained"""
    def __init__(self, bot):
        self.bot = bot
        
    #######################################################################
    ## Commands
    #######################################################################

    @commands.command(aliases=["sean","joke","dad"])
    async def dadjoke(self, ctx):
        """Send a random dadjoke from a long list. 
        
        {usage}"""
        await ctx.send(f":speaking_head: | {random.choice(dad_joke)}")

    @commands.command()
    async def riddle(self, ctx):
        """Ask a riddle to the user from a long list and waits 30 seconds for the answer. If the 
        user fails to answer they go feed Gollum's fishies. To answer the riddle simply type out 
        the answer, no need to prefix it with anything. 
        
        {usage}"""
        riddle = random.choice(riddle_list)
        await ctx.send(f"Riddle me this {ctx.author.name}: \n{riddle[0]}")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and riddle[1] in m.content.lower()

        async def bad_answer():
            await ctx.send(":negative_squared_cross_mark: | Wrong answer! Now you go to feed the fishies!")
        
        await self.bot.wait_for("message", check=check, timeout=30, propagate=False)
        await ctx.send(":white_check_mark: | Well played, that was the correct answer.")
            

    @commands.command()
    async def tarot(self, ctx):
        """Using the mystical art of tarology, NecroBot reads the user's fate in the card and 
        returns the explanation for each card. Not to be taken seriously. 
        
        {usage}"""
        card_list = random.sample(tarot_list, 3)
        await ctx.send(f":white_flower: | Settle down now and let me see your future my dear {ctx.author.name}...\n**Card #1:** {card_list[0]}\n**Card #2:** {card_list[1]}\n**Card #3:** {card_list[2]}\n__*That is your fate, none can change it for better or worse.*__")

    @commands.command()
    async def rr(self, ctx, bullets : int = 1):
        """Plays a game of russian roulette with the user. If no number of bullets is entered it will default to one. 
        
        {usage}
        
        __Example__
        `{pre}rr 3` - game of russian roulette with 3 bullets
        `{pre}rr` - game of russian roulette with 1 bullet"""
        if bullets not in range(0,7):
            bullets = 1
            
        msg = f":gun: | You insert {bullets} bullets, give the barrel a good spin and put the gun against your temple... \n:persevere: | You take a deep breath... and pull the trigger!"
        if random.randint(1,7) <= bullets:
            msg += "\n:boom: | You weren't so lucky this time. Rest in peace my friend."
        else:
            msg += "\n:ok: | Looks like you'll last the night, hopefully your friends do too."

        await ctx.send(msg)

    @commands.command()
    async def lotrfact(self, ctx):
        """Prints a random Lord of the Rings fact. 
        
        {usage}"""
        choice = random.choice(lotr_list)
        await ctx.send(f"<:onering:351442796420399119> | **Fact #{lotr_list.index(choice) + 1}**: {choice}")

    @commands.command()
    async def pokefusion(self, ctx, pokemon1 = None, pokemon2 = None):
        """Generates a rich embed containing a pokefusion from Gen 1, this can either be a two random pokemons, 
        one random pokemon and one chosen pokemon or two chosen pokemons.
        
        {usage}

        __Examples__
        `{pre}pokefusion` - random pokefusion
        `{pre}pokefusion raichu` - pokefusion of random pokemon and raichu
        `{pre}pokefusion raichu arceus` - pokefusion of raichu and arceus"""
        dex_1 = None
        dex_2 = None

        try:
            dex_1 = dex.index(pokemon1.lower() if pokemon1 else random.choice(dex)) + 1
            dex_2 = dex.index(pokemon2.lower() if pokemon2 else random.choice(dex)) + 1
        except ValueError:
            if dex_1 is None:
                raise BotError("Second pokemon does not exist.")
            
            raise BotError("First pokemon does not exist.")

        async with self.bot.session.get(f"http://pokemon.alexonsager.net/{dex_1}/{dex_2}") as resp:
            soup = BeautifulSoup(await resp.text(), "html.parser")

        image = soup.find(id="pk_img")["src"]
        name = soup.find(id="pk_name").string
        fusion1 = soup.find(id="select1").find(selected="selected").string
        fusion2 = soup.find(id="select2").find(selected="selected").string
        url = soup.find(id="permalink")["value"]
        
        embed = discord.Embed(title=f"<:pokeball:351444031949111297> {name}", colour=discord.Colour(0x277b0), url=url, description=f"{fusion1} + {fusion2}")
        embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))
        embed.set_image(url=image)

        await ctx.send(embed=embed)

    @commands.command()
    async def got(self, ctx, character=None):
        """Posts a random Game of Thrones quote.
    
        {usage}

        __Examples__
        `{pre}got` - posts a random quotes
        `{pre}got Tyrion` - posts a random quote from Tyrion
        """
        if character:
            quotes = [quote for quote in got_quotes if character.lower() in quote["character"].lower()]
            if quotes:
                quote = random.choice(quotes)
            else:
                raise BotError("Didn't find that character")
        else:
            quote = random.choice(got_quotes)

        embed = discord.Embed(title=quote["character"], colour=discord.Colour(0x277b0), description=quote["quote"])
        embed.set_author(name="Game of Thrones Quotes")
        embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Social(bot))
