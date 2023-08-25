from __future__ import annotations

import asyncio
import datetime
import logging
import math
import re
import traceback
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, List, TypeVar, Union

import discord
from discord.ext import commands
from discord.interactions import Interaction
from discord.ui.item import Item

from rings.utils.utils import BotError

if TYPE_CHECKING:
    from bot import NecroBot

CUSTOM_EMOJI = r"<:[^\s]+:([0-9]*)>"
UNICODE_EMOJI = r":\w*:"

logger = logging.getLogger()


def strip_emoji(content):
    return re.sub(UNICODE_EMOJI, "", re.sub(CUSTOM_EMOJI, "", content)).strip()


class BaseView(discord.ui.View):
    author: discord.Member | discord.User

    async def on_error(
        self, interaction: Interaction[NecroBot], error: Exception, item: Item[Any]
    ):
        error_traceback = " ".join(
            traceback.format_exception(type(error), error, error.__traceback__, chain=True)
        )

        embed = discord.Embed(
            title="View Error",
            description=f"```py\n{error_traceback}\n```",
            colour=interaction.client.bot_color,
        )

        try:
            logger.exception(error)
            await interaction.client.error_channel.send(embed=embed)
        except discord.HTTPException as e:
            logger.exception(f"Failed to send error interaction: {e}")

        await interaction.response.send_message(
            f":negative_squared_cross_mark: | Error with interaction: {error}", ephemeral=True
        )

    async def interaction_check(self, interaction: Interaction[NecroBot]):
        if not hasattr(self, "author"):
            return True

        if not interaction.user == self.author:
            await interaction.response.send_message(
                ":negative_squared_cross_mark: | This button isn't for you!", ephemeral=True
            )
            return False

        return True


class PollSelect(discord.ui.Select):
    view: PollView

    async def callback(self, interaction: discord.Interaction[NecroBot]):
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


class PollView(BaseView):
    def __init__(
        self,
        title: str,
        message: str,
        count: int,
        options: List[str],
        bot: NecroBot,
        poll_id: int = None,
    ):
        super().__init__(timeout=None)

        self.poll_id = poll_id

        self.title = title
        self.message = message
        self.count = count
        self.options = options

        self.bot = bot
        self.closer = None

        select_options = [
            discord.SelectOption(label=strip_emoji(option[1]), value=option[0])
            for option in options
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

    def generate_embed(self, values: Dict[str, Any]):
        return self.bot.embed_poll(
            self.title,
            self.message,
            self.count,
            [f"- {value['message']}: {value['total']}" for value in values],
            self.closer,
        )

    async def get_values(self, bot: NecroBot):
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

    @discord.ui.button(
        label="Close poll", style=discord.ButtonStyle.red, row=1, custom_id="poll_end"
    )
    async def close_poll(self, interaction: discord.Interaction[NecroBot], _: discord.ui.Button):
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
            embed=self.generate_embed(await self.get_values(interaction.client)),
            view=self,
        )
        await interaction.followup.send(":white_check_mark: | Poll closed", ephemeral=True)


class PollEditorModal(discord.ui.Modal):
    def __init__(self, view: PollEditorView):
        super().__init__(title="Add up to three options")

        self.option_1 = discord.ui.TextInput(label="Option 1", required=True, max_length=150)
        self.option_2 = discord.ui.TextInput(label="Option 2", required=False, max_length=150)
        self.option_3 = discord.ui.TextInput(label="Option 3", required=False, max_length=150)

        self.add_item(self.option_1)
        self.add_item(self.option_2)
        self.add_item(self.option_3)

        self.view = view

    async def on_submit(self, interaction: discord.Interaction[NecroBot]):
        errors = []

        for index, option in enumerate([self.option_1, self.option_2, self.option_3]):
            if option.value:
                stripped = strip_emoji(option.value)
                if not stripped:
                    errors.append(
                        f"- Option {index} only contains emojis, please also specify text"
                    )
                elif len(stripped) > 100:
                    errors.append(
                        f"- Option {index} is longer than 100 characters after emoji removal"
                    )
                else:

                    self.view.options.append(option.value)

        await interaction.response.edit_message(embed=await self.view.generate_embed())

        if errors:
            stringed_errors = "\n".join(errors)
            await interaction.followup.send(
                f"Could not add some options:\n{stringed_errors}", ephemeral=True
            )


class PollEditorView(BaseView):
    def __init__(self, channel: discord.TextChannel, bot: NecroBot, author: discord.Member):
        super().__init__()
        self.converters: Dict[str, EmbedDefaultConverter] = {
            "title": EmbedStringConverter(),
            "description": EmbedStringConverter(optional=True, style=discord.TextStyle.paragraph),
            "max_votes": EmbedRangeConverter(default="1", min=1, max=25),
        }
        self.attributes: Dict[str, str] = {
            key: value.default for key, value in self.converters.items()
        }
        self.options = []
        self.channel = channel
        self.bot = bot
        self.author = author

    async def generate_embed(self):
        return self.bot.embed_poll(
            self.attributes["title"],
            self.attributes["description"],
            self.attributes["max_votes"],
            [f"- {option}" for option in self.options],
        )

    @discord.ui.button(label="Add options", style=discord.ButtonStyle.secondary)
    async def add_option(self, interaction: discord.Interaction[NecroBot], _: discord.ui.Button):
        if len(self.options) >= 25:
            return await interaction.response.send_message(
                ":negative_squared_cross_mark: | Cannot add more than 25 options"
            )

        await interaction.response.send_modal(PollEditorModal(self))

    @discord.ui.button(label="Delete last option", style=discord.ButtonStyle.red)
    async def delete_option(
        self, interaction: discord.Interaction[NecroBot], _: discord.ui.Button
    ):
        if not self.options:
            return await interaction.response.send_message(
                ":negative_squared_cross_mark: | Cannot delete option"
            )

        self.options.pop(-1)
        await interaction.response.edit_message(embed=await self.generate_embed())

    @discord.ui.button(label="Edit poll settings", style=discord.ButtonStyle.secondary)
    async def send_modal(self, interaction: discord.Interaction[NecroBot], _: discord.ui.Button):
        await interaction.response.send_modal(
            EditModal(
                title="Poll Settings",
                attributes=self.attributes,
                keys=list(self.attributes.keys()),
                converters=self.converters,
                view=self,
            )
        )

    @discord.ui.button(label="Save", style=discord.ButtonStyle.green)
    async def save_poll(self, interaction: discord.Interaction[NecroBot], _: discord.ui.Button):
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

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_poll(self, interaction: discord.Interaction[NecroBot], _: discord.ui.Button):
        self.clear_items()
        self.stop()
        await interaction.response.edit_message(view=self)


class Select(discord.ui.Select):
    view: SelectView

    async def callback(self, interaction: discord.Interaction[NecroBot]):
        self.view.value = True
        self.view.stop()
        self.view.clear_items()
        await interaction.response.edit_message(
            content=f":white_check_mark: | Choice was **{self.values[0]}**",
            view=self.view,
        )


class SelectView(BaseView):
    def __init__(
        self,
        options: List[str],
        author: discord.Member,
        *,
        min_values: int = 1,
        max_values: int = 1,
        placeholder: str = "Select...",
        timeout: int = 180,
    ):
        super().__init__(timeout=timeout)

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
        self.message: discord.Message = None

        self.add_item(self.select)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, row=1)
    async def cancel(self, interaction: discord.Interaction[NecroBot], _: discord.ui.Button):
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


class Confirm(BaseView):
    def __init__(
        self,
        author: discord.Member,
        confirm_msg: str = ":white_check_mark: | Confirmed",
        cancel_msg: str = ":negative_squared_cross_mark: | Cancelled",
        *,
        timeout: int = 180,
    ):
        super().__init__(timeout=timeout)
        self.value = None
        self.confirm_msg = confirm_msg
        self.cancel_msg = cancel_msg
        self.message: discord.Message = None
        self.author = author

    async def on_timeout(self):
        self.value = False
        self.stop()
        self.clear_items()
        await self.message.edit(
            content=f":negative_squared_cross_mark: | Interaction has expired, please answer within **{self.timeout}** seconds.",
            view=self,
        )

    async def confirm_action(self, interaction: discord.Interaction[NecroBot]):
        self.value = True
        self.stop()
        self.clear_items()

        if self.confirm_msg is None:
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.edit_message(content=self.confirm_msg, view=self)

    async def cancel_action(self, interaction: discord.Interaction[NecroBot]):
        self.value = False
        self.stop()
        self.clear_items()

        if self.cancel_msg is None:
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.edit_message(content=self.cancel_msg, view=self)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction[NecroBot], _: discord.ui.Button):
        await self.confirm_action(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction[NecroBot], _: discord.ui.Button):
        await self.cancel_action(interaction)


class Paginator(BaseView):
    def __init__(
        self,
        embed_maker: Callable[[Paginator, Union[Any, List[Any]]], discord.Embed],
        page_size: int,
        entries: List[Any],
        author: discord.Member | discord.User,
        *,
        timeout: int = 180,
    ):
        super().__init__(timeout=timeout)

        if not entries:
            raise BotError("No entries in this list")

        self.embed_maker = embed_maker
        self.entries = entries
        self.index = 0
        self.max_index = max(0, ((len(entries) - 1) // page_size))
        self.page_size = page_size
        self.message: discord.Message = None
        self.author = author

    def view_maker(self, entries: Union[Any, List[Any]]):
        pass

    @property
    def page_number(self) -> int:
        return self.index + 1

    @property
    def page_count(self) -> int:
        return self.max_index + 1

    @property
    def page_string(self) -> str:
        return f"{self.page_number}/{self.page_count}"

    async def start(self, channel: discord.abc.Messageable):
        entries = self.get_entry_subset()
        embed = await self.generate_embed(entries)
        self.view_maker(entries)

        if self.max_index == 0:
            for button in [self.first_page, self.previous_page, self.next_page, self.last_page]:
                self.remove_item(button)

        self.message = await channel.send(embed=embed, view=self)

    async def on_timeout(self):
        self.stop()
        self.clear_items()

        if self.message is not None:
            await self.message.edit(view=self)

    def get_entry_subset(self) -> Union[Any, List[Any]]:
        subset = self.entries[self.index * self.page_size : (self.index + 1) * self.page_size]
        return subset[0] if self.page_size == 1 else subset

    async def change_page(self, interaction: discord.Interaction[NecroBot], change: int):
        if self.index + change > self.max_index:
            new_change = (change - 1) - (self.max_index - self.index)
            self.index = 0
            return await self.change_page(interaction, new_change)

        if self.index + change < 0:
            new_change = (change + 1) + self.index
            self.index = self.max_index
            return await self.change_page(interaction, new_change)

        self.index = self.index + change
        entries = self.get_entry_subset()
        self.view_maker(entries)
        await interaction.response.edit_message(
            embed=await self.generate_embed(entries), view=self
        )

    async def generate_embed(self, entries):
        if asyncio.iscoroutinefunction(self.embed_maker):
            return await self.embed_maker(self, entries)

        return self.embed_maker(self, entries)

    @discord.ui.button(label="-10", style=discord.ButtonStyle.grey, row=0)
    async def first_page(self, interaction: discord.Interaction[NecroBot], _: discord.ui.Button):
        await self.change_page(interaction, -10)

    @discord.ui.button(label="-1", style=discord.ButtonStyle.blurple, row=0)
    async def previous_page(
        self, interaction: discord.Interaction[NecroBot], _: discord.ui.Button
    ):
        await self.change_page(interaction, -1)

    @discord.ui.button(label="+1", style=discord.ButtonStyle.blurple, row=0)
    async def next_page(self, interaction: discord.Interaction[NecroBot], _: discord.ui.Button):
        await self.change_page(interaction, 1)

    @discord.ui.button(label="+10", style=discord.ButtonStyle.grey, row=0)
    async def last_page(self, interaction: discord.Interaction[NecroBot], _: discord.ui.Button):
        await self.change_page(interaction, 10)


def convert_key_to_label(key: str):
    return key.title().replace("_", " ")


@dataclass
class EmbedDefaultConverter:
    default: str = ""
    optional: bool = False
    style: discord.TextStyle = discord.TextStyle.short

    def convert(self, argument: str) -> Any:
        raise NotImplementedError

    def return_value(self, argument: str) -> Any:
        argument = str(argument)
        if argument.lower() in ["null", "", "none"]:
            return None

        return self.convert(argument)


@dataclass
class EmbedNumberConverter(EmbedDefaultConverter):
    def convert(self, argument: str) -> float:
        if not argument.isdigit():
            raise commands.BadArgument("Not a valid number")

        return float(argument)


@dataclass
class EmbedIntegerConverter(EmbedNumberConverter):
    def convert(self, argument: str) -> int:
        return int(super().convert(argument))


@dataclass
class EmbedBooleanConverter(EmbedDefaultConverter):
    def convert(self, argument: str) -> bool:
        return argument.lower() in ["true", "yes", "y", "1", "t"]


@dataclass
class EmbedStringConverter(EmbedDefaultConverter):
    def convert(self, argument: str) -> str:
        return argument


@dataclass
class EmbedRangeConverter(EmbedIntegerConverter):
    max: int = math.inf
    min: int = -math.inf

    def convert(self, argument: str) -> int:
        argument = super().convert(argument)

        if argument > self.max:
            raise commands.BadArgument(f"Number must be less than {self.max}")

        if argument < self.min:
            raise commands.BadArgument(f"Number must be more than {self.min}")

        return argument


@dataclass
class EmbedChoiceConverter(EmbedDefaultConverter):
    choices: List[str] = ()

    def convert(self, argument: str) -> str:
        argument = argument.strip().lower()
        if argument not in self.choices:
            raise commands.BadArgument(f"Choice must be one of {', '.join(self.choices)}")

        return argument


@dataclass
class EmbedIterableConverter(EmbedDefaultConverter):
    separator: str = ","

    def convert(self, argument) -> List:
        return [arg.strip() for arg in argument.split(self.separator)]


class EditModal(discord.ui.Modal):
    def __init__(
        self,
        *,
        title: str,
        keys: List[str],
        converters: Dict[str, EmbedDefaultConverter],
        attributes: Dict[str, str],
        view: MultiInputEmbedView,
    ) -> None:
        super().__init__(title=title)

        self.keys = keys
        self.converters = converters
        self.attributes = attributes
        self.view = view

        for key in keys:
            self.add_item(
                discord.ui.TextInput(
                    label=convert_key_to_label(key),
                    placeholder=key
                    if not converters[key].optional
                    else "Type NULL to reset the field",
                    required=False,
                    default=attributes[key],
                    max_length=2000,
                    style=converters[key].style,
                )
            )

    async def on_submit(self, interaction: discord.Interaction[NecroBot]):
        await interaction.response.defer()

        errors = []
        for key in self.keys:
            text_input: discord.TextInput = discord.utils.get(
                self.children, label=convert_key_to_label(key)
            )

            converter = self.converters[key]

            try:
                new_value = converter.return_value(text_input.value)
                if converter.default and new_value is None:
                    self.attributes[key] = None
                else:
                    self.attributes[key] = text_input.value
            except Exception as e:
                errors.append(f"- {convert_key_to_label(key)}: {e}")

        if not errors:
            try:
                await interaction.followup.edit_message(
                    interaction.message.id, embed=await self.view.generate_embed()
                )
            except Exception as e:
                await interaction.followup.send(
                    f"Something went wrong while sending an embed: {e}"
                )
                await interaction.followup.edit_message(interaction.message.id)
        else:
            errors_str = "\n".join(errors)
            await interaction.followup.send(
                f"Something went wrong with some of the values submitted:{errors_str}",
                ephemeral=True,
            )
            await interaction.followup.edit_message(interaction.message.id)


D = TypeVar("")


def chunker(seq: List[D], size: int) -> List[D]:
    return [seq[pos : pos + size] for pos in range(0, len(seq), size)]


class EditModalSelect(discord.ui.Select):
    def __init__(
        self, converters: Dict[str, EmbedDefaultConverter], values: Dict[str, str], title: str
    ):
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

    async def callback(self, interaction: discord.Interaction[NecroBot]):
        modal = EditModal(
            title=self.title,
            keys=self.chunks[int(self.values[0])],
            converters=self.converters,
            attributes=self.attributes,
            view=self.view,
        )
        await interaction.response.send_modal(modal)


class EmbedConverterError(Exception):
    pass


class MultiInputEmbedView(BaseView):
    def __init__(
        self,
        embed_maker: Callable[[Paginator, List[Any]], discord.Embed],
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

    def confirm_check(self, values: Dict[str, Any]):
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
    async def confirm(self, interaction: discord.Interaction[NecroBot], _: discord.ui.Button):
        try:
            self.confirm_check(self.convert_values())
            self.value = True
            self.stop()
            self.clear_items()
            await interaction.response.edit_message(content="Finishing construction", view=self)
        except BotError as e:
            await interaction.response.send_message(str(e), ephemeral=True, delete_after=30)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction[NecroBot], _: discord.ui.Button):
        self.value = False
        self.stop()
        self.clear_items()
        await interaction.response.edit_message(content="Cancelled", view=self)
