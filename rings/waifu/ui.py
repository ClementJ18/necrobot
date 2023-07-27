from __future__ import annotations

import asyncio
import enum
import time
from dataclasses import dataclass
from typing import List

import discord
from discord.ext import commands
from discord.interactions import Interaction

from rings.utils.ui import (
    BaseView,
    EmbedBooleanConverter,
    EmbedDefaultConverter,
    EmbedIntegerConverter,
)

from .base import Stat, get_symbol
from .battle import Battle, BattleOverException, MovementType
from .entities import Character
from .skills import ActiveSkill, PassiveSkill, get_skill


class EmbedStatConverter(EmbedDefaultConverter):
    def convert(self, argument: str):
        percent, value = argument.split(",")
        value = EmbedIntegerConverter().convert(value.strip())
        percent = EmbedBooleanConverter().convert(percent.strip())

        return Stat(percent, value)


@dataclass
class EmbedSkillConverter(EmbedDefaultConverter):
    passive: bool = False

    def convert(self, argument: str):
        skill = get_skill(argument.strip())
        if skill is None:
            raise commands.BadArgument("Not a valid skill")

        if isinstance(skill, PassiveSkill) and not self.passive:
            raise commands.BadArgument("Not a valid active skill")

        if isinstance(skill, ActiveSkill) and self.passive:
            raise commands.BadArgument("Not a valid passive skill")

        return argument


class ActionType(enum.Enum):
    move = 0
    attack = 1
    skill = 2


class AttackOrder(discord.ui.Select):
    view: CombatView

    def __init__(self, battle: Battle, character: Character):
        self.character = character
        self.battle = battle
        disabled = False

        adjacents = battle.get_adjacent_positions(character.position)
        options = [
            discord.SelectOption(
                label=e.name,
                value=index,
                description=f"Attack {e.name}",
                emoji=get_symbol(e.index),
            )
            for index, e in enumerate(battle.enemies)
            if e.position in adjacents.values() and not character.has_attacked
        ]

        if not options:
            options = [
                discord.SelectOption(
                    label="No targets",
                    value=0,
                    description="No nearby enemies to attack",
                )
            ]
            disabled = True

        super().__init__(
            options=options,
            row=3,
            placeholder="Pick which enemy to attack with your weapon",
            disabled=disabled,
        )

    async def callback(self, interaction: discord.Interaction):
        await self.view.take_action(
            interaction,
            ActionType.attack,
            character=self.character,
            target=self.battle.enemies[int(self.values[0])],
        )


class ActionButton(discord.ui.Button):
    view: CombatView

    def __init__(self, *, character: Character, action: ActionType, arguments: dict, **kwargs):
        self.character = character
        self.action = action
        self.arguments = arguments

        super().__init__(**kwargs)

    async def callback(self, interaction: Interaction):
        await self.view.take_action(
            interaction, self.action, character=self.character, **self.arguments
        )


class CharacterUI(discord.ui.Select):
    view: CombatView

    def __init__(self, characters: List[Character], battle: Battle, embed_maker):
        self.characters = characters
        self.battle = battle
        self.embed_maker = embed_maker

        options = [
            discord.SelectOption(
                label=character.name, value=character.index, emoji=get_symbol(character.index)
            )
            for character in characters
        ]

        super().__init__(options=options, row=1, placeholder="Pick which character to use")

    def generate_buttons(self, character: Character):
        buttons = [
            ActionButton(
                style=discord.ButtonStyle.primary,
                label=move.name.title(),
                disabled=not self.battle.is_valid_movement(
                    character.position, move.value, character.current_movement_range
                ),
                row=2,
                character=character,
                action=ActionType.move,
                arguments={"direction": move},
            )
            for move in MovementType
        ]

        buttons += [
            AttackOrder(self.battle, character),
            ActionButton(
                style=discord.ButtonStyle.red
                if character.skill_is_active()
                else discord.ButtonStyle.secondary,
                label="Activate Skill"
                if character.active_skill is None
                else character.active_skill.name
                + (
                    f" ({character.active_skill.current_cooldown})"
                    if character.active_skill.current_cooldown > 0
                    else ""
                ),
                row=2,
                character=character,
                action=ActionType.skill,
                disabled=not character.can_use_skill(),
                arguments={},
            ),
        ]

        return buttons

    async def callback(self, interaction: discord.Interaction):
        character = self.characters[int(self.values[0])]
        self.view.clear_items()
        for option in self.options:
            option.default = str(self.values[0]) == str(option.value)

        self.view.add_item(self)
        for button in self.generate_buttons(character):
            self.view.add_item(button)

        self.view.add_item(self.view.end_turn)
        self.view.add_item(self.view.previous_page)
        self.view.add_item(self.view.next_page)
        await interaction.response.edit_message(
            view=self.view,
            embed=self.embed_maker(self.battle, character_range=character, page=self.view.index),
        )

    def update_buttons(self, character: Character):
        for child in self.view.children:
            if isinstance(child, (ActionButton, AttackOrder)):
                self.view.remove_item(child)

        for button in self.generate_buttons(character):
            self.view.add_item(button)


class CombatView(BaseView):
    def __init__(self, battle: Battle, embed_maker, author: discord.Member):
        super().__init__()

        self.battle = battle
        self.set_ui(CharacterUI(battle.players, battle, embed_maker))
        self.message: discord.Message = None
        self.embed_maker = embed_maker
        self.author = author
        self.victory = False
        self.index = 0

    def set_ui(self, ui: CharacterUI):
        self.ui = ui
        self.add_item(ui)

    def reset_view(self):
        self.clear_items()
        self.set_ui(CharacterUI(self.battle.players, self.battle, self.embed_maker))
        self.add_item(self.end_turn)
        self.add_item(self.previous_page)
        self.add_item(self.next_page)

    def update_view(self, character: Character):
        self.ui.update_buttons(character)

    async def take_action(self, interaction: discord.Interaction, action: ActionType, **kwargs):
        character: Character = kwargs.get("character")

        if action == ActionType.move:
            self.battle.move_entity(character, change=kwargs.get("direction").value)
        elif action == ActionType.attack:
            self.battle.attack_entity(character, kwargs.get("target"))
            character.current_movement_range = 0
        elif action == ActionType.skill:
            self.battle.use_active_skill(character)
            character.current_movement_range = 0

        self.update_view(character)
        await interaction.response.edit_message(
            embed=self.embed_maker(self.battle, character_range=character, page=self.index),
            view=self,
        )

        self.battle.battlefield.check_victory(self.battle)

    @discord.ui.button(label="End Turn", style=discord.ButtonStyle.red, row=0)
    async def end_turn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = 0
        await interaction.response.defer()
        self.clear_items()

        for enemy in self.battle.enemies:
            start = time.time()
            self.battle.pick_ai_action(enemy)
            end = time.time() - start

            await interaction.followup.edit_message(
                self.message.id, embed=self.embed_maker(self.battle), view=self
            )
            await asyncio.sleep(3 - end)

        self.battle.end_turn()

        self.battle.battlefield.check_victory(self.battle)

        self.battle.start_turn()
        self.reset_view()
        await interaction.followup.edit_message(
            self.message.id, embed=self.embed_maker(self.battle), view=self
        )

    @discord.ui.button(label="<")
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index -= 1
        if self.index < 0:
            self.index = len(self.battle.players)

        character = None
        if self.ui.values:
            character = self.battle.players[int(self.ui.values[0])]

        await interaction.response.edit_message(
            embed=self.embed_maker(self.battle, page=self.index, character_range=character)
        )

    @discord.ui.button(label=">")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index += 1
        if self.index > len(self.battle.players):
            self.index = 0

        character = None
        if self.ui.values:
            character = self.battle.players[int(self.ui.values[0])]

        await interaction.response.edit_message(
            embed=self.embed_maker(self.battle, page=self.index, character_range=character)
        )

    async def on_error(self, interaction: discord.Interaction, error, item):
        if isinstance(error, BattleOverException):
            self.victory = error.victory
            self.stop()
            self.clear_items()
        else:
            await super().on_error(interaction, error, item)
