from __future__ import annotations

import random
import traceback
from typing import TYPE_CHECKING, List

import discord

from rings.utils.ui import BaseView
from rings.utils.utils import NEGATIVE_CHECK, POSITIVE_CHECK

from .hunger_game import events

if TYPE_CHECKING:
    from bot import NecroBot


class FightError(Exception):
    def __init__(self, message: str, event=None, format_dict=None):
        super().__init__(message)

        self.message = message
        self.event = event
        self.format_dict = format_dict

    def embed(self, bot: NecroBot):
        error_traceback = f"```py\n{traceback.format_exc()}\n```"
        embed = discord.Embed(title="Fight Error", description=error_traceback, colour=bot.bot_color)
        embed.add_field(name="Error String", value=self.event["string"], inline=False)
        embed.add_field(name="Error Tribute Number", value=self.event["tributes"], inline=False)
        embed.add_field(name="Error Tribute Killed", value=self.event["killed"], inline=False)
        embed.add_field(name="Error Tributes", value=str(self.format_dict), inline=False)
        embed.set_footer(**bot.bot_footer)

        return embed


class HungerGames(BaseView):
    def __init__(self, bot: NecroBot, tributes, author: discord.User, *, timeout: int = 180):
        super().__init__(timeout=timeout)

        self.tributes = tributes
        self.day: int = 1
        self.dead: List[str] = []
        self.phases: List[str] = []
        self.index: int = 0
        self.ongoing: bool = True
        self.phase: str = None
        self.bot = bot
        self.author = author
        self.message: discord.Message = None

    @property
    def max_index(self):
        return len(self.phases)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.blurple)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index - 1 < 0:
            self.index = self.max_index - 1
        else:
            self.index -= 1

        await interaction.response.edit_message(embed=self.phases[self.index], view=self)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.grey)
    async def stop_fight(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.ongoing = False
        self.remove_item(self.stop_fight)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index + 1 >= self.max_index:
            if not self.ongoing:
                self.index = 0
            else:
                self.index += 1
                self.prepare_next_phase(self.get_next_phase())

        else:
            self.index += 1

        await interaction.response.edit_message(embed=self.phases[self.index], view=self)

    async def on_timeout(self):
        self.stop()
        self.clear_items()
        await self.message.edit(view=self)

    def prepare_next_phase(self, event_name):
        if event_name == "dead":
            return self.process_deads()

        if event_name == "victory":
            return self.process_victory()

        idle_tributes = self.tributes.copy()

        deathless = [event for event in events[event_name] if len(event["killed"]) < 1]
        idle_events = events[event_name].copy() + deathless.copy()

        done_events = []
        while idle_tributes and len(self.tributes) > 1:
            tributes = []
            event = random.choice(
                [
                    event
                    for event in idle_events
                    if event["tributes"] <= len(idle_tributes) and len(event["killed"]) < len(self.tributes)
                ]
            )
            tributes = random.sample(idle_tributes, event["tributes"])
            idle_tributes = [x for x in idle_tributes if x not in tributes]
            if event["killed"]:
                for killed in event["killed"]:
                    tribute = tributes[int(killed) - 1]
                    self.tributes.remove(tribute)
                    self.dead.append(tribute)

            format_dict = {}
            for tribute in tributes:
                format_dict["p" + str(tributes.index(tribute) + 1)] = tribute

            try:
                done_events.append(event["string"].format(**format_dict))
            except Exception as e:
                raise FightError("Error formatting event", event, format_dict) from e

        if event_name == "night":
            self.day += 1

        formatted_done_events = "\n".join(done_events)
        embed = discord.Embed(
            title=f"Hunger Games Simulator ({self.index + 1}/{self.max_index + 1})",
            colour=self.bot.bot_color,
            description=f"{event_name.title()} {self.day}\n {formatted_done_events}",
        )

        embed.add_field(
            name="Tributes",
            value=f"{' - '.join(self.tributes)}\nPress :arrow_forward: to proceed"
        )

        embed.set_footer(**self.bot.bot_footer)

        self.phases.append(embed)
        return embed

    def process_deads(self):
        embed = discord.Embed(
            title=f"Dead Tributes ({self.index + 1}/{self.max_index + 1})",
            description="- " + "\n- ".join(self.dead) if self.dead else "None",
            colour=self.bot.bot_color,
        )
        embed.set_footer(**self.bot.bot_footer)
        self.dead = []

        self.phases.append(embed)
        return embed

    def process_victory(self):
        self.ongoing = False
        embed = discord.Embed(
            title=f"Hunger Game Winner ({self.index + 1}/{self.max_index + 1})",
            description=f":tada: {self.tributes[0]} is the Winner! :tada:",
            colour=self.bot.bot_color,
        )
        embed.set_footer(**self.bot.bot_footer)

        self.remove_item(self.stop_fight)
        self.phases.append(embed)
        return embed

    def get_next_phase(self):
        if self.phase is None:
            self.phase = "bloodbath"
            return self.phase

        if len(self.tributes) > 1:
            if self.day % 7 == 0:
                self.phase = "feast"
                return self.phase

            if self.phase in ["night", "feast", "bloodbath"]:
                self.phase = "day"
                return self.phase

            if self.phase in ["day"]:
                self.phase = "dead"
                return self.phase

            if self.phase == "dead":
                self.phase = "night"
                return self.phase

        self.phase = "victory"
        return self.phase


class MatchupView(BaseView):
    faction_options = {
        "Gondor": {"message": "The crownless again shall be king.", "emoji": "Gondor:966448210686132294"},
        "Rohan": {"message": "Where now are the horse and the rider?", "emoji": "Rohan:840220156772745256"},
        "Isengard": {"message": "TO WAR!", "emoji": "Isengard:840220156340469771"},
        "Mordor": {"message": "One Ring to rule them all.", "emoji": "Mordor:840220156784934912"},
        "Ered Luin": {
            "message": "And he never forgot, and he never forgave.",
            "emoji": "EredLuin:840220156655304714",
        },
        "Angmar": {"message": "A chill wind blows...", "emoji": "Angmar:840220154708099124"},
        "Erebor": {"message": "It was the city of Dale!", "emoji": "Erebor:966446268157157466"},
        "Iron Hills": {
            "message": "Would you consider... JUST SODDING OFF!",
            "emoji": "IronHills:840220159507169300",
        },
        "Lothlorien": {
            "message": "Caras Galadhon… the heart of Elvendom on earth.",
            "emoji": "Lothlorien:840220156726476810",
        },
        "Imladris": {"message": "Welcome to the last Homely House.", "emoji": "Imladris:840220156738273300"},
        "Misty Mountains": {"message": "I feel a song rising.", "emoji": "Gobbos:840224017398497311"},
    }

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        options=[
            discord.SelectOption(
                label=name, value=name, emoji=discord.PartialEmoji.from_str(faction["emoji"])
            )
            for name, faction in faction_options.items()
        ],
        placeholder="Select the faction that won",
        custom_id="matchup_winner",
        row=0,
    )
    async def winner_select(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

    @discord.ui.select(
        options=[
            discord.SelectOption(
                label=name, value=name, emoji=discord.PartialEmoji.from_str(faction["emoji"])
            )
            for name, faction in faction_options.items()
        ],
        placeholder="Select the faction that lost",
        custom_id="matchup_loser",
        row=1,
    )
    async def loser_select(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

    @discord.ui.button(label="Confirm", custom_id="matchup_confirm", row=2, style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction[NecroBot], button: discord.ui.Button):
        if not (self.winner_select.values and self.loser_select.values):
            return await interaction.response.send_message(
                f"{NEGATIVE_CHECK} | Please select a winning and losing faction", ephemeral=True
            )

        if self.winner_select.values[0] == self.loser_select.values[0]:
            return await interaction.response.send_message(
                f"{NEGATIVE_CHECK} | Please select different winning and losing factions",
                ephemeral=True,
            )

        await interaction.client.db.query(
            "UPDATE necrobot.InternalRanked SET victories = victories + 1 WHERE faction = $1 AND enemy = $2",
            self.winner_select.values[0],
            self.loser_select.values[0],
        )

        await interaction.client.db.query(
            "UPDATE necrobot.InternalRanked SET defeats = defeats + 1 WHERE faction = $1 AND enemy = $2",
            self.loser_select.values[0],
            self.winner_select.values[0],
        )

        await interaction.client.db.query(
            "INSERT INTO necrobot.InternalRankedLogs(user_id, faction, enemy, faction_won) VALUES ($1, $2, $3, $4)",
            interaction.user.id,
            self.winner_select.values[0],
            self.loser_select.values[0],
            True,
        )

        await interaction.response.edit_message()
        await interaction.followup.send(
            f"{POSITIVE_CHECK} | Registered a victory for **{self.winner_select.values[0]}** over **{self.loser_select.values[0]}**",
            ephemeral=True,
        )
