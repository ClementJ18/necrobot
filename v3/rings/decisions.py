from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

from rings.utils.utils import MoneyConverter
from rings.utils.var import ball8_list

import dice
import random

class CoinConverter(commands.Converter):
    async def convert(self, ctx, argument):
        if argument.lower() in ["h", "head"]:
            return "h"
        if argument.lower() in ["t", "tail"]:
            return "t"

        raise commands.BadArgument("Choices must be one of: `t`, `tail`, `h` or `head`")

class Decisions(commands.Cog):
    """Helpful commands to help you make decisions"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def choose(self, ctx, *, choices):
        """Returns a single choice from the list of choices given. Use `,` to seperate each of the choices.
        
        {usage}
        
        __Example__
        `{pre}choose Bob, John Smith, Mary` - choose between the names of Bob, John Smith, and Mary
        `{pre}choose 1, 2` - choose between 1 and 2 """
        choice_list = [x.strip() for x in choices.split(",")]
        await ctx.send(f"I choose **{random.choice(choice_list)}**")

    @commands.command(aliases=["flip"])
    @commands.cooldown(3, 5, BucketType.user)
    async def coin(self, ctx, choice : CoinConverter = None, bet : MoneyConverter = 0):
        """Flips a coin and returns the result. Can also be used to bet money on the result (`h` for head and `t` for tail).
        
        {usage}

        __Example__
        `{pre}coin` - flips a coin
        `{pre}coin h 50` - bet 50 coins on the result being head"""
        options = {"h": "<:head:351456287453872135> | **Head**", "t": "<:tail:351456234257514496> | **Tail**"}
        
        outcome = random.choice(list(options.keys()))
        msg = options[outcome]
        if bet > 0:
            if choice == outcome:
                msg += "\nWell done!"
            else:
                msg += "\nBetter luck next time."
                bet = -bet
                
            await self.bot.db.update_money(ctx.author.id, add=bet)

        await ctx.send(msg)

    @commands.command()
    async def roll(self, ctx, dices="1d6"):
        """Rolls one or multiple x sided dices and returns the result. 
        Structure of the argument: `[number of die]d[number of faces]`. 
        
        {usage}
        
        __Example__
        `{pre}roll 3d8` - roll three 8-sided die
        `{pre}roll` - roll one 6-sided die"""
        dice_list = dice.roll(dices)
        try:
            t = sum(dice_list)
        except TypeError:
            t = dice_list

        await ctx.send(f":game_die: | **{ctx.author.display_name}** rolled {dice_list} for a total of: **{t}**")

    @commands.command(name="8ball")
    async def ball8(self, ctx, *, message):
        """Uses an 8ball system to reply to the user's question. 
        
        {usage}"""
        await ctx.send(f"{message} \n:8ball: | {random.choice(ball8_list)}")

def setup(bot):
    bot.add_cog(Decisions(bot))
