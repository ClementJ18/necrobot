#!/usr/bin/python3.6
from discord.ext import commands

from rings.utils.utils import BotError
from rings.utils.converters import MoneyConverter

from collections import deque

from cards import common
from cards.decks import standard52
from cards.decks.standard52 import JACK, QUEEN, KING

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
        
class BlackJack:
    def __init__(self, ctx, bet):
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
        self.is_over = True
        self.msg = None
        self.reaction_list = ["\N{PLAYING CARD BLACK JOKER}","\N{BLACK SQUARE FOR STOP}", "\N{MONEY BAG}"]
        
        self.initial = ":white_check_mark: | Starting a game of Blackjack with **{ctx.author.display_name}** for {bet} :euro: \n :warning: **Wait till all three reactions have been added before choosing** :warning: "
        self.status = "**You** have {player_hand}. Total: {player_total}\n**The Dealer** has {dealer_hand}. Total: {dealer_total}"
        self.info = "**Current bet** - {bet} \nWhat would you like to do? \n :black_joker: - Draw a card \n :stop_button: - Pass your turn \n :moneybag: - Double your bet and draw a card"
        self.actions = deque([], maxlen=5)
    
    @property
    def complete(self):
        actions = "__Status__\n" + "\n".join(self.actions)
        return f"{self.initial}\n{self.status}\n\n{actions}\n\n{self.info}"
        
    def format_message(self):
        return self.complete.format(
            ctx=self.ctx,
            bet=self.bet,
            player_hand=self.player,
            dealer_hand=self.dealer,
            player_total=self.player.value(),
            dealer_total=self.dealer.value()
        )
        
    async def lose(self):
        await self.ctx.bot.db.update_money(self.ctx.author.id, add=-self.bet)
        
    async def win(self):
        await self.ctx.bot.db.update_money(self.ctx.author.id, add=self.bet)

    async def loop(self):
        self.msg = await self.ctx.send(self.format_message())
        for reaction in self.reaction_list:
            await self.msg.add_reaction(reaction)
        while True:
            await self.player_turn()   
            
            if self.player.blackjack():
                break
            
            if self.player.is_bust():
                break
            
            if self.player.passing and self.dealer.is_passing(self.player):
                break
                         
            await self.dealer_turn()
            
            if self.dealer.is_bust():
                break
                
            await self.msg.edit(content=self.format_message())
           
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
            
        self.info = "**GAME FINISHED**"
        await self.msg.edit(content=self.format_message())
        await self.msg.clear_reactions()        
            
    async def dealer_turn(self):
        if self.dealer.is_passing(self.player):
            self.actions.append("**The Dealer** passes his turn")
        else:
            card = self.deck.draw()
            self.dealer.add_card(card)
            self.actions.append(f"**The Dealer** draws {card}")
        
    async def player_turn(self):       
        def check(reaction, user):
            return user == self.ctx.author and str(reaction.emoji) in self.reaction_list and self.msg.id == reaction.message.id
        
        async def clean_up():
            await self.lose()
            await self.msg.clear_reactions()
            
        
        reaction, _ = await self.ctx.bot.wait_for(
            "reaction_add", 
            check=check, 
            timeout=120, 
            handler=clean_up, 
            propagate=True
        )

        if reaction.emoji == '\N{PLAYING CARD BLACK JOKER}':
            card = self.deck.draw()
            self.player.add_card(card)
            self.actions.append(f"**You** draw {card}")
        elif reaction.emoji == "\N{MONEY BAG}":
            try:
                self.bet = await MoneyConverter().convert(self.ctx, str(self.bet*2))
                card = self.deck.draw()
                self.player.add_card(card)
                self.actions.append(f"**You** double your bet and draw {card}")
                self.player.passing = True
            except commands.BadArgument:
                self.actions.append("**You** don't have enough money to double your bet and pass")
        elif reaction.emoji == "\N{BLACK SQUARE FOR STOP}":
            self.actions.append("**You** pass your turn")
            self.player.passing = True
            
        await self.msg.remove_reaction(reaction.emoji, self.ctx.author)
        
class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.IS_GAME = []
        
    #######################################################################
    ## Commands
    #######################################################################
        
    @commands.command(aliases=["bj"])
    async def blackjack(self, ctx, bet : MoneyConverter):
        """A simpe game of black jack against NecroBot's dealer. You can either draw a card by click on :black_joker: 
        or you can pass your turn by clicking on :stop_button: . If you win you get double the amount of money you 
        placed, if you lose you lose it all and if you tie everything is reset. Minimum bet 10 :euro:
         
        {usage}
        
        __Example__
        `{pre}blackjack 200` - bet 200 :euro: in the game of blackjack"""
        if ctx.channel.id in self.IS_GAME:
            raise BotError("There is already a game ongoing")

        if bet < 10:
            raise BotError("Please bet at least 10 necroins.")

        try:
            self.IS_GAME.append(ctx.channel.id)
            bj = BlackJack(ctx, bet)
            await bj.loop()
        except Exception as e:
            raise e
        finally:
            self.IS_GAME.remove(ctx.channel.id)
        
    
async def setup(bot):
    await bot.add_cog(Economy(bot))
