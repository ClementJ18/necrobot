from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from discord.interactions import Interaction

from cards import common
from cards.decks import standard52
from cards.decks.standard52 import JACK, KING, QUEEN
from rings.utils.converters import MoneyConverter
from rings.utils.ui import BaseView
from rings.utils.utils import NEGATIVE_CHECK, BotError

if TYPE_CHECKING:
    from bot import NecroBot

ACE_LOW = 1
ACE_HIGH = 11
JACK_VALUE = 10

WIN_MIN = 17
WIN_MAX = 21


class GameEnd(Exception):
    pass


class Card(standard52.Card):
    def value(self):
        if self.rank in (JACK, QUEEN, KING):
            return JACK_VALUE

        return self.rank


class Deck(standard52.Deck):
    def create_card(self, suit, rank):
        return Card(suit, rank)


class Hand(common.Hand):
    def __init__(self):
        super().__init__()
        self.busted = False
        self.passing = False

    def add_card(self, card):
        super().add_card(card)
        self.busted = self.is_bust()

    def value(self):
        total = 0
        aces = 0
        for card in self.cards:
            if card.is_ace():
                aces += 1
            else:
                total += card.value()
        for _ in range(aces):
            if total + ACE_HIGH <= WIN_MAX:
                total += ACE_HIGH
            else:
                total += ACE_LOW
        return total

    def is_bust(self):
        return self.value() > WIN_MAX

    def is_passing(self, other):
        if self.value() < WIN_MIN:
            return False

        if self.value() >= other.value():
            return True

        return not self.busted and self.value() >= other.value()

    def blackjack(self):
        return self.value() == 21

    def beats(self, other):
        if not self.busted and other.busted:
            return True
        if self.busted:
            return False
        if self.value() == WIN_MAX:
            return True
        return self.value() > other.value()


class BlackJack(BaseView):
    def __init__(self, ctx: commands.Context[NecroBot], bet, *, timeout=180):
        super().__init__(timeout=timeout)

        self.deck = Deck()
        self.deck.shuffle()

        self.bet = bet

        self.player = Hand()
        self.dealer = Hand()

        self.player.add_card(self.deck.draw())
        self.dealer.add_card(self.deck.draw())

        self.player.add_card(self.deck.draw())
        self.dealer.add_card(self.deck.draw())

        self.ctx = ctx
        self.status = "Ongoing"
        self.actions = ["Game started"]
        self.index = 0
        self.message: discord.Message = None

        self.author = ctx.author

    @property
    def max_index(self):
        return max(1, (len(self.actions) // 5))

    def format_message(self):
        embed = discord.Embed(
            title="Blackjack",
            description=f"Player: {self.ctx.author.mention}\nBet: **{self.bet}**\nStatus: {self.status}\n\nYour hand: {self.player} (**{self.player.value()}**)\nDealer's Hand: {self.dealer} (**{self.dealer.value()}**)",
            colour=self.ctx.bot.bot_color,
        )
        embed.set_footer(**self.ctx.bot.bot_footer)
        embed.add_field(
            name=f"Actions ({self.index + 1} / {self.max_index + 1})",
            value="\n".join(self.actions[self.index * 5 : (self.index + 1) * 5]),
            inline=False,
        )

        return embed

    @discord.ui.button(label="Pass", style=discord.ButtonStyle.primary, row=1)
    async def pass_turn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.actions.append("**You** pass your turn")
        self.player.passing = True

        await self.process_turn()

        await interaction.response.edit_message(embed=self.format_message(), view=self)

    @discord.ui.button(label="Draw", style=discord.ButtonStyle.primary, row=1)
    async def draw_card(self, interaction: discord.Interaction, button: discord.ui.Button):
        card = self.deck.draw()
        self.player.add_card(card)
        self.actions.append(f"**You** draw {card}")

        await self.process_turn()

        await interaction.response.edit_message(embed=self.format_message(), view=self)

    @discord.ui.button(label="Double Down and Draw", style=discord.ButtonStyle.secondary, row=2)
    async def double_down(self, interaction: discord.Interaction, button: discord.ui.Button):

        try:
            self.bet = await MoneyConverter().convert(self.ctx, str(self.bet * 2))
            card = self.deck.draw()
            self.player.add_card(card)
            self.actions.append(f"**You** double your bet and draw {card}")
            self.player.passing = True
        except commands.BadArgument:
            return await interaction.response.send_message(
                f"{NEGATIVE_CHECK} | Not enough money to double down",
                ephemeral=True,
            )

        await self.process_turn()

        await interaction.response.edit_message(embed=self.format_message(), view=self)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, row=3)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index - 1 < 0:
            self.index = self.max_index
        else:
            self.index -= 1

        await interaction.response.edit_message(embed=self.format_message(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, row=3)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index + 1 >= self.max_index:
            self.index = 0
        else:
            self.index += 1

        await interaction.response.edit_message(embed=self.format_message(), view=self)

    async def lose(self):
        await self.ctx.bot.db.update_money(self.ctx.author.id, add=-self.bet)

    async def win(self):
        await self.ctx.bot.db.update_money(self.ctx.author.id, add=self.bet)

    def stop_game(self):
        return (
            self.player.blackjack()
            or self.player.is_bust()
            or self.dealer.is_bust()
            or (self.player.passing and self.dealer.is_passing(self.player))
        )

    async def process_turn(self):
        if not self.stop_game():
            await self.dealer_turn()

        if not self.stop_game():
            return

        if self.player.blackjack() and not self.dealer.blackjack():
            self.actions.append("**BLACKJACK!**")
            await self.win()
        elif self.player.beats(self.dealer):
            self.actions.append(f"**Your** hand beats **the Dealer's** hand. Won {self.bet}")
            await self.win()
        elif self.dealer.beats(self.player):
            self.actions.append(f"**The Dealer's** hand beats **your** hand. Lost {self.bet}")
            await self.lose()
        else:
            self.actions.append("Tie, everything is reset")

        self.status = "**GAME FINISHED**"
        self.remove_item(self.pass_turn)
        self.remove_item(self.draw_card)
        self.remove_item(self.double_down)

    async def on_timeout(self):
        if self.status != "**GAME FINISHED**":
            self.status = "**GAME ABANDONNED**"
            self.remove_item(self.pass_turn)
            self.remove_item(self.draw_card)
            self.remove_item(self.double_down)
            self.actions.append("**You** timed out")
            await self.lose()

            await self.message.edit(embed=self.format_message(), view=self)

    async def dealer_turn(self):
        if self.dealer.is_passing(self.player):
            self.actions.append("**The Dealer** passes his turn")
        else:
            card = self.deck.draw()
            self.dealer.add_card(card)
            self.actions.append(f"**The Dealer** draws {card}")


class Economy(commands.Cog):
    """Commands that allow you pay a certain amount of money for a chance to increase your balance."""
    def __init__(self, bot: NecroBot):
        self.bot = bot
        self.IS_GAME = []

    #######################################################################
    ## Commands
    #######################################################################

    @commands.command(aliases=["bj"])
    async def blackjack(self, ctx: commands.Context[NecroBot], bet: MoneyConverter):
        """A simpe game of black jack against NecroBot's dealer. You can either draw a card by click on :black_joker: \
        or you can pass your turn by clicking on :stop_button: . If you win you get double the amount of money you \
        placed, if you lose you lose it all and if you tie everything is reset. Minimum bet 10 :euro:

        {usage}

        __Example__
        `{pre}blackjack 200` - bet 200 :euro: in the game of blackjack"""
        if bet < 10:
            raise BotError("Please bet at least 10 necroins.")

        bj = BlackJack(ctx, bet)
        bj.message = await ctx.send(embed=bj.format_message(), view=bj)
        await bj.wait()


async def setup(bot: NecroBot):
    await bot.add_cog(Economy(bot))
