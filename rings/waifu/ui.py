import asyncio
import enum
import time
from typing import List

import discord
from discord.interactions import Interaction

from rings.utils.ui import EmbedBooleanConverter, EmbedDefaultConverter, EmbedIntegerConverter

from .base import get_symbol
from .battle import Battle, Character, MovementType
from .entities import Stat


class EmbedStatConverter(EmbedDefaultConverter):
    def convert(self, argument):
        percent, value = argument.split(",")
        value = EmbedIntegerConverter().convert(value.strip())
        percent = EmbedBooleanConverter().convert(percent.strip())

        return Stat(percent, value)


class ActionType(enum.Enum):
    move = 0
    attack = 1
    skill = 2


class AttackOrder(discord.ui.Select):
    def __init__(self, battle: Battle, character: Character):
        self.character = character
        self.battle = battle

        adjacents = battle.get_adjacent_positions(character.position)
        options = [
            discord.SelectOption(
                label=e.name,
                value=index,
                description=f"Attack {e.name}",
                emoji=get_symbol(index + len(battle.players)),
            )
            for index, e in enumerate(battle.enemies)
            if e.position in adjacents.values()
        ]

        super().__init__(
            options=options, row=2, placeholder="Pick which enemy to attack with your weapon"
        )

    async def callback(self, interaction: discord.Interaction):
        await self.view.take_action(
            interaction,
            ActionType.attack,
            character=self.character,
            target=self.battle.enemies[int(self.values[0])],
        )


class ActionButton(discord.ui.Button):
    def __init__(self, *, character: Character, action: ActionType, arguments, **kwargs):
        self.character = character
        self.action = action
        self.arguments = arguments

        super().__init__(**kwargs)

    async def callback(self, interaction: Interaction):
        await self.view.take_action(
            interaction, self.action, character=self.character, **self.arguments
        )


class CharacterUI(discord.ui.Select):
    def __init__(self, characters: List[Character], battle: Battle, embed_maker):
        self.characters = characters
        self.battle = battle
        self.embed_maker = embed_maker

        options = [
            discord.SelectOption(label=character.name, value=index, emoji=get_symbol(index))
            for index, character in enumerate(characters)
        ]

        super().__init__(options=options, row=0, placeholder="Pick which character to use")

    def generate_buttons(self, character: Character):
        buttons = [
            ActionButton(
                style=discord.ButtonStyle.primary,
                label=move.name.title(),
                disabled=not self.battle.is_valid_movement(
                    character.position, move.value, character.current_movement_range
                ),
                row=1,
                character=character,
                action=ActionType.move,
                arguments={"direction": move},
            )
            for move in MovementType
        ]

        attack_order = AttackOrder(self.battle, character)
        if attack_order.options:
            buttons.append(attack_order)

        if character.active_skill is not None:
            buttons.append(
                ActionButton(
                    style=discord.ButtonStyle.secondary,
                    label="Activate Skill",
                    row=2,
                    character=character,
                    action=ActionType.skill,
                )
            )

        return buttons

    async def callback(self, interaction: discord.Interaction):
        character = self.characters[int(self.values[0])]
        self.view.clear_items()
        for option in self.options:
            option.default = int(self.values[0]) == option.value

        self.view.add_item(self)
        for button in self.generate_buttons(character):
            self.view.add_item(button)

        self.view.add_item(self.view.end_turn)
        await interaction.response.edit_message(
            view=self.view, embed=self.embed_maker(self.battle, character)
        )


class CombatView(discord.ui.View):
    def __init__(self, battle: Battle, embed_maker, author: discord.Member):
        super().__init__()

        self.battle = battle
        self.add_item(CharacterUI(battle.players, battle, embed_maker))
        self.message: discord.Message = None
        self.embed_maker = embed_maker
        self.author = author
        self.victory = False

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.author.id

    async def on_timeout(self):
        self.stop()
        self.clear_items()
        await self.message.edit(view=self)

    def reset_view(self):
        self.clear_items()
        self.add_item(CharacterUI(self.battle.players, self.battle, self.embed_maker))
        self.add_item(self.end_turn)

    async def take_action(self, interaction: discord.Interaction, action: ActionType, **kwargs):
        if action == ActionType.move:
            self.battle.move_character(
                kwargs.get("character"), change=kwargs.get("direction").value
            )
        elif action == ActionType.attack:
            character: Character = kwargs.get("character")
            self.battle.attack_character(character, kwargs.get("target"))
            character.current_movement_range = 0
        elif action == ActionType.skill:
            self.battle.use_active_skill(kwargs.get("character"))

        self.reset_view()
        await interaction.response.edit_message(embed=self.embed_maker(self.battle), view=self)

    @discord.ui.button(label="End Turn", style=discord.ButtonStyle.red, row=4)
    async def end_turn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.clear_items()

        for enemy in self.battle.enemies:
            start = time.time()
            self.battle.pick_ai_action(enemy)
            end = time.time() - start

            await interaction.followup.edit_message(
                self.message.id, embed=self.embed_maker(self.battle), view=self
            )
            await asyncio.sleep(5 - end)

        self.battle.end_turn()
        self.reset_view()
        await interaction.followup.edit_message(
            self.message.id, embed=self.embed_maker(self.battle), view=self
        )
