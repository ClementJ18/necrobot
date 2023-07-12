from __future__ import annotations
import asyncio
import datetime
import math
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

import discord
from discord.ext import commands
from discord.interactions import Interaction

from rings.utils.utils import BotError


class PollSelect(discord.ui.Select):
    view: PollView

    async def callback(self, interaction: Interaction):
        await interaction.client.db.query(
            "DELETE FROM necrobot.PollVotes WHERE user_id = $1 AND poll_id = $2",
            interaction.user.id,
            self.view.poll_id,
        )
        await interaction.client.db.query(
            "INSERT INTO necrobot.PollVotes VALUES($1, $2, $3)",
            ((int(option), interaction.user.id, self.view.poll_id) for option in self.values),
            many=True,
        )

        await interaction.response.edit_message(
            embed=self.view.generate_embed(await self.view.get_values(interaction.client))
        )
        await interaction.followup.send(":white_check_mark: | Vote(s) registered", ephemeral=True)


class PollView(discord.ui.View):
    def __init__(self, title, message, count, options, bot, poll_id=None):
        super().__init__(timeout=None)

        self.poll_id = poll_id

        self.title = title
        self.message = message
        self.count = count
        self.options = options

        self.bot = bot
        self.closer = None

        select_options = [
            discord.SelectOption(label=option[1], value=option[0]) for option in options
        ]
        self.add_item(
            PollSelect(
                options=select_options,
                min_values=count,
                max_values=count,
                custom_id="poll_select",
                row=0,
            )
        )

    def generate_embed(self, values):
        return self.bot.embed_poll(
            self.title,
            self.message,
            self.count,
            [f"- {value['message']}: {value['total']}" for value in values],
            self.closer,
        )

    async def get_values(self, bot):
        return await bot.db.query(
            """
                SELECT po.*, count(pv.*) as total 
                FROM necrobot.PollOptions AS po 
                LEFT OUTER JOIN necrobot.PollVotes AS pv ON po.id = pv.option_id 
                WHERE po.poll_id = $1
                GROUP BY po.id;
            """,
            self.poll_id,
        )

    @discord.ui.button(label="Close poll", style=discord.ButtonStyle.red, row=1, custom_id="poll_end")
    async def close_poll(self, interaction: discord.Interaction, button: discord.ui.Button):
        perms = await interaction.client.db.get_permission(
            interaction.user.id, interaction.guild.id
        )
        if perms < 3:
            return await interaction.response.send_message(
                ":negative_squared_cross_mark: | You don't have permissions to close a poll",
                ephemeral=True,
            )

        self.closer = (interaction.user, datetime.datetime.now())
        self.stop()
        self.clear_items()
        await interaction.response.edit_message(
            content="Poll closed!",
            embed=self.generate_embed(await self.get_values(interaction.client)), view=self
        )
        await interaction.followup.send(":white_check_mark: | Poll closed", ephemeral=True)


class PollEditorModal(discord.ui.Modal):
    view: PollEditorView

    def __init__(self, view):
        super().__init__(title="Add option")

        self.name = discord.ui.TextInput(label="Name of the option")
        self.add_item(self.name)
        self.view = view

    async def on_submit(self, interaction: Interaction):
        self.view.options.append(self.name.value)
        await interaction.response.edit_message(embed=await self.view.generate_embed())


class PollEditorView(discord.ui.View):
    def __init__(self, channel: discord.TextChannel, bot, author):
        super().__init__()
        self.converters = {
            "title": EmbedStringConverter(),
            "description": EmbedStringConverter(optional=True),
            "max_votes": EmbedRangeConverter(default="1", min=1, max=25),
        }
        self.attributes = {key: value.default for key, value in self.converters.items()}
        self.options = []
        self.channel = channel
        self.bot = bot
        self.author = author

    async def interaction_check(self, interaction: Interaction):
        if not interaction.user == self.author:
            await interaction.response.send_message(":negative_squared_cross_mark: | This button isn't for you!", ephemeral=True)
            return False
        
        return True

    async def generate_embed(self):
        return self.bot.embed_poll(
            self.attributes["title"],
            self.attributes["description"],
            self.attributes["max_votes"],
            [f"- {option}" for option in self.options],
        )

    @discord.ui.button(label="Add an option", style=discord.ButtonStyle.secondary)
    async def add_option(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.options) >= 25:
            return await interaction.response.send_message(
                ":negative_squared_cross_mark: | Cannot add more than 25 options"
            )

        await interaction.response.send_modal(PollEditorModal(self))

    @discord.ui.button(label="Delete last option", style=discord.ButtonStyle.red)
    async def delete_option(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.options:
            return await interaction.response.send_message(
                ":negative_squared_cross_mark: | Cannot delete option"
            )

        self.options.pop(-1)
        await interaction.response.edit_message(embed=await self.generate_embed())

    @discord.ui.button(label="Edit poll settings", style=discord.ButtonStyle.secondary)
    async def send_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            generate_edit_modal(
                "Poll Settings",
                self.attributes,
                list(self.attributes.keys()),
                self.converters,
                self,
            )
        )

    @discord.ui.button(label="Save", style=discord.ButtonStyle.green)
    async def save_poll(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.options:
            return await interaction.response.send_message(
                ":negative_squared_cross_mark: | Cannot save a poll with no options",
                ephemeral=True,
            )

        missing = [
            convert_key_to_label(key)
            for key, value in self.attributes.items()
            if not self.converters[key].optional and value in [None, ""]
        ]
        if missing:
            return await interaction.response.send_message(
                f"Missing required values: {', '.join(missing)}", ephemeral=True
            )

        self.stop()
        self.clear_items()
        await interaction.response.edit_message(content="Poll saved!", view=self)

        msg = await self.channel.send("Placeholder")

        await interaction.client.db.query(
            "INSERT INTO necrobot.PollsV2(message_id, channel_id, guild_id, message, title, max_votes) VALUES($1, $2, $3, $4, $5, $6)",
            msg.id,
            self.channel.id,
            self.channel.guild.id,
            self.attributes["description"],
            self.attributes["title"],
            int(self.attributes["max_votes"]),
        )

        ids = await interaction.client.db.query(
            "INSERT INTO necrobot.PollOptions(poll_id, message) select poll_id, message FROM unnest($1::poll_option[]) RETURNING (id, message);",
            [(msg.id, option) for option in self.options],
        )

        poll_view = PollView(
            self.attributes["title"],
            self.attributes["description"],
            int(self.attributes["max_votes"]),
            [option["row"] for option in ids],
            self.bot,
            msg.id,
        )
        await msg.edit(
            content="A new poll has opened!",
            embed=poll_view.generate_embed(
                [{"message": option, "total": 0} for option in self.options]
            ),
            view=poll_view,
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
        author,
        *,
        min_values=1,
        max_values=1,
        placeholder="Select...",
        timeout=180,
    ):
        self.options = [discord.SelectOption(label=x) for x in options]
        self.value = False
        self.author = author
        self.select = Select(
            min_values=min_values,
            max_values=max_values,
            placeholder=placeholder,
            options=self.options,
            row=0,
        )
        super().__init__(timeout=timeout)

        self.add_item(self.select)

    async def interaction_check(self, interaction: Interaction):
        if not interaction.user == self.author:
            await interaction.response.send_message(":negative_squared_cross_mark: | This button isn't for you!", ephemeral=True)
            return False
        
        return True

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
        author,
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
        self.author = author

    async def interaction_check(self, interaction: Interaction):
        if not interaction.user == self.author:
            await interaction.response.send_message(":negative_squared_cross_mark: | This button isn't for you!", ephemeral=True)
            return False
        
        return True

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

    paginator = Paginator(embed_maker, page_size, entries, ctx.author, timeout=timeout)

    if paginator.max_index == 0:
        return await ctx.send(embed=paginator.embed_maker(paginator, paginator.get_entry_subset()))

    paginator.message = await ctx.send(
        embed=paginator.embed_maker(paginator, paginator.get_entry_subset()),
        view=paginator,
    )

    await paginator.wait()


class Paginator(discord.ui.View):
    def __init__(self, embed_maker, page_size, entries, author, *, timeout=180):
        super().__init__(timeout=timeout)

        self.embed_maker = embed_maker
        self.entries = entries
        self.index = 0
        self.max_index = max(0, ((len(entries) - 1) // page_size))
        self.page_size = page_size
        self.message = None
        self.author = author

    async def interaction_check(self, interaction: Interaction):
        if not interaction.user == self.author:
            await interaction.response.send_message(":negative_squared_cross_mark: | This button isn't for you!", ephemeral=True)
            return False
        
        return True

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


def convert_key_to_label(key: str):
    return key.title().replace("_", " ")


@dataclass
class EmbedDefaultConverter:
    default: str = ""
    optional: bool = False

    def return_value(self, argument):
        if argument.lower() in ["null", "", None]:
            return None

        return self.convert(argument)

    def convert(self, argument):
        raise NotImplementedError


@dataclass
class EmbedNumberConverter(EmbedDefaultConverter):
    def convert(self, argument: str):
        if not argument.isdigit():
            raise commands.BadArgument("Not a valid number")

        return float(argument)


@dataclass
class EmbedIntegerConverter(EmbedNumberConverter):
    def convert(self, argument: str):
        return int(super().convert(argument))


@dataclass
class EmbedBooleanConverter(EmbedDefaultConverter):
    def convert(self, argument: str):
        return argument.lower() in ["true", "yes", "y", "1", "t"]


@dataclass
class EmbedStringConverter(EmbedDefaultConverter):
    def convert(self, argument: str):
        return argument


@dataclass
class EmbedRangeConverter(EmbedIntegerConverter):
    max: int = math.inf
    min: int = -math.inf

    def convert(self, argument):
        argument = super().convert(argument)

        if argument > self.max:
            raise commands.BadArgument(f"Number must be less than {self.max}")

        if argument < self.min:
            raise commands.BadArgument(f"Number must be more than {self.min}")

        return argument


@dataclass
class EmbedChoiceConverter(EmbedDefaultConverter):
    choices: List[str] = ()

    def convert(self, argument):
        argument = argument.strip().lower()
        if argument not in self.choices:
            raise commands.BadArgument(f"Choice must be one of {', '.join(self.choices)}")

        return argument


@dataclass
class EmbedIterableConverter(EmbedDefaultConverter):
    separator: str = ","

    def convert(self, argument):
        return [arg.strip() for arg in argument.split(self.separator)]


def generate_edit_modal(
    title,
    attributes: dict,
    keys: List[str],
    converters: Dict[str, EmbedDefaultConverter],
    view: "MultiInputEmbedView",
):
    class EditModal(discord.ui.Modal, title=title):
        async def on_submit(self, interaction: discord.Interaction):
            await interaction.response.defer()

            errors = []
            for key in keys:
                text_input = discord.utils.get(self.children, label=convert_key_to_label(key))

                converter = converters[key]

                try:
                    new_value = converter.return_value(text_input.value)
                    if converter.default and new_value is None:
                        attributes[key] = None
                    else:
                        attributes[key] = text_input.value
                except Exception as e:
                    errors.append(f"- {key}: {str(e)}")

            if not errors:
                try:
                    await interaction.followup.edit_message(
                        interaction.message.id, embed=await view.generate_embed()
                    )
                except Exception as e:
                    await interaction.followup.send(
                        f"Something went wrong while sending an embed: {e}"
                    )
                    await interaction.followup.edit_message(interaction.message.id)
            else:
                errors_str = "\n".join(errors)
                await interaction.followup.send(
                    f"Something went wrong with some of the values submitted:\n {errors_str}",
                    ephemeral=True,
                )
                await interaction.followup.edit_message(interaction.message.id)

    modal = EditModal()
    for key in keys:
        modal.add_item(
            discord.ui.TextInput(
                label=convert_key_to_label(key),
                placeholder=key
                if not converters[key].optional
                else "Type NULL to reset the field",
                required=False,
                default=attributes[key],
                max_length=2000,
            )
        )

    return modal


def chunker(seq, size):
    return [seq[pos : pos + size] for pos in range(0, len(seq), size)]


class EditModalSelect(discord.ui.Select):
    def __init__(self, converters, values, title):
        self.converters = converters
        self.attributes = values
        self.chunks = chunker(list(values.keys()), 5)
        self.title = title

        options = [
            discord.SelectOption(
                label=f"Edit - {', '.join(convert_key_to_label(key) for key in chunk)}",
                value=index,
            )
            for index, chunk in enumerate(self.chunks)
        ]

        super().__init__(options=options, row=1, placeholder="Pick a set of attributes to edit")

    async def callback(self, interaction: discord.Interaction):
        modal = generate_edit_modal(
            self.title,
            self.attributes,
            self.chunks[int(self.values[0])],
            self.converters,
            self.view,
        )
        await interaction.response.send_modal(modal)


class EmbedConverterError(Exception):
    pass


class MultiInputEmbedView(discord.ui.View):
    def __init__(
        self,
        embed_maker: Callable,
        defaults: Dict[str, EmbedDefaultConverter],
        modal_title: str,
        author,
        *,
        extra_confirm_check: Callable = None,
    ):
        super().__init__()

        self.embed_maker = embed_maker
        self.extra_confirm_check = extra_confirm_check
        self.converters = defaults
        self.values = {key: value.default for key, value in defaults.items()}
        self.message = None
        self.modal_title = modal_title
        self.value = False
        self.author = author
        self.add_item(EditModalSelect(self.converters, self.values, modal_title))

    async def interaction_check(self, interaction: Interaction):
        if not interaction.user == self.author:
            await interaction.response.send_message(":negative_squared_cross_mark: | This button isn't for you!", ephemeral=True)
            return False
        
        return True

    async def generate_embed(self):
        converted_values = self.convert_values()
        if asyncio.iscoroutinefunction(self.embed_maker):
            return await self.embed_maker(converted_values)

        return self.embed_maker(converted_values)

    def convert_values(self):
        final_values = {}
        for key, value in self.values.items():
            converter = self.converters[key]
            try:
                final_values[key] = converter.return_value(value)
            except Exception as e:
                raise EmbedConverterError(f"{key}: {e}") from e

        return final_values

    def confirm_check(self, values):
        missing = [
            convert_key_to_label(key)
            for key, value in values.items()
            if not self.converters[key].optional and value is None
        ]
        if missing:
            raise BotError(f"Missing required values: {', '.join(missing)}")

        if self.extra_confirm_check is not None:
            self.extra_confirm_check(values)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            self.confirm_check(self.convert_values())
            self.value = True
            self.stop()
            self.clear_items()
            await interaction.response.edit_message(content="Finishing construction", view=self)
        except BotError as e:
            await interaction.response.send_message(str(e), ephemeral=True, delete_after=30)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        self.clear_items()
        await interaction.response.edit_message(content="Cancelled", view=self)
