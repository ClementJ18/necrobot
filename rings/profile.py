from __future__ import annotations

import functools
import random
from io import BytesIO
from typing import TYPE_CHECKING, Annotated, Dict, List, Union

import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
from PIL import Image, ImageDraw, ImageFont

from rings.utils.checks import has_perms
from rings.utils.converters import BadgeConverter, MemberConverter, MoneyConverter, RangeConverter
from rings.utils.ui import Confirm, Paginator
from rings.utils.utils import POSITIVE_CHECK, BotError, DatabaseError, midnight

if TYPE_CHECKING:
    from bot import NecroBot


class Profile(commands.Cog):
    """See everything there is to know about your NecroBot profile. From your balance to badges \
    or info. Can also be used to shift money around.    
    """
    def __init__(self, bot: NecroBot):
        self.bot = bot
        self.font17 = ImageFont.truetype("rings/utils/profile/fonts/Ringbearer Medium.ttf", 17)
        self.font20 = ImageFont.truetype("rings/utils/profile/fonts/Ringbearer Medium.ttf", 20)
        self.font21 = ImageFont.truetype("rings/utils/profile/fonts/Ringbearer Medium.ttf", 21)
        self.font30 = ImageFont.truetype("rings/utils/profile/fonts/Ringbearer Medium.ttf", 30)
        self.overlay = Image.open("rings/utils/profile/overlay.png").convert("RGBA")
        self.badges_coords = [
            (580, 295, 680, 395),
            (685, 295, 785, 395),
            (790, 295, 890, 395),
            (895, 295, 995, 395),
            (580, 400, 680, 500),
            (685, 400, 785, 500),
            (790, 400, 890, 500),
            (895, 400, 995, 500),
        ]

    #######################################################################
    ## Commands
    #######################################################################

    @commands.group(invoke_without_command=True)
    async def balance(
        self,
        ctx: commands.Context[NecroBot],
        *,
        user: Annotated[discord.Member, MemberConverter] = commands.Author,
    ):
        """Prints the given user's NecroBot balance, if no user is supplied then it will print your own NecroBot balance.

        {usage}

        __Example__
        `{pre}balance @NecroBot` - prints NecroBot's balance
        `{pre}balance` - prints your own balance"""
        if user != ctx.author:
            money = await self.bot.db.get_money(user.id)
            await ctx.send(f":atm: | **{user.display_name}** has **{'{:,}'.format(money)}** :euro:")
        else:
            money = await self.bot.db.get_money(ctx.author.id)
            await ctx.send(
                f":atm: | **{ctx.author.display_name}** you have **{'{:,}'.format(money)}** :euro:"
            )

    async def money_ranking(self, ctx: commands.Context[NecroBot], entries: List[int], server: bool):
        description = (
            "Ranking of user's money on the server"
            if server
            else "Ranking of user's money throughout Discord"
        )

        def embed_maker(view: Paginator, entries: List[Dict[str, str]]):
            embed = discord.Embed(
                title=f"Money Ranking ({view.page_string})",
                colour=self.bot.bot_color,
                description=description,
            )

            embed.set_footer(**self.bot.bot_footer)

            for user in entries:
                embed.add_field(
                    name=f"{entries.index(user)+1}. {ctx.guild.get_member(user[0]).display_name}",
                    value=user[1],
                    inline=False,
                )

            return embed

        await Paginator(10, entries, ctx.author, embed_maker=embed_maker).start(ctx)

    @balance.command(name="server")
    async def balance_server(self, ctx: commands.Context[NecroBot]):
        """See the ranking of users with the most money within the server

        {usage}

        __Example__
        `{pre}balance server` - See the ranking starting from the top 10
        """
        monies = await self.bot.db.query(
            "SELECT user_id, necroins FROM necrobot.Users WHERE user_id = any($1) ORDER BY necroins DESC",
            [x.id for x in ctx.guild.members],
        )

        await self.money_ranking(ctx, monies, True)

    @balance.command(name="global")
    async def balance_global(self, ctx: commands.Context[NecroBot]):
        """See the ranking of users with the most money throughout discord

        {usage}

        __Example__
        `{pre}balance server` - See the ranking starting from the top 10
        """
        monies = await self.bot.db.query(
            "SELECT user_id, necroins FROM necrobot.Users WHERE user_id = ANY($1) ORDER BY necroins DESC",
            [x.id for x in self.bot.users],
        )

        await self.money_ranking(ctx, monies, False)

    @commands.command(name="daily", cooldown_after_parsing=True)
    @commands.cooldown(1, 60, BucketType.user)
    async def daily(
        self,
        ctx: commands.Context[NecroBot],
        *,
        member: Annotated[discord.Member, MemberConverter] = commands.Author,
    ):
        """Adds your daily 200 :euro: to your NecroBot balance. This can be used at anytime once every GMT day. Can \
        also be gifted to a user for some extra cash.

        {usage}

        __Example__
        `{pre}daily` - claim your daily for 200 Necroins
        `{pre}daily @NecroBot` - give your daily to Necrobot and they will received 200 + a random bonus

        """
        day = await self.bot.db.query(
            "UPDATE necrobot.Users SET daily = current_date WHERE user_id = $1 AND daily != current_date RETURNING user_id",
            ctx.author.id,
        )

        if not day:
            hours, remainder = divmod(midnight().total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            raise BotError(
                f"You have already claimed your daily today. You can claim it again in **{int(hours)} hours, {int(minutes)} minutes and {int(seconds)} seconds**"
            )

        if member.id == ctx.author.id:
            amount = 200
            message = "You have received your daily **200** :euro:"
        else:
            amount = random.choice(range(235, 450))
            message = f"{member.mention}, **{ctx.author.display_name}** has given you their daily of **{amount}** :euro:"

        await self.bot.db.update_money(member.id, add=amount)
        await ctx.send(f":m: | {message}")

    @commands.command()
    async def pay(
        self,
        ctx: commands.Context[NecroBot],
        payee: Annotated[discord.Member, MemberConverter],
        amount: MoneyConverter,
    ):
        """Transfers the given amount of money to the given user's NecroBot bank account.

        {usage}

        __Example__
        `{pre}pay @NecroBot 200` - pays NecroBot 200 :euro:"""
        payer = ctx.author
        view = Confirm(
            ctx.author,
            confirm_msg=f"{POSITIVE_CHECK} | **{payer.display_name}** approved the transaction.",
            cancel_msg=f"{POSITIVE_CHECK} | **{payer.display_name}** cancelled the transaction.",
        )

        view.message = await ctx.send(
            f"Are you sure you want to pay **{amount}** to user **{payee.display_name}**?",
            view=view,
        )
        await view.wait()
        if not view.value:
            return

        try:
            await self.bot.db.transfer_money(payer.id, amount, payee.id)
        except DatabaseError as e:
            raise BotError("You no longer have enough money") from e

        try:
            await payee.send(f":m: | **{payer.display_name}** has transferred **{amount}$** to your profile")
        except (discord.Forbidden, discord.HTTPException, AttributeError):
            pass

    @commands.command()
    @commands.guild_only()
    async def info(
        self,
        ctx: commands.Context[NecroBot],
        *,
        user: Annotated[discord.Member, MemberConverter] = commands.Author,
    ):
        """Returns a rich embed of the given user's info. If no user is provided it will return your own info.

        {usage}

        __Example__
        `{pre}info @NecroBot` - returns the NecroBot info for NecroBot
        `{pre}info` - returns your own NecroBot info"""
        embed = discord.Embed(
            title=user.display_name,
            colour=self.bot.bot_color,
            description=f"**Title**: {await self.bot.db.get_title(user.id)}",
        )

        embed.set_thumbnail(url=user.display_avatar.replace(format="png", size=256))
        embed.set_footer(**self.bot.bot_footer)

        embed.add_field(name="User Name", value=str(user))
        embed.add_field(name="Top Role", value=user.top_role.name, inline=True)

        embed.add_field(
            name="Permission Level",
            value=await self.bot.db.get_permission(user.id, ctx.guild.id),
            inline=False,
        )

        embed.add_field(name="Date Created", value=user.created_at.strftime("%d - %B - %Y %H:%M"))
        embed.add_field(name="Date Joined", value=user.joined_at.strftime("%d - %B - %Y %H:%M"))

        badges = await self.bot.db.get_badges(user.id)
        string = " - ".join([x["name"] for x in badges])
        embed.add_field(name="Badges", value=string if string else "None", inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def profile(
        self,
        ctx: commands.Context[NecroBot],
        *,
        user: Annotated[discord.Member, MemberConverter] = commands.Author,
    ):
        """Shows your profile information in a picture

        {usage}

        __Example__
        `{pre}info @NecroBot` - returns the NecroBot info for NecroBot
        `{pre}info` - returns your own NecroBot info"""

        def profile_maker():
            im = (
                Image.open(f"rings/utils/profile/backgrounds/{random.randint(1,22)}.jpg")
                .resize((1024, 512))
                .convert("RGBA")
            )
            draw = ImageDraw.Draw(im)

            pfp = Image.open(BytesIO(image_bytes)).resize((170, 170)).convert("RGBA")
            perms_level = (
                Image.open(f"rings/utils/profile/perms_level/{level}.png").resize((50, 50)).convert("RGBA")
            )

            im.paste(self.overlay, box=(0, 0, 1024, 512), mask=self.overlay)
            im.paste(pfp, box=(83, 147, 253, 317), mask=pfp)
            im.paste(perms_level, box=(143, 30, 193, 80))

            for badge, spot in badges:
                badge_img = (
                    Image.open(f"rings/utils/profile/badges/{badge}").resize((100, 100)).convert("RGBA")
                )
                index = spot - 1
                im.paste(badge_img, box=self.badges_coords[index], mask=badge_img)

            draw.text((83, 97), self.bot.perms_name[level], (0, 0, 0), font=self.font20)
            draw.text((300, 145), "{:,}$".format(money), (0, 0, 0), font=self.font30)
            draw.text((50, 355), user.display_name, (0, 0, 0), font=self.font21)
            draw.text((50, 405), title, (0, 0, 0), font=self.font21)

            output_buffer = BytesIO()
            im.save(output_buffer, "png")
            output_buffer.seek(0)
            ifile = discord.File(output_buffer, filename=f"{user.id}.png")

            return ifile

        async with ctx.channel.typing():
            image_bytes = await user.display_avatar.replace(format="png").read()
            money = await self.bot.db.get_money(user.id)
            level = await self.bot.db.get_permission(user.id, ctx.guild.id)
            title = await self.bot.db.get_title(user.id)

            badges = await self.bot.db.query(
                """SELECT s.file_name, b.spot FROM necrobot.Badges b, necrobot.BadgeShop s
                WHERE b.user_id = $1 AND s.name = b.badge AND spot > 0
                ORDER BY spot""",
                user.id,
            )

            syncer = functools.partial(profile_maker)
            ifile = await self.bot.loop.run_in_executor(None, syncer)

            await ctx.send(file=ifile)

    @commands.command()
    async def title(self, ctx: commands.Context[NecroBot], *, text: str = ""):
        """Sets your NecroBot title to [text]. If no text is provided it will reset it. Limited to max 32 characters.

        {usage}

        __Example__
        `{pre}title Cool Dood` - set your title to 'Cool Dood'
        `{pre}title` - resets your title"""
        if len(text) > 32:
            raise BotError(
                "You have gone over the 32 character limit, your title wasn't set. ({len(text)}/32)"
            )

        await self.bot.db.update_title(ctx.author.id, text)
        if text == "":
            await ctx.send(f"{POSITIVE_CHECK} | Your title has been reset")
        else:
            await ctx.send(f"{POSITIVE_CHECK} | Great, your title is now **{text}**")

    @commands.group(aliases=["badge"], invoke_without_command=True)
    async def badges(self, ctx: commands.Context[NecroBot]):
        """The badge system allows you to buy badges and place them on profiles. Show the world what your favorite \
        games/movies/books/things are. You can see all the badges from the badge shop.

        {usage}

        __Examples__
        `{pre}badges` - lists your badges and a link to the list of all badges"""
        badges = await self.bot.db.get_badges(ctx.author.id)
        string = " - ".join([x["name"] for x in badges])
        await ctx.send(f"__Badges__\n{string if string else 'None'}")

    @badges.command(name="place")
    async def badges_place(
        self,
        ctx: commands.Context[NecroBot],
        spot: RangeConverter(1, 8),
        badge: BadgeConverter = None,
    ):
        """Opens the grid menu to allow you to place a badge or reset a badge. Simply supply a badge name to the command to \
        place a badge or supply "none" to reset the grid location.

        {usage}

        __Examples__
        `{pre}badges place 4 edain` - instantly place the edain badge on the 4th spot
        `{pre}badles place 2` - instanty reset the 2th badge place
        """
        if badge is None:
            await self.bot.db.update_spot_badge(ctx.author.id, spot)
            await ctx.send(f"{POSITIVE_CHECK} | Reset spot {spot}")
        else:
            badge = await self.bot.db.get_badges(ctx.author.id, badge=badge["name"])
            if not badge:
                raise BotError("You do not posses this badge")

            badge = badge[0]
            await self.bot.db.update_spot_badge(ctx.author.id, spot, badge["name"])
            await ctx.send(f"{POSITIVE_CHECK} | **{badge['name']}** set on spot **{spot}**")

    @badges.command(name="buy")
    async def badges_buy(
        self,
        ctx: commands.Context[NecroBot],
        badge: BadgeConverter,
        spot: RangeConverter(1, 8) = 0,
    ):
        """Allows to buy the given badge and place it on a specific spot

        {usage}

        __Examples__
        `{pre}badges buy edain` - buy the edain badge, price will appear once you run the command
        `{pre}badges buy edain 3` - buy the edain badge and place it on spot 3
        """
        has_badge = await self.bot.db.get_badges(ctx.author.id, badge=badge["name"])
        if has_badge:
            raise BotError("You already posses this badge")

        if badge["special"]:
            raise BotError("You cannot buy this badge")

        await self.bot.db.update_money(ctx.author.id, add=-badge["cost"])
        await self.bot.db.insert_badge(ctx.author.id, badge["name"], spot)

        if spot:
            await ctx.send(
                f"{POSITIVE_CHECK} | Bought badge **{badge['name']}** and placed it on spot **{spot}**"
            )
        else:
            await ctx.send(f"{POSITIVE_CHECK} | Bought badge **{badge['name']}**")

    @badges.group(name="shop", invoke_without_command=True)
    async def badge_shop(self, ctx: commands.Context[NecroBot]):
        """Open the badge show to browse and preview all the badges. To buy a badge simply pass the name \
        to `{pre}badge buy`.

        {usage}
        """

        def embed_maker(view: Paginator, entry: Dict[str, str]):
            embed = discord.Embed(
                title=f"Badge Shop ({view.page_string})",
                description="Here you can browse available badges at your leisure. To buy a badge use the `badge buy` command and pass the name of the badge",
            )

            embed.set_image(url=entry)

            return embed

        await Paginator(1, self.bot.settings["shop"], ctx.author, embed_maker=embed_maker).start(ctx)

    @badge_shop.command(name="generate")
    @has_perms(6)
    async def badge_shop_generate(self, ctx: commands.Context[NecroBot]):
        """Generate images used by the bage shop react menu, needs to be updated every so often.

        {usage}
        """
        badges = await self.bot.db.query(
            "SELECT * FROM necrobot.BadgeShop ORDER BY cost = 0 nulls last, cost"
        )

        def draw_centered_text(draw, text, W, H, font):
            w, h = font.getsize(text)
            draw.text((W - (w / 2), H - (h / 2)), text, (0, 0, 0), font=font)

        def image_maker(entries):
            im = Image.open("rings/utils/profile/badge_shop.png").convert("RGBA")
            draw = ImageDraw.Draw(im)

            counter = 0
            for entry in entries:
                W_modif = 183 * (counter % 3)
                H_modif = 183 * (counter // 3)

                badge = Image.open(f"rings/utils/profile/badges/{entry['file_name']}").resize((101, 101))
                im.paste(badge, (41 + W_modif, 43 + H_modif), mask=badge)

                draw_centered_text(draw, entry["name"], 91 + W_modif, 29 + H_modif, self.font20)

                price = "Special" if entry["special"] else "{:,}$".format(entry["cost"])
                font = self.font17 if entry["special"] else self.font20
                draw_centered_text(draw, price, 91 + W_modif, 153 + H_modif, font)

                counter += 1

            output_buffer = BytesIO()
            im.save(output_buffer, "png")
            output_buffer.seek(0)
            ifile = discord.File(output_buffer, filename=f"{ctx.author.id}.png")

            return ifile

        def image_getter():
            files = []
            for section in [badges[i : i + 9] for i in range(0, len(badges), 9)]:
                files.append(image_maker(section))

            return files

        async with ctx.channel.typing():
            syncer = functools.partial(image_getter)
            files = await self.bot.loop.run_in_executor(None, syncer)

        urls = []
        for file in files:
            msg = await ctx.send(file=file)
            urls.append(msg.attachments[0].url)

        self.bot.settings["shop"] = urls
        await ctx.send(f"{POSITIVE_CHECK} | Done generating and updating")

    @commands.group(invoke_without_command=True, aliases=["star"])
    async def stars(
        self,
        ctx: commands.Context[NecroBot],
        user: Union[MemberConverter, str] = None,
        key: str = "date",
    ):
        """
        See all the starred messages of a user or all the ones on the server. Order by most recent first, \
        can change order with keywords:
            - stars : order by highest star

        {usage}

        __Examples__
        `{pre}starboard stars @Necrobot`
        """
        mapping = {"stars": "stars", "date": "starred_id"}
        if isinstance(user, discord.Member):
            order = mapping.get(key, "starred_id")
            stars = await self.bot.db.query(
                f"SELECT user_id, stars, link FROM necrobot.Starred WHERE guild_id = $1 AND user_id = $2 AND link != 'None' ORDER BY {order} DESC",
                ctx.guild.id,
                user.id,
            )
        else:
            order = mapping.get(user, "starred_id")
            stars = await self.bot.db.query(
                f"SELECT user_id, stars, link FROM necrobot.Starred WHERE guild_id = $1 AND link != 'None' ORDER BY {order} DESC",
                ctx.guild.id,
            )

        total_stars = sum([x[1] for x in stars])

        def embed_maker(view: Paginator, entries: List[Dict[str, str]]):
            star_str = "\n".join(
                [
                    f"{x[1]} :star: - [Link]({x[2]}) ({ctx.guild.get_member(x[0]) if ctx.guild.get_member(x[0]) is not None else 'User Left'})"
                    for x in entries
                ]
            )
            embed = discord.Embed(
                title=f"Stars ({view.page_string})",
                description=f"Total Stars: {total_stars} \n Total Message: {len(stars)} \n {star_str}",
                colour=self.bot.bot_color,
            )

            embed.set_footer(**self.bot.bot_footer)

            return embed

        await Paginator(15, stars, ctx.author, embed_maker=embed_maker).start(ctx)

    @stars.group(invoke_without_command=True, name="ranking")
    async def stars_ranking(self, ctx: commands.Context[NecroBot], order: str = "messages"):
        """Server ranking for amount of starred messages and amount of stars. By default \
        ordered by number of starred message, other order keywords can be passed to change this:
            - stars : order users based on their number of stars descending

        """
        mapping = {"messages": "COUNT(message_id)", "stars": "SUM(stars)"}
        order = mapping.get(order, "COUNT(message_id)")

        results = await self.bot.db.query(
            f"""SELECT user_id, COUNT(message_id), SUM(stars) FROM necrobot.Starred 
            WHERE guild_id = $1 AND user_id IS NOT null AND link != 'None'
            GROUP BY user_id 
            ORDER BY {order} DESC""",
            ctx.guild.id,
        )

        def embed_maker(view: Paginator, entries: List[Dict[str, str]]):
            description = ""
            for row in entries:
                member = ctx.guild.get_member(row[0])
                description += f"- {member.mention if member else 'User Left'}: {row[1]} starred messages ({row[2]} :star:) \n"

            embed = discord.Embed(
                title=f"Starboard Leaderboard ({view.page_string})",
                description=f"A leaderboard to rank people by the amount of their messages that were starred. \n {description}",
                colour=self.bot.bot_color,
            )
            embed.set_footer(**self.bot.bot_footer)
            return embed

        await Paginator(15, results, ctx.author, embed_maker=embed_maker).start(ctx)

    @stars_ranking.command(name="old")
    async def stars_ranking_old(self, ctx: commands.Context[NecroBot]):
        """This command will soon be deprecated

        {usage}
        """
        results = await self.bot.db.query(
            """SELECT user_id, COUNT(message_id) FROM necrobot.Starred 
            WHERE guild_id = $1 AND user_id IS NOT null 
            GROUP BY user_id 
            ORDER BY COUNT(message_id) DESC""",
            ctx.guild.id,
        )

        def embed_maker(view: Paginator, entries: List[Dict[str, str]]):
            description = ""
            for row in entries:
                member = ctx.guild.get_member(row[0])
                description += f"- {member.mention if member else 'User Left'}: {row[1]} starred messages \n"

            embed = discord.Embed(
                title=f"Starboard Leaderboard ({view.page_string})",
                description=f":warning: **This command is deprecated and will be removed soon**. :warning:\nA leaderboard to rank people by the amount of their messages that were starred. \n {description}",
                colour=self.bot.bot_color,
            )
            embed.set_footer(**self.bot.bot_footer)
            return embed

        await Paginator(15, results, ctx.author, embed_maker=embed_maker).start(ctx)


async def setup(bot: NecroBot):
    await bot.add_cog(Profile(bot))
