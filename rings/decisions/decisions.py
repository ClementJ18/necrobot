from __future__ import annotations

import random
from typing import TYPE_CHECKING, List

import dice
import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

from rings.utils.converters import CoinConverter, MoneyConverter
from rings.utils.ui import Paginator
from rings.utils.utils import BotError

from .var import ball8_list

if TYPE_CHECKING:
    from bot import NecroBot


class Decisions(commands.Cog):
    """Helpful commands to help you make decisions"""

    def __init__(self, bot: NecroBot):
        self.bot = bot

    #######################################################################
    ## Commands
    #######################################################################

    async def _choose(self, ctx: commands.Context[NecroBot], choices: str, count: int):
        choice_sets = choices.split("|")
        final_choices = []
        for choice_set in choice_sets:
            choice_list = [x.strip() for x in choice_set.strip().split(",")]
            if len(choice_list) < count:
                raise BotError(f"Less than {count} in choice {' '.join(choices)}")

            final_choices.append(", ".join(random.sample(choice_list, count)))

        await ctx.send(f"I choose **{' '.join(final_choices)}**")

    @commands.group(aliases=["choice"], invoke_without_command=True)
    async def choose(self, ctx: commands.Context[NecroBot], *, choices: str):
        """Returns a single choice from the list of choices given. Use `,` to separate each of the choices. You can \
        make multiple choices with a single command by separating them with `|`.

        {usage}

        __Example__
        `{pre}choose Bob, John Smith, Mary` - choose between the names of Bob, John Smith, and Mary
        `{pre}choice 1, 2` - choose between 1 and 2
        `{pre}choose I | like, hate | tico, kittycat` - can become 'I like tico' or 'I hate tico' or 'I like kittycat'"""
        await self._choose(ctx, choices, 1)

    @choose.command(name="multiple", aliases=["mult"])
    async def choose_mult(self, ctx: commands.Context[NecroBot], count: int, *, choices: str):
        """Similar to the choose command but allows you to specify a number of unique results to return by group.

        {usage}

        __Example__
        `{pre}choose multiple 2 Bob, John, Smith, Mary` -  choose two names of the list of names provided
        `{pre}choose mult 2 Elves, Men, Dwarves | Legolas, Gimli, Aragorn` - return two results from each group
        """
        await self._choose(ctx, choices, count)

    @commands.command(aliases=["flip"])
    @commands.cooldown(3, 5, BucketType.user)
    async def coin(
        self,
        ctx: commands.Context[NecroBot],
        choice: CoinConverter = None,
        bet: MoneyConverter = 0,
    ):
        """Flips a coin and returns the result. Can also be used to bet money on the result (`h` for head and \
        `t` for tail). The bet return is 50% of your initial bet.

        {usage}

        __Example__
        `{pre}coin` - flips a coin
        `{pre}coin h 50` - bet 50 coins on the result being head"""
        options = {
            "h": "<:head:351456287453872135> | **Head**",
            "t": "<:tail:351456234257514496> | **Tail**",
        }

        outcome = random.choice(list(options.keys()))
        msg = options[outcome]
        if bet > 0:
            if choice == outcome:
                msg += "\nWell done!"
            else:
                msg += "\nBetter luck next time."
                bet = -bet

            await self.bot.db.update_money(ctx.author.id, add=bet // 2)

        await ctx.send(msg)

    @commands.command(aliases=["dice"])
    async def roll(self, ctx: commands.Context[NecroBot], dices: str = "1d6"):
        """Rolls one or multiple x sided dices and returns the result. \
        Structure of the argument: `[number of die]d[number of faces]`.

        {usage}

        __Example__
        `{pre}roll 3d8` - roll three 8-sided die
        `{pre}roll` - roll one 6-sided die"""
        try:
            dice_list = dice.roll(dices)
        except Exception as e:
            raise BotError(e) from e

        if isinstance(dice_list, int):
            total = dice_list
            dice_list = []
        else:
            total = sum(dice_list)

        chunk_size = 1800
        chunks = []
        current_chunk = []
        current_length = 0
        for roll in dice_list:
            roll_lenght = len(str(roll)) + 2
            if roll_lenght + current_length > chunk_size:
                chunks.append(current_chunk)
                current_chunk = []
                current_length = 0

            current_chunk.append(str(roll))
            current_length += roll_lenght

        chunks.append(current_chunk)

        def content_maker(view: Paginator, entry: List[str]):
            dice_string = None
            if entry:
                dice_string = ", ".join(entry)

            if view.max_index > 0 and view.index < view.max_index:
                dice_string = dice_string + "..."

            if view.index > 0:
                dice_string = "..." + dice_string

            page_string = f" **({view.page_string})** "
            string = f":game_die: | **{ctx.author.display_name}** rolled **{dices}** for a total of **{total}**."

            if dice_string is None:
                return string
    
            return f"{string} The dice were{page_string if view.max_index > 0 else ''}: {dice_string}"

        await Paginator(1, chunks, ctx.author, content_maker=content_maker).start(ctx)

    @commands.command(name="8ball")
    async def ball8(self, ctx: commands.Context[NecroBot], *, message: str = None):
        """Uses an 8ball system to reply to the user's question.

        {usage}"""
        msg = f":8ball: | {random.choice(ball8_list)}"
        if message is not None:
            msg = f"{message} \n" + msg

        await ctx.send(msg)
