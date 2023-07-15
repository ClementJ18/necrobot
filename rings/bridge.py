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

if TYPE_CHECKING:
    from bot import NecroBot


class Bridge(commands.Cog):
    """A cog for all commands specific to certain servers."""

    def __init__(self, bot: NecroBot):
        self.bot = bot
        self.TEST_CHANNEL = 722040731946057789
        self.mu_channels = (self.TEST_CHANNEL, 722474242762997868)
        self.cookies = False
        self.in_process = []
        self.mapping = {
            "angmar": {
                "id": 687748138345169075,
                "url": "https://modding-union.com/index.php/topic,33016.0.html",
            },
            "erebor": {
                "id": 687748357543952417,
                "url": "https://modding-union.com/index.php/topic,31202.0.html",
            },
            "gondor": {
                "id": 687747730684117012,
                "url": "https://modding-union.com/index.php/topic,30434.0.html",
            },
            "imladris": {
                "id": 687748566105849890,
                "url": "https://modding-union.com/index.php/topic,33678.0.html",
            },
            "isengard": {
                "id": 687748680182530086,
                "url": "https://modding-union.com/index.php/topic,30436.0.html",
            },
            "lothlorien": {
                "id": 687748760054661152,
                "url": "https://modding-union.com/index.php/topic,32089.0.html",
            },
            "mm": {
                "id": 688040356184588423,
                "url": "https://modding-union.com/index.php/topic,36986.0.html",
            },
            "mordor": {
                "id": 687749364692549651,
                "url": "https://modding-union.com/index.php/topic,30433.0.html",
            },
            "rohan": {
                "id": 687747731716177930,
                "url": "https://modding-union.com/index.php/topic,30435.0.html",
            },
            "eothain": {
                "id": 361473129253568513,
                "url": "https://modding-union.com/index.php/topic,30438.0.html",
            },  # CAH
            "onering": {
                "id": 342033729637711872,
                "url": "https://modding-union.com/index.php/topic,30437.0.html",
            },  # WotR
            "LUL": {
                "id": 778021945685704724,
                "url": "https://modding-union.com/index.php/topic,31224.0.html",
            },  # Audio
            "mu": {
                "id": 733692917318942801,
                "url": "https://modding-union.com/index.php/topic,35939.0.html",
            },  # Horde Maps
            "edain": {
                "id": 339025957136629772,
                "url": "https://modding-union.com/index.php/topic,33017.0.html",
            },  # General
            "dwarf_f": {
                "id": 778019875120742400,
                "url": "https://modding-union.com/index.php/topic,30440.0.html",
            },  # Maps
            "gildor": {
                "id": 340577178192445441,
                "url": "https://modding-union.com/index.php/topic,30439.0.html",
            },  # AI
        }

        self.test_mapping = {
            "delthis": {
                "id": 778027866142146570,
                "url": "https://modding-union.com/index.php/topic,30439.0.html",
            }  # test
        }

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
        await self.bot.wait_until_ready()

        while True:
            post = await self.bot.queued_posts.get()
            try:
                await post["message"].remove_reaction(
                    "\N{SLEEPING SYMBOL}", post["message"].guild.me
                )
                await self.mu_poster(post)
                await asyncio.sleep(120)
            except Exception as e:
                error_traceback = " ".join(
                    traceback.format_exception(type(e), e, e.__traceback__, chain=True)
                )
                logging.error(error_traceback)

                await post["message"].channel.send(
                    f":negative_squared_cross_mark: | Error while sending: {e}"
                )
                self.bot.pending_posts[post["message"].id] = post
                await post["message"].remove_reaction("\N{GEAR}", post["message"].guild.me)

    async def get_form(self, url, form_name):
        async with self.bot.session.get(url) as resp:
            soup = BeautifulSoup(await resp.read(), "html.parser")

        form = soup.find("form", {"name": form_name})
        if form is not None:
            return Form(form)

    async def submit_form(self, form, submit=None, **kwargs):
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

    async def mu_poster(self, pending, retry=0):
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
                raise ValueError(
                    f"Retried three times, unable to get form for {pending['message'].id}"
                )

        content = pending["content"]
        author = pending["message"].author
        form["message"].value = f"{content} \n[hr]\n {author} ({author.mention})"

        del form.fields["preview"]

        if pending["message"].channel.id == self.TEST_CHANNEL:
            await self.bot.get_bot_channel().send(
                f"Payload sent. {form.serialize().data}"
            )  # dud debug test
        else:
            await self.submit_form(form)  # actual submit

        ids = [pending["message"].id] + [x.id for x in pending["replies"]]
        await pending["message"].channel.purge(limit=100, check=lambda m: m.id in ids)

    #######################################################################
    ## Events
    #######################################################################

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        if payload.message_id in self.bot.pending_posts:
            self.bot.pending_posts[payload.message_id]["message"]._update(payload.data)
            self.bot.pending_posts[payload.message_id]["content"] = self.bot.pending_posts[
                payload.message_id
            ]["message"].content

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        if payload.message_id in self.bot.pending_posts:
            del self.bot.pending_posts[payload.message_id]

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id not in self.mu_channels:
            return

        if message.author.bot:
            return

        # registered = await self.bot.db.query(
        #     "SELECT active FROM necrobot.MU_Users WHERE user_id=$1",
        #     message.author.id, fetchval=True
        # )

        if message.reference:
            if message.reference.message_id in self.bot.pending_posts:
                self.bot.pending_posts[message.reference.message_id]["replies"].append(message)
                return

        perms = await self.bot.db.get_permission(message.author.id, message.guild.id)
        if perms > 0 and message.channel.id != self.TEST_CHANNEL:
            return

        self.bot.pending_posts[message.id] = {
            "message": message,
            "content": message.content,
            "replies": [],
        }

        for reaction, value in self.mapping.items():
            try:
                await message.add_reaction(f"{reaction}:{value['id']}")
            except discord.HTTPException:
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if self.bot.blacklist_check(payload.user_id):
            return

        if not payload.channel_id in self.mu_channels:
            return

        if not payload.message_id in self.bot.pending_posts:
            return

        if not payload.user_id == 241942232867799040:  # that's me, only I can authorize posts
            return

        if not payload.emoji.name in self.mapping and (
            not payload.emoji.name in self.test_mapping and payload.channel_id == self.TEST_CHANNEL
        ):
            return

        post = self.bot.pending_posts.pop(payload.message_id)
        await post["message"].clear_reactions()
        await post["message"].add_reaction("\N{GEAR}")
        await post["message"].add_reaction("\N{SLEEPING SYMBOL}")
        post["approver"] = payload.user_id
        post["url"] = (
            self.mapping[payload.emoji.name]["url"]
            if payload.emoji.name in self.mapping
            else self.test_mapping[payload.emoji.name]["url"]
        )
        await self.bot.queued_posts.put(post)


async def setup(bot):
    await bot.add_cog(Bridge(bot))
