import discord
from discord.ext import commands

from rings.utils.converters import time_converter

try:
    import sh
except ImportError:
    import pbs as sh

import io
import re
import aiohttp
import asyncio
import datetime
from PIL import Image

class Meta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot        
        self.hourly_loop = self.bot.loop.create_task(self.hourly())
        
        self.tasks_hourly = [
            self.rotate_status,
            self.check_processes,
            self.broadcast
        ]

        self.tasks_daily = [
            self.clear_potential_star,
            self.clear_temporary_invites,
            self.clear_old_denied,
        ]

        self.processes = {
            "rss.py": "RSS Feeds"
        }
        
    #######################################################################
    ## Cog Functions
    #######################################################################
        
    def cog_unload(self):
        self.hourly_loop.cancel()
        
    #######################################################################
    ## Functions
    #######################################################################

    async def bmp_converter(self, message):
        attachment = message.attachments[0]
        f = io.BytesIO()
        await attachment.save(f)

        with Image.open(f) as im:
            output_buffer = io.BytesIO()
            im.save(output_buffer, "png")
            output_buffer.seek(0)
            ifile = discord.File(filename="converted.png", fp=output_buffer)
        
        await message.channel.send(file=ifile)
        
    async def new_guild(self, guild_id):
        if guild_id not in self.bot.guild_data:
            welcome_message = "Welcome {member} to {server}!"
            goodbye_message = "Leaving so soon? We\'ll miss you, {member}!"

            self.bot.guild_data[guild_id] = {
                "mute":"",
                "automod":"",
                "welcome-channel":"",
                "ignore-command":[],
                "ignore-automod":[],
                "welcome": welcome_message,
                "goodbye": goodbye_message,
                "prefix" :"",
                "disabled": [],
                "auto-role": "",
                "auto-role-timer": 0,
                "starboard-channel":"",
                "starboard-limit":5,
                "self-roles": [],
                "pm-warning": False,
                "mutes": [],
            }
            
            await self.bot.db.query(
                "INSERT INTO necrobot.Guilds(guild_id, welcome_message, goodbye_message) VALUES($1, $2, $3);",
                guild_id, welcome_message, goodbye_message
            )
        
        await self.bot.db.insert_leaderboard(guild_id)

        await self.bot.db.query(
            "INSERT INTO necrobot.FlowersGuild(guild_id) VALUES($1) ON CONFLICT DO NOTHING",
            guild_id
        )
        
    async def delete_guild(self, guild_id):
        if guild_id not in self.bot.guild_data:
            return
            
        del self.bot.guild_data[guild_id]
        await self.bot.db.query(
            "DELETE FROM necrobot.Guilds WHERE guild_id = $1",
            guild_id
        )  
        
    async def new_member(self, user, guild = None):
        await self.bot.db.query(
            "INSERT INTO necrobot.Users(user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING", 
            user.id
        )
            
        if guild is None:
            return
        
        if isinstance(user, discord.User):
            user = guild.get_member(user.id)
            
        permissions = await self.bot.db.get_permission(user.id)
        
        if not any(x[0] == guild.id for x in permissions):
            if any(x[1] == 7 for x in permissions):
                level = 7
            elif any(x[1] == 6 for x in permissions):
                level = 6
            elif user.id == guild.owner.id:
                level = 5
            elif user.guild_permissions.administrator:
                level = 4
            else:
                level = 0
                
            await self.bot.db.insert_permission(user.id, guild.id, level)
            
        await self.bot.db.insert_leaderboard_member(guild.id, user.id)

        await self.bot.db.query(
            "INSERT INTO necrobot.Flowers(guild_id, user_id) VALUES($1, $2) ON CONFLICT DO NOTHING",
            guild.id, user.id
        )
        
    async def star_message(self, message):
        if self.bot.blacklist_check(message.author.id):
            return

        starboard = self.bot.get_channel(self.bot.guild_data[message.guild.id]["starboard-channel"])

        embed = discord.Embed(colour=self.bot.bot_color, description = message.content)
        embed.set_author(name=message.author.display_name, icon_url=message.author.avatar_url_as(format="png", size=128))
        embed.set_footer(**self.bot.bot_footer)
        if message.embeds:
            data = message.embeds[0]
            if data.type == 'image':
                embed.set_image(url=data.url)

        if message.attachments:
            file = message.attachments[0]
            if file.url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
                embed.set_image(url=file.url)
            else:
                embed.add_field(name='Attachment', value=f'[{file.filename}]({file.url})', inline=False)

        embed.add_field(name="Message", value=f'[Jump]({message.jump_url})', inline=False)

        msg = await starboard.send(content=f"In {message.channel.mention}", embed=embed)
        
        if message.id not in self.bot.starred:
            self.bot.starred.append(message.id)
            await self.bot.db.add_star(message, msg, self.bot.guild_data[message.guild.id]["starboard-limit"])
            
    async def hourly(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            if self.bot.counter >= 24:
                self.bot.counter = 0
                self.bot.settings["day"] += 1
                for task in self.tasks_daily:
                    await task()

            now = datetime.datetime.now()
            time = 3600 - (now.second + (now.minute * 60))
            try:
                await asyncio.sleep(time) # task runs every hour
            except asyncio.CancelledError:
                return
            
            for task in self.tasks_hourly:
                await task()

            self.bot.counter += 1

    async def check_processes(self):
        if not self.bot.check_enabled:
            return

        ps = sh.grep(sh.ps("-ef"), 'python3.8')
        downed = []
        for file, name in self.processes.items():
            if file not in ps:
                downed.append(name)

        if downed:
            await self.bot.get_bot_channel().send(f":negative_squared_cross_mark: | The following processes are down: {', '.join(downed)}")
            self.bot.check_enabled = False
        
    async def clear_potential_star(self):
        ids = list(self.bot.potential_stars.keys())
        ids.sort()
        
        for message_id in ids:
            limit = datetime.datetime.utcnow() - datetime.timedelta(days=3)
            timestamp = discord.utils.snowflake_time(message_id)
            
            if timestamp < limit:
                del self.bot.potential_stars[message_id]
            else:
                break

    async def clear_temporary_invites(self):
        for guild in self.bot.guilds:
            try:
                ids = [x.id for x in await guild.invites()]
            except discord.Forbidden:
                return

            await self.bot.db.query(
                "DELETE FROM necrobot.Invites WHERE guild_id = $1 AND id != ANY ($2)",
                guild.id, ids
            )
                
    async def clear_old_denied(self):
        posts = list(self.bot.denied_posts)
        posts.sort()
        
        for post in posts:
            limit = datetime.datetime.utcnow() - datetime.timedelta(seconds=30)
            timestamp = discord.utils.snowflake_time(post["message"].id)
            
            if timestamp < limit:
                self.bot.denied_posts.remove(post)
                
    async def rotate_status(self):
        status = self.bot.statuses.pop(0)
        self.bot.statuses.append(status)
        await self.bot.change_presence(
            activity=discord.Game(status.format(
                guild=len(self.bot.guilds), 
                members=len(self.bot.users)
            ))
        )

    def is_scam(self, message : discord.Message) -> bool:
        has_nitro = "nitro" in message.content.lower()
        # has_nitro_link = any(("nitro" in x.lower() or "gift" in x.lower()) for x in re.findall(self.bot.url_pattern, message.content))
        has_link = bool(re.findall(self.bot.url_pattern, message.content.lower()))
        has_embed = bool(message.embeds)
        has_everyone_ping = "@everyone" in message.content.lower()

        return has_nitro and has_link and has_everyone_ping

    async def restrain_scammer(self, scam_msg : discord.Message):
        if scam_msg.guild is None:
            return

        try:
            await scam_msg.delete()
        except discord.Forbidden:
            pass

        role = discord.utils.get(scam_msg.guild.roles, id=self.bot.guild_data[scam_msg.guild.id]["mute"])
        if role in scam_msg.author.roles or role is None:
            return

        try:
            await scam_msg.author.add_roles(role)
        except discord.Forbidden:
            pass

        automod = scam_msg.guild.get_channel(self.bot.guild_data[scam_msg.guild.id]["automod"])
        if automod is not None:
            embed = discord.Embed(title="Scam Warning", description=f"{scam_msg.author.mention} triggered the scam filter. User has been muted while awaiting moderation review.", colour=self.bot.bot_color)
            embed.set_footer(**self.bot.bot_footer)
            await automod.send(embed=embed)
        
    async def load_cache(self):
        await self.bot.wait_until_ready()
        
        await self.bot.db.create_pool()
        self.bot.session = aiohttp.ClientSession(loop=self.bot.loop)
        
        msg = await self.bot.get_bot_channel().send("**Initiating Bot**")
        for guild in self.bot.guilds:
            await self.new_guild(guild.id)
            await self.guild_checker(guild)
                
            for member in guild.members:
                await self.new_member(member, guild)
                
        for guild in [x for x in self.bot.guild_data if self.bot.get_guild(x) is None]:
            await self.delete_guild(guild)
                
        await msg.edit(content="All servers checked")
        
        reminders = await self.bot.db.get_reminders()
        for reminder in reminders:
            timer = time_converter(reminder["timer"])
            sleep = timer - ((datetime.datetime.now() - reminder["start_date"].replace(tzinfo=None)).total_seconds())
            if sleep <= 0:
                await self.bot.db.delete_reminder(reminder["id"])
            else:
                task = self.bot.loop.create_task(
                    self.bot.meta.reminder_task(
                        reminder["id"],
                        sleep, 
                        reminder["reminder"], 
                        reminder["channel_id"],
                        reminder["user_id"]
                    )
                )
                
                self.bot.reminders[reminder["id"]] = task
                
        self.bot.maintenance = False
        await msg.edit(content="**Bot Online**")
        
    async def guild_checker(self, guild):
        channels = [channel.id for channel in guild.channels]
        roles = [role.id for role in guild.roles] 
        members = [member.id for member in guild.members]
        
        g = self.bot.guild_data[guild.id]

        if g["starboard-channel"] not in channels:
            await self.bot.db.update_starboard_channel(guild.id)
            
        if g["welcome-channel"] not in channels:
            await self.bot.db.update_greeting_channel(guild.id)
        if g["automod"] not in channels:
            await self.bot.db.update_automod_channel(guild.id)
            
        if g["mute"] not in roles:
            await self.bot.db.update_mute_role(guild.id)
            
        await self.bot.db.delete_self_roles(guild.id, *[role for role in g["self-roles"] if role not in roles])
        await self.bot.db.sync_invites(guild)
        
        await self.bot.db.query(
            "DELETE FROM necrobot.Youtube WHERE guild_id = $1 AND NOT(channel_id = ANY($2))",
            guild.id, channels            
        )

        await self.bot.db.query(
            "DELETE FROM necrobot.Broadcasts WHERE guild_id = $1 AND NOT(channel_id = ANY($2))",
            guild.id, channels
        )
        
        combined = [*channels, *roles, *members]
        await self.bot.db.delete_automod_ignore(guild.id, [x for x in g["ignore-automod"] if x not in combined])
        await self.bot.db.delete_command_ignore(guild.id, [x for x in g["ignore-command"] if x not in combined])
        
        await self.bot.db.query(
            "DELETE FROM necrobot.Permissions WHERE guild_id = $1 AND NOT(user_id = any($2))",
            guild.id, members    
        )

        await self.bot.db.query(
            "DELETE FROM necrobot.PermissionRoles WHERE guild_id = $1 AND NOT(role_id = any($2))",
            guild.id, roles
        )
        
    async def reminder_task(self, reminder_id, time, message, channel_id, user_id):
        try:
            await asyncio.sleep(time)
        except asyncio.CancelledError:
            return

        channel = self.bot.get_channel(channel_id)
        user = self.bot.get_user(user_id)
        if channel is not None and user is not None:
            if message is None or message == "":
                await channel.send(f":alarm_clock: | {user.mention}, you asked to be reminded!")
            else:
                await channel.send(f":alarm_clock: | {user.mention} reminder: **{message}**")
        
        del self.bot.reminders[reminder_id]
        await self.bot.db.delete_reminder(reminder_id)

    async def broadcast(self):
        total_hours = (self.bot.settings["day"] * 24) + self.bot.counter

        broadcasts = await self.bot.db.query(
            "SELECT * FROM necrobot.Broadcasts WHERE MOD(($1 - start_time), interval) = 0 AND enabled=True",
            total_hours
        )

        for broadcast in broadcasts:
            try:
                await self.bot.get_channel(broadcast[2]).send(broadcast[5], allowed_mentions=discord.AllowedMentions())
            except discord.Forbidden:
                pass
            except Exception as e:
                await self.bot.get_error_channel().send(f"Broadcast error with guild {broadcast[1]}\n{e}")
        
def setup(bot):
    bot.add_cog(Meta(bot))
