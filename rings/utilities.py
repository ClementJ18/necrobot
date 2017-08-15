#!/usr/bin/python3.6
import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

from simpleeval import simple_eval
import time
import dice
import random

ball8List = ["It is certain"," It is decidedly so"," Without a doubt","Yes, definitely","You may rely on it","As I see it, yes"," Most likely","Outlook good","Yes","Signs point to yes","Reply hazy try again","Ask again later","Better not tell you now"," Cannot predict now","Concentrate and ask again","Don't count on it"," My reply is no","My sources say no","Outlook not so good","Very doubtful"]


class Utilities():
    """A bunch of useful commands to do various tasks."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(3, 5, BucketType.user)
    async def calc(self, *, equation : str):
        """Evaluates a pythonics mathematical equation, use the following to build your mathematical equations:
        `*` - for multiplication
        `+` - for additions
        `-` - for substractions
        `/` - for divisons
        `**` - for exponents
        `%` - for modulo
        More symbols can be used, simply research 'python math symbols'
        \n
        {}
        \n
        __Example__
        `n!calc 2 + 2` - 4
        `n!calc (4 + 5) * 3 / (2 - 1)` - 27
        """
        try:
            final = simple_eval(equation)
            await self.bot.say(":1234: | **" + str(final) + "**")
        except NameError:
            await self.bot.say(":negative_squared_cross_mark: | **Mathematical equation not recognized.**")

    @commands.command(pass_context=True, aliases=["pong"])
    @commands.cooldown(3, 5, BucketType.user)
    async def ping(self, cont):
        """Pings the user and returns the time it took. 
        \n
        {}"""
        pingtime = time.time()
        pingms = await self.bot.say(" :clock1: | Pinging... {}'s location".format(cont.message.author.display_name))
        ping = time.time() - pingtime
        await self.bot.edit_message(pingms, ":white_check_mark: | The ping time is `%.01f seconds`" % ping)

    #prints a rich embed of the server info it was called in
    @commands.command(pass_context = True)
    @commands.cooldown(1, 5, BucketType.user)
    async def serverinfo(self, cont):
        """Returns a rich embed of the server's information. 
        \n
        {}"""
        server = cont.message.server
        embed = discord.Embed(title="__**" + server.name + "**__", colour=discord.Colour(0x277b0), description="Info on this server")
        embed.set_thumbnail(url=server.icon_url.replace("webp","jpg"))
        embed.set_footer(text="Generated by NecroBot", icon_url="https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128")

        embed.add_field(name="**Date Created**", value=server.created_at.strftime("%d - %B - %Y %H:%M"))
        embed.add_field(name="**Owner**", value=server.owner.name + "#" + server.owner.discriminator, inline=True)

        embed.add_field(name="**Default Channel**", value=server.default_channel)
        embed.add_field(name="**Members**", value=server.member_count, inline=True)

        embed.add_field(name="**Region**", value=server.region)
        embed.add_field(name="**Server ID**", value=server.id, inline=True)

        channelList = [channel.name for channel in server.channels]
        roleList = [role.name for role in server.roles]
        embed.add_field(name="**Channels**", value=str(len(channelList)) + ": " + ", ".join(channelList))
        embed.add_field(name="**Roles**", value=str(len(roleList) - 1) + ": " + ", ".join(roleList[1:]))

        await self.bot.say(embed=embed)

    @commands.command()
    @commands.cooldown(5, 10, BucketType.channel)
    async def avatar(self, user : discord.Member):
        """Returns a link to the given user's profile pic 
        \n
        {}
        \n
        __Example__
        `n!avatar @NecroBot` - return the link to NecroBot's avatar"""
        await self.bot.say(user.avatar_url.replace("webp","jpg"))

    @commands.command()
    @commands.cooldown(5, 5, BucketType.user)
    async def choose(self, *, choices):
        """Returns a single choice from the list of choices given. Use `|` to seperate each of the choices.
        \n
        {}
        \n
        __Example__
        `n!choose Bob | John | Mary` - choose between the names of Bob, John, and Mary
        `n!choose 1 | 2` - choose between 1 and 2 """
        choiceList = [x.strip() for x in choices.split("|")]
        await self.bot.say("I choose **" + random.choice(choiceList) + "**")

    @commands.command()
    @commands.cooldown(5, 5, BucketType.user)
    async def coin(self):
        """Flips a coin and returns the result
        \n
        {}"""
        await self.bot.say(random.choice(["Head","Tail"]))

    @commands.command(pass_context = True)
    @commands.cooldown(5, 5, BucketType.user)
    async def roll(self, cont, dices="1d6"):
        """Rolls one or multiple x sided dices and returns the result. Structure of the argument: `[number of die]d[number of faces]` 
        \n
        {}
        \n
        __Example__
        `n!roll 3d8` - roll three 8-sided die
        `n!roll` - roll one 6-sided die"""
        await self.bot.say(":game_die: | " + cont.message.author.display_name + " rolled " + str(dice.roll(dices)))

    @commands.command(name="8ball")
    @commands.cooldown(3, 5, BucketType.user)
    async def ball8(self, *, question):
        """Uses an 8ball system to reply to the user's question. 
        \n
        {}"""
        await self.bot.say(":8ball: | " + random.choice(ball8List))

def setup(bot):
    bot.add_cog(Utilities(bot))