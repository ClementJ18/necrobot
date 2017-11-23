#!/usr/bin/python3.6
import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
from rings.botdata.data import Data
import asyncio
import re
from rings.botdata.utils import has_perms, is_necro, allmentions, userData, serverData

lockedList = list()


class Moderation():
    """All of the tools moderators can use from the most basic such as `nick` to the most complex like `purge`. All you need to keep your server clean and tidy"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["rename","name"], pass_context = True)
    @has_perms(1)
    async def nick(self, cont, user : discord.Member, *, nickname=""):
        """ Nicknames a user, use to clean up offensive or vulgar names or just to prank your friends. Will return an error message if the user cannot be renamed due to permission issues. (Permission level required: 1+ (Helper))
        
        {usage}
        
        __Example__
        `{pre}nick @NecroBot Lord of All Bots` - renames NecroBot to 'Lord of All Bots'
        `{pre}nick @NecroBot` - will reset NecroBot's nickname"""
        if userData[cont.message.author.id]["perms"][cont.message.server.id] > userData[user.id]["perms"][cont.message.server.id]:
            if nickname == "":
                msg = ":white_check_mark: | User **{0.display_name}**'s nickname reset".format(user)
            else:
                msg = ":white_check_mark: | User **{0.display_name}** renamed to **{1}**".format(user, nickname)

            try:
                await self.bot.say(msg)
                await self.bot.change_nickname(user, nickname)
            except discord.errors.Forbidden:
                await self.bot.say(":negative_squared_cross_mark: | You cannot change the nickname of that user.")
        else:
            await self.bot.say(":negative_squared_cross_mark: | You do not have the required NecroBot permissions to rename this user.")

    @commands.command(pass_context = True)
    @has_perms(2)
    async def mute(self, cont, user : discord.Member, *seconds : int):
        """Blocks the user from writing in channels by giving it the server's mute role. Make sure an admin has set a mute role using `{pre}settings mute`. The user can either be muted for the given amount of seconds or indefinitely if no amount is given. (Permission level required: 2+ (Moderator))
        
        {usage}

        __Example__
        `{pre}mute @NecroBot` - mute NecroBot until a user with the proper permission level does `{pre}unmute @NecroBot`
        `{pre}mute @NecroBot 30` - mutes NecroBot for 30 seconds or until a user with the proper permission level does `{pre}unmute @NecroBot`"""
        if serverData[cont.message.server.id]["mute"] == "":
            await self.bot.say(":negative_squared_cross_mark: | Please set up the mute role with `n!settings mute [rolename]` first.")
            return

        role = discord.utils.get(cont.message.server.roles, name=serverData[cont.message.server.id]["mute"])
        if role not in user.roles:
            await self.bot.add_roles(user, role)
            await self.bot.send_message(self.bot.get_channel(cont.message.channel.id),":white_check_mark: | User: **{0}** has been muted".format(user.display_name))
        else:
            await self.bot.send_message(self.bot.get_channel(cont.message.channel.id),":negative_squared_cross_mark: | User: **{0}** is already muted".format(user.display_name))
            return

        if seconds:
            await asyncio.sleep(seconds[0])
            if role in user.roles:
                await self.bot.remove_roles(user, role)
                await self.bot.send_message(self.bot.get_channel(cont.message.channel.id),":white_check_mark: | User: **{0}** has been automatically unmuted".format(user.display_name))

    @commands.command(pass_context = True)
    @has_perms(2)
    async def unmute(self, cont, user : discord.Member):
        """Unmutes a user by removing the mute role, allowing them once again to write in text channels. (Permission level required: 2+ (Moderator))
        
        {usage}

        __Example__
        `{pre}unmute @NecroBot` - unmutes NecroBot if he is muted"""
        if serverData[cont.message.server.id]["mute"] == "":
            await self.bot.say(":negative_squared_cross_mark: | Please set up the mute role with `n!settings mute [rolename]` first.")
            return
            
        role = discord.utils.get(cont.message.server.roles, name=serverData[cont.message.server.id]["mute"])
        if role in user.roles:
            await self.bot.remove_roles(user, role)
            await self.bot.send_message(self.bot.get_channel(cont.message.channel.id),":white_check_mark: | User: **{0}** has been unmuted".format(user.display_name))
        else:
            await self.bot.send_message(self.bot.get_channel(cont.message.channel.id),":negative_squared_cross_mark: | User: **{0}** is not muted".format(user.display_name))

    @commands.group(invoke_without_command = True, pass_context=True)
    @has_perms(1)
    async def warn(self, cont, user : discord.Member, *, message : str):
        """Adds the given message as a warning to the user's NecroBot profile (Permission level required: 1+ (Server Helper))
        
        {usage}
        
        __Example__
        `{pre}warn @NecroBot For being the best bot` - will add the warning 'For being the best bot' to Necrobot's warning list and pm the warning message to him"""
        await self.bot.say(":white_check_mark: | Warning: **\"" + message + "\"** added to warning list of user " + user.display_name)
        userData[user.id]["warnings"].append(message + " by " + str(cont.message.author) + " on server " + cont.message.server.name)
        await self.bot.send_message(user, "You have been warned on " + cont.message.server.name + ", the warning is: \n" + message)

    @warn.command(name="del")
    @has_perms(3)
    async def warn_del(self, user : discord.Member, position : int):
        """Removes the warning from the user's NecroBot system based on the given warning position. (Permission level required: 3+ (Server Semi-Admin)) 
        
        {usage}
        
        __Example__
        `{pre}warn del @NecroBot 1` - delete the warning in first position of NecroBot's warning list"""
        await self.bot.say(":white_check_mark: | Warning: **\"" + userData[user.id]["warnings"][position - 1] + "\"** removed from warning list of user " + user.display_name)
        userData[user.id]["warnings"].pop(position - 1)

    @commands.command()
    @has_perms(3)
    async def lock(self, user : discord.Member):
        """Moves a user back to the voice channel they were locked in every time they try to move to another one (Permission level required: 3+ (Semi-Admin))
        
        {usage}
        
        __Example__
        `{pre}lock @NecroBot` - lock NecroBot in the voice channel it currently is in
        """
        if user.id in lockedList:
            lockedList.remove(user.id)
            await self.bot.say(":white_check_mark: | User no longer locked in channel **"+ self.bot.get_channel(userData[user.id]['locked']).name + "**")
            userData[user.id]["locked"] = ""
        else:
            v_channel = user.voice_channel
            userData[user.id]["locked"] = v_channel.id
            lockedList.append(user.id)
            await self.bot.say(":white_check_mark: | User locked in channel **"+ v_channel.name + "**")

    @commands.command(pass_context = True)
    @commands.cooldown(1, 10, BucketType.channel)
    @has_perms(4)
    async def purge(self, cont, number : int = 1, check="", extra=""):
        """Removes number of messages from the channel it is called in. That's all it does at the moment but later checks will also be added to allow for more flexible/specific purging (Permission level required: 4+ (Server Admin))
        
        {usage}
        
        __Example__
        `{pre}purge 50` - purges the last 50 messages
        `{pre}purge 15 link` - purges all messages containing links from the previous 15 messages
        `{pre}purge 20 mention @Necro` - purges all messages sent by @Necro from the previous 20 messages
        `{pre}purge 35 bot` - purges all messages sent by the bot from the previous 35 messages"""
        channel = serverData[cont.message.server.id]["automod"]
        serverData[cont.message.server.id]["automod"] = ""

        if check == "link":
            deleted = await self.bot.purge_from(cont.message.channel, limit=number+1, check=lambda m: "http" in m.content)
        elif check == "mention":
            deleted = await self.bot.purge_from(cont.message.channel, limit=number+1, check=lambda m: m.author.mention == extra)
        elif check == "image":
            deleted = await self.bot.purge_from(cont.message.channel, limit=number+1, check=lambda m: len(m.attachments) > 0)
        elif check == "bot":
            deleted = await self.bot.purge_from(cont.message.channel, limit=number+1, check=lambda m: m.author == self.bot.user)
        else:
            deleted = await self.bot.purge_from(cont.message.channel, limit=number+1)

        await self.bot.say(":wastebasket: | **{}** messages purged.".format(len(deleted)), delete_after=5)

        serverData[cont.message.server.id]["automod"] = channel

    @commands.command(pass_context = True)
    @has_perms(3)
    async def speak(self, cont, channel : str, *, message : str):
        """Send the given message to the channel mentioned either by id or by mention. Requires the correct permission level on both servers. (Permission level required: 3+ (Semi-Admin))
        
        {usage}
        
        __Example__
        `{pre}speak #general Hello` - sends hello to the mentionned #general channel
        `{pre}speak 235426357468543 Hello` - sends hello to the channel with the given ID (if any)"""
        try: 
            channel = self.allmentions(cont, channel)[0]
        except IndexError:
            await self.bot.say("No channel with that name")
            return
        
        if userData[cont.message.author.id]["perms"][cont.message.server.id] >= 3 and userData[cont.message.author.id]["perms"][channel.server.id] >= 3:
            await self.bot.send_message(channel, ":loudspeaker: | " + message)
        elif userData[cont.message.author.id]["perms"][channel.server.id] < 4:
            await self.bot.say(":negative_squared_cross_mark: | You do not have the required NecroBot permissions on the server you're trying to send the message to.")
        else:
            await self.bot.say(":negative_squared_cross_mark: | You do not have the required NecroBot permissions to use this command.")

    async def on_voice_state_update(self, before, after):
        if before.id in lockedList:
            await self.bot.move_member(before, self.bot.get_channel(userData[before.id]["locked"]))


def setup(bot):
    bot.add_cog(Moderation(bot))
