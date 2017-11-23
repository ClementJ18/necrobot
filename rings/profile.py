#!/usr/bin/python3.6
import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

from rings.botdata.data import Data
from simpleeval import simple_eval
import datetime as d
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw 
from PIL import ImageColor 
import os
import aiohttp
import random
from rings.botdata.utils import userData, serverData


#Permissions Names
permsName = ["User","Helper","Moderator","Semi-Admin","Admin","Server Owner","NecroBot Admin","The Bot Smith"]

class Profile():
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context = True)
    @commands.cooldown(3, 10, BucketType.user)
    async def balance(self, cont, *user : discord.Member ):
        """Prints the given user's NecroBot balance, if no user is supplied then it will print your own NecroBot balance.
        
        {usage}
        
        __Example__
        `{pre}balance @NecroBot` - prints NecroBot's balance
        `{pre}balance` - prints your own balance"""
        if user:
            user = user[0]
            await self.bot.say(":atm: | **"+ str(user.name) +"** has **{:,}** :euro:".format(userData[user.id]["money"]))
        else:
            await self.bot.say(":atm: | **"+ str(cont.message.author.name) +"** you have **{:,}** :euro:".format(userData[cont.message.author.id]["money"]))

    @commands.command(pass_context = True, aliases=["daily"])
    @commands.cooldown(1, 5, BucketType.user)
    async def claim(self, cont):
        """Adds your daily 200 :euro: to your NecroBot balance. This can be used at anytime once every GMT day.
        
        {usage}"""
        aDay = str(d.datetime.today().date())
        if aDay != userData[cont.message.author.id]["daily"]:
            await self.bot.say(":m: | You have received your daily **200** :euro:")
            userData[cont.message.author.id]["money"] += 200
            userData[cont.message.author.id]["daily"] = aDay
        else:
            await self.bot.say(":negative_squared_cross_mark: | You have already claimed your daily today, come back tomorrow.")

    @commands.command(pass_context = True)
    async def pay(self, cont, user : discord.User, amount : int):
        """Transfers the given amount of money to the given user's NecroBot bank account.

        {usage}

        __Example__
        `{pre}pay @NecroBot 200` - pays NecroBot 200 :euro:"""
        amount = abs(amount)
        payer = cont.message.author
        payee = user
        if userData[payer.id]["money"] < amount:
            await self.bot.say(":negative_squared_cross_mark: | You don't have enough money")
            return

        msg = await self.bot.say("Are you sure you want to pay **{}** to user **{}**? Press :white_check_mark: to confirm transaction. Press :negative_squared_cross_mark: to cancel the transaction.".format(amount, payee.display_name))
        await self.bot.add_reaction(msg, "\N{WHITE HEAVY CHECK MARK}")
        await self.bot.add_reaction(msg, "\N{NEGATIVE SQUARED CROSS MARK}")
        res = await self.bot.wait_for_reaction(["\N{WHITE HEAVY CHECK MARK}", "\N{NEGATIVE SQUARED CROSS MARK}"], user=payer, message=msg)

        if res.reaction.emoji == "\N{NEGATIVE SQUARED CROSS MARK}":
            await self.bot.say(":white_check_mark: | **{}** cancelled the transaction.".format(payer.display_name))
        elif res.reaction.emoji == "\N{WHITE HEAVY CHECK MARK}":
            if userData[payer.id]["money"] < amount:
                await self.bot.say(":negative_squared_cross_mark: | You don't have enough money")
                await self.bot.delete_message(msg)
                return
            await self.bot.say(":white_check_mark: | **{}** approved the transaction.".format(payer.display_name))
            userData[payer.id]["money"] -= amount
            userData[payee.id]["money"] += amount
            
        await self.bot.delete_message(msg)


    @commands.command(pass_context = True)
    @commands.cooldown(3, 5, BucketType.user)
    async def info(self, cont, *user : discord.Member):
        """Returns a rich embed of the given user's info. If no user is provided it will return your own info. **WIP**
        
        {usage}
        
        __Example__
        `{pre}info @NecroBot` - returns the NecroBot info for NecroBot
        `{pre}info` - returns your own NecroBot info"""
        if user:
            user = user[0]
        else:
            user = cont.message.author

        serverID = cont.message.server.id
        embed = discord.Embed(title="__**" + user.display_name + "**__", colour=discord.Colour(0x277b0), description="**Title**: " + userData[user.id]["title"])
        embed.set_thumbnail(url=user.avatar_url.replace("webp","jpg"))
        embed.set_footer(text="Generated by NecroBot", icon_url="https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128")

        embed.add_field(name="**Date Created**", value=user.created_at.strftime("%d - %B - %Y %H:%M"))
        embed.add_field(name="**Date Joined**", value=user.joined_at.strftime("%d - %B - %Y %H:%M"), inline=True)

        embed.add_field(name="**User Name**", value=user.name + "#" + user.discriminator)
        embed.add_field(name="**Top Role**", value=user.top_role.name, inline=True)
        embed.add_field(name="Warning List", value=userData[user.id]["warnings"])

        await self.bot.say(embed=embed)

    @commands.command(pass_context = True)
    async def profile(self, cont, *user : discord.Member):
        """Shows your profile information in a picture

        {usage}
            
        __Example__
        `{pre}info @NecroBot` - returns the NecroBot info for NecroBot
        `{pre}info` - returns your own NecroBot info"""
        if user:
            user = user[0]
        else:
            user = cont.message.author

        url = user.avatar_url.replace("webp","jpg").replace("?size=1024","")
        async with aiohttp.ClientSession() as cs:
            async with cs.get(url) as r:
                filename = os.path.basename(url)
                with open(filename, 'wb') as f_handle:
                    while True:
                        chunk = await r.content.read(1024)
                        if not chunk:
                            break
                        f_handle.write(chunk)
                await r.release()

        im = Image.open("rings/botdata/profile/backgrounds/{}.jpg".format(random.randint(1,139))).resize((1024,512)).crop((59,29,964,482))
        draw = ImageDraw.Draw(im)

        pfp = Image.open(filename).resize((150,150))
        overlay = Image.open("rings/botdata/profile/overlay.png")
        perms_level = Image.open("rings/botdata/profile/perms_level/{}.png".format(userData[user.id]["perms"][cont.message.server.id])).resize((50,50))
        line = Image.open("rings/botdata/profile/underline.png").resize((235,30))

        im.paste(overlay, box=(0, 0, 905, 453), mask=overlay)
        im.paste(pfp, box=(75, 132, 225, 282))
        im.paste(perms_level, box=(125, 25, 175, 75))

        font20 = ImageFont.truetype("Ringbearer Medium.ttf", 20)
        font21 = ImageFont.truetype("Ringbearer Medium.ttf", 21)
        font30 = ImageFont.truetype("Ringbearer Medium.ttf", 30)

        draw.text((70,85), permsName[userData[user.id]["perms"][cont.message.server.id]], (0,0,0), font=font20)
        draw.text((260,125), "{:,}$".format(userData[user.id]["money"]), (0,0,0), font=font30)
        draw.text((260,230), "{:,} EXP".format(userData[user.id]["exp"]), (0,0,0), font=font30)
        draw.text((43,313), user.display_name, (0,0,0), font=font21)
        draw.text((43,356), userData[user.id]["title"], (0,0,0), font=font21)
        draw.line((52,346,468,346),fill=(0,0,0), width=2)

        im.save('{}.png'.format(user.id))
        await self.bot.upload('{}.png'.format(user.id))
        os.remove("{}.png".format(user.id))
        os.remove(filename)

    @commands.command(pass_context = True)
    @commands.cooldown(3, 5, BucketType.user)
    async def settitle(self, cont, *, text : str = ""):
        """Sets your NecroBot title to [text]. If no text is provided it will reset it. Limited to max 25 characters.
        
        {usage}
        
        __Example__
        `{pre}settitle Cool Dood` - set your title to 'Cool Dood'
        `{pre}settitle` - resets your title"""
        if text == "":
            await self.bot.say(":white_check_mark: | Your title has been reset")
        elif len(text) <= 25:
            await self.bot.say(":white_check_mark: | Great your title is now **" + text + "**")
        else:
            await self.bot.say(":negative_squared_cross_mark: | You have gone over the 25 character limit, your title wasn't set.")
            return

        userData[cont.message.author.id]["title"] = text

def setup(bot):
    bot.add_cog(Profile(bot))