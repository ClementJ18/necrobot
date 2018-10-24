#!/usr/bin/python3.6
import discord
from discord.ext import commands

from rings.utils.utils import has_goodbye, has_welcome, has_automod, UPDATE_PERMS, UPDATE_FLOWERS

import sys
import asyncio
import traceback
from datetime import timedelta

class NecroEvents():
    def __init__(self, bot):
        self.bot = bot

    async def on_resumed(self):
        channel = self.bot.get_channel(318465643420712962)
        await channel.send("**Bot Resumed**")

    async def on_command_error(self, ctx, error):
        """Catches error and sends a message to the user that caused the error with a helpful message."""
        channel = ctx.message.channel
        if isinstance(error, commands.MissingRequiredArgument):
            await channel.send(f":negative_squared_cross_mark: | Missing required argument: `{error.param.name}`! Check help guide with `n!help {ctx.command.qualified_name}`", delete_after=10)
            #this can be used to print *all* the missing arguments (bit hacky tho)
            # index = list(ctx.command.clean_params.keys()).index(error.param.name)
            # missing = list(ctx.command.clean_params.values())[index:]
            # print(f"missing following: {", ".join([x.name for x in missing])}")
        elif isinstance(error, commands.CheckFailure):
            await channel.send(f":negative_squared_cross_mark: | **{error}**", delete_after=10)
        elif isinstance(error, commands.CommandOnCooldown):
            retry_after = str(timedelta(seconds=error.retry_after)).partition(".")[0].replace(":", "{}").format("hours, ", "minutes and ")
            await channel.send(f":negative_squared_cross_mark: | This command is on cooldown, retry after **{retry_after}seconds**", delete_after=10)
        elif isinstance(error, commands.NoPrivateMessage):
            await channel.send(":negative_squared_cross_mark: | This command cannot be used in private messages.", delete_after=10)
        elif isinstance(error, commands.DisabledCommand):
            await channel.send(":negative_squared_cross_mark: | This command is disabled and cannot be used for now.", delete_after=10)
        elif isinstance(error, commands.BadArgument) or isinstance(error, commands.BadUnionArgument):
            await channel.send(f":negative_squared_cross_mark: | Following error with passed arguments: **{error}**", delete_after=10)
        elif isinstance(error, asyncio.TimeoutError) and hasattr(error, "timer"):
            retry_after = str(timedelta(seconds=error.timer)).partition(".")[0].replace(":", "{}").format("hours, ", "minutes and ")
            await channel.send(f":negative_squared_cross_mark: | You took too long to reply, please reply within {retry_after}seconds next time", delete_after=10)
        elif isinstance(error, commands.CommandInvokeError):
            if "Forbidden" in error.args[0]:
                await channel.send(":negative_squared_cross_mark: | Something went wrong, check my permission level, it seems I'm not allowed to do that on your server.", delete_after=10)
                return

            channel = self.bot.get_channel(415169176693506048)
            the_traceback = "```py\n" + " ".join(traceback.format_exception(type(error), error, error.__traceback__, chain=True)) + "\n```"
            embed = discord.Embed(title="Command Error", description=the_traceback, colour=discord.Colour(0x277b0))
            embed.set_footer(text="Generated by NecroBot", icon_url="https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128")
            embed.add_field(name="Command", value=ctx.command.name)
            embed.add_field(name="Author", value=ctx.author.mention)
            embed.add_field(name="Location", value=f"**Guild:** {ctx.guild.name} ({ctx.guild.id}) \n**Channel:** {ctx.channel.name} ({ctx.channel.id})")
            embed.add_field(name="Message", value=ctx.message.content, inline=False)
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                print(f'Bot: Ignoring exception in command {ctx.command}:', file=sys.stderr)
                traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
            
            if ctx.guild.id != 311630847969198082:
                await ctx.send(":negative_squared_cross_mark: | Something unexpected went wrong, Necro's gonna get right to it. If you wish to know more on what went wrong you can join the support server, the invite is in the `about` command.", delete_after=10)
                
    async def on_guild_join(self, guild):
        if guild.id in self.bot.settings["blacklist"]:
            await guild.leave()
            return

        if guild.id not in self.bot.server_data:
            self.bot.server_data[guild.id] = self.bot._new_server()
            await self.bot.query_executer("INSERT INTO necrobot.Guilds VALUES($1, 0, 0, 0, 'Welcome {member} to {server}!', 'Leaving so soon? We''ll miss you, {member}!)', '', 0, '', 1, 0, 5, 0, 0);", guild.id)

        for member in guild.members:
            await self.bot.default_stats(member, guild)
            
        await guild.owner.send(embed=self.bot.tutorial_e)

    async def on_message_delete(self, message):
        if message.id in self.bot.ignored_messages:
            self.bot.ignored_messages.remove(message.id)
            return
            
        if isinstance(message.channel, discord.DMChannel) or message.author.bot:
            return

        if has_automod(self.bot, message):
            if not message.content:
                message.content = "\U0000200b"

            embed = discord.Embed(title="Message Deleted", description=message.content, colour=discord.Colour(0x277b0))
            embed.set_author(name=message.author, icon_url= message.author.avatar_url)
            embed.set_footer(text="Generated by NecroBot", icon_url="https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128")
            embed.add_field(name="Info", value="In " + message.channel.mention + " by " + message.author.mention)
            embed.add_field(name="Attachment?", value="Yes" if message.attachments else "No", inline=False)
            channel = self.bot.get_channel(self.bot.server_data[message.guild.id]["automod"])
            await channel.send(embed=embed)

    async def on_message_edit(self, before, after):
        if isinstance(before.channel, discord.DMChannel) or before.author.bot or before.content == after.content:
            return

        if has_automod(self.bot, message):
            embed = discord.Embed(title="Message Edited", description=f"In {before.channel.mention} by {before.author.mention}", colour=discord.Colour(0x277b0))
            if not after.content:
                after.content = "\U0000200b"

            embed.set_author(name=before.author, icon_url= before.author.avatar_url)
            embed.set_footer(text="Generated by NecroBot", icon_url="https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128")
            embed.add_field(name="Before", value=before.content if len(before.content) < 1024 else before.content[1020:] + "...", inline=False)
            embed.add_field(name="After", value=after.content if len(after.content) < 1024 else after.content[1020:] + "...", inline=False)
            channel = self.bot.get_channel(self.bot.server_data[before.guild.id]["automod"])
            await channel.send(embed=embed)

    async def on_command(self, ctx):
        try:
            can_run = str(await ctx.command.can_run(ctx) and ctx.command.enabled)
        except commands.CheckFailure:
            can_run = "False"

        guildname = "DM"
        guildid = None
        if ctx.guild:
            guildname = ctx.guild.name
            guildid = ctx.guild.id

        await self.bot.query_executer("INSERT INTO necrobot.Logs (user_id, username, command, guild_id, guildname, message, can_run) VALUES($1,$2,$3,$4,$5,$6,$7);", ctx.author.id, ctx.author.name, ctx.command.name, guildid, guildname, ctx.message.content, can_run)

    async def on_member_join(self, member):
        await self.bot.default_stats(member, member.guild)

        if member.bot:
            return

        if has_welcome(self.bot, member):
            channel = self.bot.get_channel(self.bot.server_data[member.guild.id]["welcome-channel"])
            message = self.bot.server_data[member.guild.id]["welcome"]
            if member.id in self.bot.settings["blacklist"]:
                await channel.send(":eight_pointed_black_star: | **You are not welcome here, disturber of the peace**")
            else:
                await channel.send(message.format(member=member, server=member.guild.name))

        if not self.bot.server_data[member.guild.id]["auto-role"] == "":
            role = discord.utils.get(member.guild.roles, id=self.bot.server_data[member.guild.id]["auto-role"])
            await member.add_roles(role)

            if self.bot.server_data[member.guild.id]["auto-role-timer"] > 0:
                await asyncio.sleep(self.bot.server_data[member.guild.id]["auto-role-timer"])
                try:
                    await member.remove_roles(role)
                except:
                    pass

    async def on_member_remove(self, member):
        if self.bot.user_data[member.id]["perms"][member.guild.id] < 6:
            self.bot.user_data[member.id]["perms"][member.guild.id] = 0
            await self.bot.query_executer(UPDATE_PERMS, 0, member.guild.id, member.id)

        if has_goodbye(self.bot, member):
            channel = self.bot.get_channel(self.bot.server_data[member.guild.id]["welcome-channel"])
            message = self.bot.server_data[member.guild.id]["goodbye"]

            if member.id in self.bot.settings["blacklist"]:
                await channel.send(":eight_pointed_black_star: | **...**")
            else:
                await channel.send(message.format(member=member, server=member.guild.name))

    async def on_reaction_add(self, reaction, user):
        if user.id in self.bot.settings["blacklist"]:
            return
            
        if isinstance(user, discord.User) and reaction.emoji == "\N{WASTEBASKET}" and reaction.message.author == self.bot.user:
            await reaction.message.delete()
            return            

        if reaction.emoji == "\N{CHERRY BLOSSOM}" and reaction.message.id in self.bot.events:
            if user.id in self.bot.events[reaction.message.id]["users"]:
                return

            self.bot.events[reaction.message.id]["users"].append(user.id)
            self.bot.user_data[user.id]["waifu"][reaction.message.guild.id]["flowers"] += self.bot.events[reaction.message.id]["amount"]
            await self.bot.query_executer(UPDATE_FLOWERS, self.bot.user_data[user.id]["waifu"][reaction.message.guild.id]["flowers"], user.id, reaction.message.guild.id)

        if self.bot.server_data[user.guild.id]["starboard-channel"] == "":
            return

        if reaction.message.channel.id == self.bot.server_data[user.guild.id]["starboard-channel"]:
            return

        if reaction.message.id in self.bot.starred:
            return

        if reaction.emoji == "\N{WHITE MEDIUM STAR}" and reaction.count >= self.bot.server_data[user.guild.id]["starboard-limit"]:
            users = await reaction.users().flatten()
            try:
                users.remove(reaction.message.author)
            except ValueError:
                pass

            if len(users) >=  self.bot.server_data[user.guild.id]["starboard-limit"]:
                await self.bot._star_message(reaction.message)   

    async def on_guild_channel_delete(self, channel):
        guild = self.bot.server_data[channel.guild.id]

        if channel.id == guild["broadcast-channel"]:
            guild["broadcast-channel"] = ""
            await self.bot.query_executer("UPDATE necrobot.Guilds SET broadcast_channel = 0 WHERE guild_id = $1;", channel.guild.id)

        if channel.id == guild["starboard-channel"]:
            guild["starboard"] = ""
            await self.bot.query_executer("UPDATE necrobot.Guilds SET starboard_channel = 0 WHERE guild_id = $1;", channel.guild.id)

        if channel.id == guild["welcome-channel"]:
            guild["welcome-channel"] = ""
            await self.bot.query_executer("UPDATE necrobot.Guilds SET welcome_channel = 0 WHERE guild_id = $1;", channel.guild.id)

        if channel.id == guild["automod"]:
            guild["automod"] = ""
            await self.bot.query_executer("UPDATE necrobot.Guilds SET automod_channel = 0 WHERE guild_id = $1;", channel.guild.id) 

    async def on_guild_role_delete(self, role):
        guild = self.bot.server_data[role.guild.id]

        if role.id == guild["mute"]:
            guild["mute"] = "" 
            await self.bot.query_executer("UPDATE necrobot.Guilds SET mute = 0 WHERE guild_id = $1;", role.guild.id)

        if role.id in guild["self-roles"]:
            guild["self-roles"].remove(role.id)
            await self.bot.query_executer("DELETE FROM necrobot.SelfRoles WHERE guild_id = $1 AND id = $2;", role.guild.id, role.id)

def setup(bot):
    bot.add_cog(NecroEvents(bot))
