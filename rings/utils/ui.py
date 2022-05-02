import discord

from rings.utils.hunger_game import events

import random
import traceback


class Confirm(discord.ui.View):
    def __init__(self, confirm_msg="Confirmed", cancel_msg="Cancelled", *, timeout=180):
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
            content=f":negative_squared_cross_mark: | Interaction has expireded, please answer within **{self.timeout}** seconds.",
            view=self,
        )

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.value = True
        self.stop()
        self.clear_items()
        await interaction.response.edit_message(content=self.confirm_msg, view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        self.clear_items()
        await interaction.response.edit_message(content=self.cancel_msg, view=self)


async def paginate(ctx, entries, page_size, embed_maker, *, timeout=300):
    paginator = Paginator(embed_maker, page_size, entries, timeout=timeout)
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

    async def on_timeout(self):
        self.stop()
        self.clear_items()
        await self.message.edit(view=self)

    def get_entry_subset(self):
        subset = self.entries[
            self.index * self.page_size : (self.index + 1) * self.page_size
        ]
        return subset[0] if self.page_size == 1 else subset

    @discord.ui.button(label="First", style=discord.ButtonStyle.secondary)
    async def first_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.index = 0
        await interaction.response.edit_message(
            embed=self.embed_maker(self, self.get_entry_subset()), view=self
        )

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def previous_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.index - 1 < 0:
            self.index = self.max_index
        else:
            self.index -= 1

        await interaction.response.edit_message(
            embed=self.embed_maker(self, self.get_entry_subset()), view=self
        )

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.index + 1 > self.max_index:
            self.index = 0
        else:
            self.index += 1

        await interaction.response.edit_message(
            embed=self.embed_maker(self, self.get_entry_subset()), view=self
        )

    @discord.ui.button(label="Last", style=discord.ButtonStyle.secondary)
    async def last_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.index = self.max_index
        await interaction.response.edit_message(
            embed=self.embed_maker(self, self.get_entry_subset()), view=self
        )

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
        embed.add_field(
            name="Error Tribute Number", value=self.event["tributes"], inline=False
        )
        embed.add_field(
            name="Error Tribute Killed", value=self.event["killed"], inline=False
        )
        embed.add_field(
            name="Error Tributes", value=str(self.format_dict), inline=False
        )
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

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def previous_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.index - 1 < 0:
            self.index = self.max_index - 1
        else:
            self.index -= 1

        await interaction.response.edit_message(
            embed=self.phases[self.index], view=self
        )

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.secondary)
    async def stop_fight(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.ongoing = False
        self.remove_item(self.stop_fight)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.index + 1 >= self.max_index:
            if not self.ongoing:
                self.index = 0
            else:
                self.index += 1
                self.prepare_next_phase(self.get_next_phase())

        else:
            self.index += 1

        await interaction.response.edit_message(
            embed=self.phases[self.index], view=self
        )

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
            title=f"Hunger Games Simulator ({self.index})",
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
            colour=self.bot.bot_color
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
