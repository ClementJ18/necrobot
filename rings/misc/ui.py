from __future__ import annotations

import random
import traceback
from typing import TYPE_CHECKING, List

import discord

from rings.utils.ui import BaseView

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

        embed = discord.Embed(
            title=f"Hunger Games Simulator ({self.index + 1}/{self.max_index + 1})",
            colour=self.bot.bot_color,
            description=f"{' - '.join(self.tributes)}\nPress :arrow_forward: to proceed",
        )

        embed.set_footer(**self.bot.bot_footer)

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

        embed.add_field(
            name=f"{event_name.title()} {self.day}",
            value="\n".join(done_events),
            inline=False,
        )

        if event_name == "night":
            self.day += 1

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
