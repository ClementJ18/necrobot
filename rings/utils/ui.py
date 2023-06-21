import asyncio
import random
import traceback
from typing import Callable, Dict, Iterable, List

import discord

from rings.utils.hunger_game import events
from rings.utils.utils import BotError


class TextInput(discord.ui.TextInput):
    async def callback(self, interaction):
        self.view.stop()
        self.view.clear_items()

        if self.value.lower() == self.view.answer:
            self.view.value = True
            await interaction.response.edit_message(
                content=":white_check_mark: | Correct! Guess you get to live.",
                view=self.view,
            )
        else:
            self.view.value = True
            await interaction.response.edit_message(
                content=":negative_squared_cross_mark: | Wrong answer! Now you go to feed the fishies!",
                view=self.view,
            )


class RiddleView(discord.ui.View):
    def __init__(self, answer, *, timeout=180):
        self.answer = answer.lower()
        super().__init__(timeout=timeout)
        self.add_item(TextInput(style=discord.TextStyle.short, required=True, label="Answer:"))

    async def on_timeout(self):
        self.stop()
        self.clear_items()
        await self.message.edit(
            content=":negative_squared_cross_mark: | Too slow! Now you go to feed the fishies!",
            view=self,
        )


class Select(discord.ui.Select):
    async def callback(self, interaction):
        self.view.value = True
        self.view.stop()
        self.view.clear_items()
        await interaction.response.edit_message(
            content=f":white_check_mark: | Choice was **{self.values[0]}**",
            view=self.view,
        )


class SelectView(discord.ui.View):
    def __init__(
        self,
        options,
        *,
        min_values=1,
        max_values=1,
        placeholder="Select...",
        timeout=180,
    ):
        self.options = [discord.SelectOption(label=x) for x in options]
        self.value = False
        self.select = Select(
            min_values=min_values,
            max_values=max_values,
            placeholder=placeholder,
            options=self.options,
            row=0,
        )
        super().__init__(timeout=timeout)

        self.add_item(self.select)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, row=1)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        self.clear_items()
        await interaction.response.edit_message(
            content=":negative_squared_cross_mark: | Cancelled", view=self
        )

    async def on_timeout(self):
        self.stop()
        self.clear_items()
        await self.message.edit(view=self)


class Confirm(discord.ui.View):
    def __init__(
        self,
        confirm_msg=":white_check_mark: | Confirmed",
        cancel_msg=":negative_squared_cross_mark: | Cancelled",
        *,
        timeout=180,
    ):
        super().__init__(timeout=timeout)
        self.value = None
        self.confirm_msg = confirm_msg
        self.cancel_msg = cancel_msg
        self.message = None

    async def on_timeout(self):
        self.value = False
        self.stop()
        self.clear_items()
        await self.message.edit(
            content=f":negative_squared_cross_mark: | Interaction has expired, please answer within **{self.timeout}** seconds.",
            view=self,
        )

    async def confirm_action(self, interaction):
        self.value = True
        self.stop()
        self.clear_items()

        if self.confirm_msg is None:
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.edit_message(content=self.confirm_msg, view=self)

    async def cancel_action(self, interaction):
        self.value = False
        self.stop()
        self.clear_items()

        if self.cancel_msg is None:
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.edit_message(content=self.cancel_msg, view=self)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.confirm_action(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cancel_action(interaction)


async def paginate(ctx, entries, page_size, embed_maker, *, timeout=300):
    if not entries:
        raise BotError("No entries in this list")

    paginator = Paginator(embed_maker, page_size, entries, timeout=timeout)

    if paginator.max_index == 0:
        return await ctx.send(embed=paginator.embed_maker(paginator, paginator.get_entry_subset()))

    paginator.message = await ctx.send(
        embed=paginator.embed_maker(paginator, paginator.get_entry_subset()),
        view=paginator,
    )

    await paginator.wait()


class Paginator(discord.ui.View):
    def __init__(self, embed_maker, page_size, entries, *, timeout=180):
        super().__init__(timeout=timeout)

        self.embed_maker = embed_maker
        self.entries = entries
        self.index = 0
        self.max_index = max(0, ((len(entries) - 1) // page_size))
        self.page_size = page_size
        self.message = None

    @property
    def page_number(self):
        return self.index + 1

    @property
    def page_count(self):
        return self.max_index + 1

    async def on_timeout(self):
        self.stop()
        self.clear_items()
        await self.message.edit(view=self)

    def get_entry_subset(self):
        subset = self.entries[self.index * self.page_size : (self.index + 1) * self.page_size]
        return subset[0] if self.page_size == 1 else subset

    async def change_page(self, interaction, change):
        if self.index + change > self.max_index:
            new_change = (change - 1) - (self.max_index - self.index)
            self.index = 0
            return await self.change_page(interaction, new_change)

        if self.index + change < 0:
            new_change = (change + 1) + self.index
            self.index = self.max_index
            return await self.change_page(interaction, new_change)

        self.index = self.index + change
        await interaction.response.edit_message(
            embed=self.embed_maker(self, self.get_entry_subset()), view=self
        )

    @discord.ui.button(label="-10", style=discord.ButtonStyle.grey)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.change_page(interaction, -10)

    @discord.ui.button(label="-1", style=discord.ButtonStyle.blurple)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.change_page(interaction, -1)

    @discord.ui.button(label="+1", style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.change_page(interaction, 1)

    @discord.ui.button(label="+10", style=discord.ButtonStyle.grey)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.change_page(interaction, 10)


class FightError(Exception):
    def __init__(self, message, event=None, format_dict=None):
        super().__init__(message)

        self.message = message
        self.event = event
        self.format_dict = format_dict

    def embed(self, bot):
        error_traceback = f"```py\n{traceback.format_exc()}\n```"
        embed = discord.Embed(
            title="Fight Error", description=error_traceback, colour=bot.bot_color
        )
        embed.add_field(name="Error String", value=self.event["string"], inline=False)
        embed.add_field(name="Error Tribute Number", value=self.event["tributes"], inline=False)
        embed.add_field(name="Error Tribute Killed", value=self.event["killed"], inline=False)
        embed.add_field(name="Error Tributes", value=str(self.format_dict), inline=False)
        embed.set_footer(**bot.bot_footer)

        return embed


class HungerGames(discord.ui.View):
    def __init__(self, bot, tributes, *, timeout=180):
        super().__init__(timeout=timeout)

        self.tributes = tributes
        self.day = 1
        self.dead = []
        self.phases = []
        self.index = 0
        self.ongoing = True
        self.phase = None
        self.bot = bot

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
            title=f"Hunger Games Simulator ({self.index + 1})",
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
                    if event["tributes"] <= len(idle_tributes)
                    and len(event["killed"]) < len(self.tributes)
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
            title=f"Dead Tributes ({self.index})",
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
            title=f"Hunger Game Winner ({self.index})",
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
    
def convert_key_to_label(key: str):
        return key.title().replace("_", " ")

def generate_edit_modal(title, values: dict, keys: List[str], optionals: List[str], embed_maker):
    class EditModal(discord.ui.Modal, title=title):
        async def on_submit(modal, interaction: discord.Interaction):
            for key in keys:
                text_input = discord.utils.get(
                    modal.children, label=convert_key_to_label(key)
                )
                if text_input.value.lower() == "null" and key in optionals:
                    values[key] = None
                elif text_input.value != "":
                    values[key] = text_input.value.strip()

            await interaction.response.defer()
            try:
                await interaction.followup.edit_message(
                    interaction.message.id, embed=await embed_maker()
                )
            except Exception as e:
                await interaction.followup.send(
                    f"Something went wrong with the embed: {e}", ephemeral=True
                )

    modal = EditModal()
    for key in keys:
        converted_default = None
        if isinstance(values[key], Iterable):
            converted_default = ", ".join(str(x) for x in values[key])

        modal.add_item(
            discord.ui.TextInput(
                label=convert_key_to_label(key),
                placeholder=key
                if key not in optionals
                else "Type NULL to reset the field",
                required=False,
                default=converted_default,
                max_length=2000,
            )
        )

    return modal

def chunker(seq, size):
    return [seq[pos:pos + size] for pos in range(0, len(seq), size)]

class EditModalSelect(discord.ui.Select):
    def __init__(self, values, title, optionals, embed_maker):
        self.attributes = values
        self.chunks = chunker(list(values.keys()), 5)
        self.title = title
        self.optionals = optionals
        self.embed_maker = embed_maker

        options = [
            discord.SelectOption(
                label=f"Edit - {', '.join(convert_key_to_label(key) for key in chunk)}",
                value=index 
            )
            for index, chunk in enumerate(self.chunks)
        ]

        super().__init__(options=options, row=1, placeholder="Pick a set of attributes to edit")

    async def callback(self, interaction: discord.Interaction):
        modal = generate_edit_modal(self.title, self.attributes, self.chunks[int(self.values[0])], self.optionals, self.embed_maker)
        await interaction.response.send_modal(modal)

class MultiInputEmbedView(discord.ui.View):
    def __init__(
        self,
        embed_maker: Callable,
        confirm_check: Callable,
        defaults: Dict,
        modal_title: str,
        optionals: List = (),
    ):
        super().__init__()

        self.embed_maker = embed_maker
        self.confirm_check = confirm_check
        self.values = defaults
        self.message = None
        self.modal_title = modal_title
        self.value = False
        self.optionals = optionals
        self.add_item(EditModalSelect(defaults, modal_title, optionals, self.generate_embed))

    async def generate_embed(self):
        if asyncio.iscoroutinefunction(self.embed_maker):
            return await self.embed_maker(self.values)

        return self.embed_maker(self.values)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            self.confirm_check(self.values)
            self.value = True
            self.stop()
            self.clear_items()
            await interaction.response.edit_message(content="Finishing construction", view=self)
        except BotError as e:
            await interaction.response.send_message(
                f"Something wrong with input: {e}", ephemeral=True
            )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        self.clear_items()
        await interaction.response.edit_message(content="Cancelled", view=self)
