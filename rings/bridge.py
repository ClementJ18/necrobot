from __future__ import annotations

import asyncio
import logging
import traceback
from typing import TYPE_CHECKING

import discord
from bs4 import BeautifulSoup
from discord.ext import commands
from robobrowser.forms.form import Form

from rings.utils.config import MU_Password, MU_Username
from rings.utils.ui import BaseView
from rings.utils.utils import NEGATIVE_CHECK, POSITIVE_CHECK, QueuedPosts, testing_or

if TYPE_CHECKING:
    from bot import NecroBot

logger = logging.getLogger()

bug_mapping = {
    "angmar": {
        "emoji": "angmar:687748138345169075",
        "url": "https://modding-union.com/index.php/topic,33016.0.html",
        "title": "Angmar Bugs",
    },
    "dwarves": {
        "emoji": "erebor:687748357543952417",
        "url": "https://modding-union.com/index.php/topic,31202.0.html",
        "title": "Dwarven Bugs",
    },
    "gondor": {
        "emoji": "gondor:687747730684117012",
        "url": "https://modding-union.com/index.php/topic,30434.0.html",
        "title": "Gondor/Arnor Bugs",
    },
    "imladris": {
        "emoji": "imladris:687748566105849890",
        "url": "https://modding-union.com/index.php/topic,33678.0.html",
        "title": "Imladris Bugs",
    },
    "isengard": {
        "emoji": "isengard:687748680182530086",
        "url": "https://modding-union.com/index.php/topic,30436.0.html",
        "title": "Isengard Bugs",
    },
    "lothlorien": {
        "emoji": "lothlorien:687748760054661152",
        "url": "https://modding-union.com/index.php/topic,32089.0.html",
        "title": "Lothlorien Bugs",
    },
    "mm": {
        "emoji": "mm:688040356184588423",
        "url": "https://modding-union.com/index.php/topic,36986.0.html",
        "title": "Misty Mountain Bugs",
    },
    "mordor": {
        "emoji": "mordor:687749364692549651",
        "url": "https://modding-union.com/index.php/topic,30433.0.html",
        "title": "Mordor Bugs",
    },
    "rohan": {
        "emoji": "rohan:687747731716177930",
        "url": "https://modding-union.com/index.php/topic,30435.0.html",
        "title": "Rohan Bugs",
    },
    "cah": {
        "emoji": "eothain:361473129253568513",
        "url": "https://modding-union.com/index.php/topic,30438.0.html",
        "title": "Create-a-hero Bugs",
    },
    "wotr": {
        "emoji": "onering:342033729637711872",
        "url": "https://modding-union.com/index.php/topic,30437.0.html",
        "title": "War of the Ring Bugs",
    },
    "audio": {
        "emoji": "LUL:778021945685704724",
        "url": "https://modding-union.com/index.php/topic,31224.0.html",
        "title": "Audio Bugs",
    },
    "horde": {
        "emoji": "mu:733692917318942801",
        "url": "https://modding-union.com/index.php/topic,35939.0.html",
        "title": "Horde Map Bugs",
    },
    "general": {
        "emoji": "edain:339025957136629772",
        "url": "https://modding-union.com/index.php/topic,33017.0.html",
        "title": "General Bugs",
    },
    "map": {
        "emoji": "dwarf_f:778019875120742400",
        "url": "https://modding-union.com/index.php/topic,30440.0.html",
        "title": "Map Bugs",
    },
    "ai": {
        "emoji": "gildor:340577178192445441",
        "url": "https://modding-union.com/index.php/topic,30439.0.html",
        "title": "AI Bugs",
    },
}

TEST_CHANNEL = 722040731946057789


class BridgeView(BaseView):
    def __init__(self, message: discord.Message):
        super().__init__()

        self.message = message
        self.content = message.content

    @discord.ui.select(
        options=[
            discord.SelectOption(
                label=thread["title"], value=name, emoji=discord.PartialEmoji.from_str(thread["emoji"])
            )
            for name, thread in bug_mapping.items()
        ],
        placeholder="Select the thread to send to",
        row=0,
    )
    async def thread_select(self, interaction: discord.Interaction[NecroBot], button: discord.ui.Button):
        await interaction.response.defer()

    @discord.ui.button(label="Confirm", row=1, style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction[NecroBot], button: discord.ui.Button):
        if not self.thread_select.values:
            return await interaction.response.send_message(
                f"{NEGATIVE_CHECK} | Please select a thread first", ephemeral=True
            )

        await self.message.add_reaction("\N{GEAR}")
        await self.message.add_reaction("\N{SLEEPING SYMBOL}")

        post = {
            "approver": interaction.user.id,
            "url": bug_mapping[self.thread_select.values[0]]["url"],
            "message": self.message,
            "content": self.content,
        }

        await interaction.client.queued_posts.put(post)
        await interaction.response.edit_message(content=f"{POSITIVE_CHECK} | Post queued", view=None)


@discord.app_commands.context_menu(name="Send message as bug report")
@discord.app_commands.guilds(*testing_or(327175434754326539))
async def send_bug_report(interaction: discord.Interaction[NecroBot], message: discord.Message):
    if interaction.user.id != 241942232867799040:  # that's me, only I can authorize posts
        return await interaction.response.send_message(
            f"{NEGATIVE_CHECK} | This button is not for you", ephemeral=True
        )

    await interaction.response.send_message(
        "Which thread would you like to send it to?", ephemeral=True, view=BridgeView(message)
    )


class Bridge(commands.Cog):
    """A cog for all commands specific to certain servers."""

    def __init__(self, bot: NecroBot):
        self.bot = bot
        self.cookies = False

    #######################################################################
    ## Cog Functions
    #######################################################################
    async def cog_load(self):
        self.task = self.bot.loop.create_task(self.post_task())

    async def cog_unload(self):
        self.task.cancel()

    #######################################################################
    ## Functions
    #######################################################################

    async def post_task(self):
        await self.bot.wait_until_loaded()

        while True:
            post = await self.bot.queued_posts.get()
            try:
                await post["message"].remove_reaction("\N{SLEEPING SYMBOL}", post["message"].guild.me)
                await self.mu_poster(post)
                await asyncio.sleep(120)
            except Exception as e:
                error_traceback = " ".join(
                    traceback.format_exception(type(e), e, e.__traceback__, chain=True)
                )
                logger.error(error_traceback)

                await post["message"].channel.send(f"{NEGATIVE_CHECK} | Error while sending: {e}")
                await post["message"].remove_reaction("\N{GEAR}", post["message"].guild.me)

    async def get_form(self, url, form_name):
        async with self.bot.session.get(url) as resp:
            soup = BeautifulSoup(await resp.read(), "html.parser")

        form = soup.find("form", {"name": form_name})
        if form is not None:
            return Form(form)

    async def submit_form(self, form: Form, submit=None, **kwargs):
        method = form.method.upper()

        url = form.action
        payload = form.serialize(submit=submit)
        serialized = payload.to_requests(method)
        kwargs.update(serialized)

        return await self.bot.session.request(method, url, **kwargs)

    async def new_cookies(self):
        url = "https://modding-union.com/index.php?action=login"
        form = await self.get_form(url, "frmLogin")

        form["user"].value = MU_Username
        form["passwrd"].value = MU_Password
        form["cookielength"].value = "-1"

        await self.submit_form(form)
        self.cookies = True

    async def mu_poster(self, pending: QueuedPosts, retry=0):
        if pending is None:
            return

        if not self.cookies:
            await self.new_cookies()

        form = await self.get_form(pending["url"], "postmodify")
        if form is None:
            await self.new_cookies()
            if retry < 3:
                await self.mu_poster(pending, retry + 1)
            else:
                raise ValueError(f"Retried three times, unable to get form for {pending['message'].id}")

        content = pending["content"]
        author = pending["message"].author
        form["message"].value = f"{content} \n[hr]\n {author} ({author.mention})"

        del form.fields["preview"]

        if pending["message"].channel.id == TEST_CHANNEL:
            await self.bot.bot_channel.send(f"Payload sent. {form.serialize().data}")  # dud debug test
        else:
            await self.submit_form(form)  # actual submit

        await pending["message"].delete()


async def setup(bot: NecroBot):
    await bot.add_cog(Bridge(bot))

    bot.tree.add_command(send_bug_report)
