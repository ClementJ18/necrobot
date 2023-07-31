from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Mapping, Optional, Tuple, Union
import discord
from discord.ext import commands as cmd
from rings.utils.ui import Paginator

if TYPE_CHECKING:
    from bot import NecroBot

class GroupPaginator(Paginator):
    pass 

class CogPaginator(Paginator):
    pass

class NecrobotHelp(cmd.HelpCommand):
    context: cmd.Context[NecroBot]

    def command_not_found(self, string):
        return f":negative_squared_cross_mark: | Command **{string}** not found."

    def subcommand_not_found(self, command: cmd.Command, string):
        return f":negative_squared_cross_mark: | Command **{command.qualified_name}** has no subcommand **{string}**"

    def get_command_signature(self, command: cmd.Command):
        """Retrieves the signature portion of the help page."""
        prefix = self.context.clean_prefix
        signature = command.signature.replace("<", "[").replace(">", "]")
        return f"{prefix}{command.qualified_name} {signature}"

    def get_ending_note(self):
        command_name = self.context.invoked_with
        return (
            "\nCommands in `codeblocks` are commands you can use, __underlined__ means the command has subcommands, commands with ~~strikethrough~~ you cannot use but you can still check the help. Commands in ***italics*** are recent additions.\n"
            "Type `{0}{1} [command]` for more info on a command.(Example: `{0}help edain`)\n"
            "You can also type `{0}{1} [category]` for more info on a category. Don't forget the first letter is always uppercase. (Example: `{0}help Animals`) \n".format(
                self.context.clean_prefix, command_name
            )
        )

    async def format_command_name(self, command: cmd.Command):
        async def predicate():
            try:
                return await command.can_run(self.context)
            except cmd.CommandError:
                return False

        valid = await predicate()
        if valid and command.enabled:
            if command.qualified_name in self.context.bot.new_commands:
                return f"***{command.qualified_name}***"

            if isinstance(command, cmd.Group):
                return f"__`{command.qualified_name}`__"
            return f"`{command.qualified_name}`"

        return f"~~{command.qualified_name}~~"

    async def get_brief_signature(self, command: cmd.Command):
        help = command.help
        if help is None:
            help = "{usage}"

        first_line = help.split("\n")[0]
        formatted = first_line.format(usage=self.get_command_signature(command))

        if len(formatted) > 250:
            return formatted[:247] + "..."

        return formatted
    
    async def embed_cog(self, cog: cmd.Cog, commands: List[cmd.Command]) -> discord.Embed:
        help_msg = ""
        for command in commands:
            name = await self.format_command_name(command)
            help_msg += f"{name} - {await self.get_brief_signature(command)}\n"

        help_msg += self.get_ending_note()

        embed = discord.Embed(
            title=f"{cog.qualified_name} Help",
            description=help_msg,
            color=self.context.bot.bot_color
        )
        embed.set_footer(**self.context.bot.bot_footer)

        return embed
    
    async def embed_command(self, command: cmd.Command) -> discord.Embed:
        description = command.help
        signature = f"__Usage__\n{self.get_command_signature(command)}"

        perms_check = discord.utils.find(
            lambda x: x.__qualname__.startswith("has_perms"), command.checks
        )
        if perms_check is not None:
            name = self.context.bot.perms_name[perms_check.level]
            signature = (
                f"**Permission level required: {name} ({perms_check.level}+)**\n\n{signature}"
            )

        owner_check = discord.utils.find(
            lambda x: x.__qualname__.startswith("is_owner"), command.checks
        )
        if owner_check is not None:
            signature = (
                f"**Owner only command**\n\n{signature}"
            )

        embed = discord.Embed(
            color=self.context.bot.bot_color,
            title=str(command),
            description=description.format(usage=signature, pre=self.context.clean_prefix)
        )
        embed.set_footer(**self.context.bot.bot_footer)

        return embed

    async def embed_group(self, group: cmd.Group) -> discord.Embed:
        embed = await self.embed_command(group)
        if any(not command.hidden for command in group.commands):
            embed.description += "\n\n__Subcommands__\n"

        for command in group.commands:
            if not command.hidden:
                name = await self.format_command_name(command)
                embed.description += f"{name} - {await self.get_brief_signature(command)}\n"

        return embed

    async def send_bot_help(self, mapping: Mapping[Optional[cmd.Cog], List[cmd.Command[Any, ..., Any]]]):
        async def embed_maker(view: CogPaginator, entry: Tuple[Optional[cmd.Cog], List[cmd.Command[Any, ..., Any]]]):
            if view.index == 0:
                embed = discord.Embed(
                    title=f":information_source: NecroBot Help Menu {view.page_string} :information_source:",
                    description=self.context.bot.description,
                    color=self.context.bot.bot_color
                )
                embed.set_footer(**self.context.bot.bot_footer)
                return embed

            embed = await self.embed_cog(entry[0], entry[1])
            embed.title += f" ({view.page_string})"
            return embed

        sorted_mapping = sorted(mapping.items(), key=lambda item: item[0].qualified_name if item[0] else "None")
        await CogPaginator(embed_maker, 1, [None, *[m for m in sorted_mapping if m[1] and m[0] is not None]], self.context.author).start(self.get_destination())

    async def send_cog_help(self, cog: cmd.Cog):
        async def embed_maker(view: CogPaginator, entry: cmd.Cog):
            return await self.embed_cog(entry, entry.get_commands())

        await CogPaginator(embed_maker, 1, [cog], self.context.author).start(self.get_destination())

    async def send_command_help(self, command: cmd.Command):
        await self.get_destination().send(embed=await self.embed_command(command))

    async def send_group_help(self, group: cmd.Group[Any, ..., Any]):
        async def embed_maker(view: GroupPaginator, entry: Union[cmd.Group, cmd.Command]):
            if isinstance(entry, cmd.Group):
                embed = await self.embed_group(entry)
                embed.title += f" ({view.page_string})"
                return embed
            
            embed = await self.embed_command(entry)
            embed.title += f" ({view.page_string})"
            return embed

        await GroupPaginator(embed_maker, 1, [group, *group.commands], self.context.author).start(self.get_destination())
