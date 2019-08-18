import discord

from rings.utils.config import dbpass
from rings.utils.utils import UPDATE_PERMS, time_converter

import io
import asyncio
import asyncpg
import datetime
import traceback
from PIL import Image
from bs4 import BeautifulSoup
from collections import defaultdict

class Meta():
    def __init__(self, bot):
        self.bot = bot
        self.bot._new_server = self._new_server
        self.bot._mu_auto_embed = self._mu_auto_embed
        self.bot._bmp_converter = self._bmp_converter
        self.bot._star_message = self._star_message
        self.bot.query_executer = self.query_executer
        self.bot.default_stats = self.default_stats
        self.bot.load_cache = self.load_cache
        self.bot.guild_checker = self.guild_checker
        self.bot.broadcast_task = self.bot.loop.create_task(self.broadcast())
        self.bot.status_task = self.bot.loop.create_task(self.rotation_status())
        self.bot.reminder_task = self.reminder_task

    def __unload(self):
        self.bot.broadcast_task.cancel()
        self.bot.status_task.cancel()

    def _new_server(self):
        return {
            "mute":"",
            "automod":"",
            "welcome-channel":"",
            "self-roles":[],
            "ignore-command":[],
            "ignore-automod":[],
            "welcome":"Welcome {member} to {server}!",
            "goodbye":"Leaving so soon? We\'ll miss you, {member}!",
            "tags":{},
            "prefix" :"",
            "broadcast-channel": "",
            "broadcast": "",
            "broadcast-time": 1,
            "disabled": [],
            "auto-role": "",
            "auto-role-timer": 0,
            "starboard-channel":"",
            "starboard-limit":5,
            "aliases":{},
        } 

    async def _mu_auto_embed(self, url, message):
        async with self.bot.session.get(url) as resp:
            soup = BeautifulSoup(await resp.text(), "html.parser")

        try:
            header = list(soup.find_all("h3", class_="catbg")[-1].stripped_strings)[1].replace("Thema: ", "").split(" \xa0")
            title = header[0]
            read = header[1].replace("Gelesen", "Read**").replace("mal", "**times").replace("(", "").replace(")","")
        except IndexError:
            return

        op = soup.find("div", class_="poster")
        board = [x.a.string for x in soup.find("div", class_="navigate_section").ul.find_all("li") if "board" in x.a["href"]][0]

        embed = discord.Embed(title=title, url=url, colour=discord.Colour(0x277b0), description=f"Some information on the thread that was linked \n -Board: **{board}** \n -{read}")
        if op.a is not None:
            embed.set_author(name=f"OP: {op.a.string}", url=op.a["href"], icon_url=op.find("img", class_="avatar")["src"] if op.find("img", class_="avatar") is not None else self.bot.user.avatar_url_as(format="png", size=128))
        else:
            embed.set_author(name=f"OP: {list(op.stripped_strings)[0]}")

        embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))

        await message.channel.send("Oh. That's a little bare. Here, let me embed that for you.", embed=embed)

    async def _bmp_converter(self, message):
        attachment = message.attachments[0]
        f = io.BytesIO()
        await attachment.save(f)

        with Image.open(f) as im:
            output_buffer = io.BytesIO()
            im.save(output_buffer, "png")
            output_buffer.seek(0)
            ifile = discord.File(filename="converted.png", fp=output_buffer)
        
        await message.channel.send(file=ifile)

    async def _star_message(self, message):
        if message.author.id in self.bot.settings["blacklist"]:
            return

        embed = discord.Embed(colour=discord.Colour(0x277b0), description = message.content)
        embed.set_author(name=message.author.display_name, icon_url=message.author.avatar_url.replace("webp","jpg"))
        embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))
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

        msg = await self.bot.get_channel(self.bot.server_data[message.guild.id]["starboard-channel"]).send(content=f"In {message.channel.mention}", embed=embed)
        
        if message.id not in self.bot.starred:
            self.bot.starred.append(message.id)
            await self.bot.query_executer("INSERT INTO necrobot.Starred VALUES ($1, $2, $3, $4);", message.id, msg.id, msg.guild.id, message.author.id)        
        
    async def broadcast(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            if self.bot.counter >= 24:
                self.bot.counter = 0

            now = datetime.datetime.now()
            time = 3600 - (now.second + (now.minute * 60))
            try:
                await asyncio.sleep(time) # task runs every hour
            except asyncio.CancelledError:
                return
            self.bot.counter += 1

            def guild_check(guild):
                if self.bot.server_data[guild]["broadcast-time"] < 1:
                    return False

                if self.bot.get_guild(guild) is None:
                    return False

                if self.bot.get_channel(self.bot.server_data[guild]["broadcast-channel"]) is None:
                    return False
                    
                return self.bot.counter % self.bot.server_data[guild]["broadcast-time"] == 0

            broadcast_guilds = [guild for guild in self.bot.server_data if guild_check(guild)]

            for guild in broadcast_guilds:
                try:
                    channel = self.bot.get_channel(self.bot.server_data[guild]["broadcast-channel"])
                    await channel.send(self.bot.server_data[guild]["broadcast"])
                except Exception as e:
                    await self.bot.get_channel(415169176693506048).send(f"Broadcast error with guild {guild}\n{e}")

    async def rotation_status(self):
        await self.bot.wait_until_ready()
        try:
            while not self.bot.is_closed():
                await asyncio.sleep(3600)
                status = self.bot.statuses.pop(0)
                self.bot.statuses.append(status)
                await self.bot.change_presence(activity=discord.Game(name=status.format(guild=len(self.bot.guilds), members=len(self.bot.users))))
        except asyncio.CancelledError:
            return
        except Exception as e:
            self.bot.dispatch("error", f'rotation_status: {e}')

    async def load_cache(self):        
        self.bot.pool = await asyncpg.create_pool(database="postgres", user="postgres", password=dbpass)
        msg = await self.bot.get_channel(318465643420712962).send("**Initiating Bot**")
     
        #checking what guilds we are in, setting the data for the new ones and checking if the already existing ones have
        #deleted anything that could break the bot while it was down (roles, channels)   
        for guild in self.bot.guilds:
            if guild.id not in self.bot.server_data:
                self.bot.server_data[guild.id] = self.bot._new_server()
                await self.bot.query_executer("INSERT INTO necrobot.Guilds VALUES($1, 0, 0, 0, 'Welcome {member} to {server}!', 'Leaving so soon? We''ll miss you, {member}!)', '', 0, '', 1, 0, 5, 0);", guild.id)
            else:
                await self.bot.guild_checker(guild)

        await msg.edit(content="All servers checked")
        
        #checking if there are any new members and setting default stats for any newcomers, in addition we group
        #up all the guilds the users are in for later use
        # d = {..., user_id :[guild_id, guild_id, guild_id], ...}
        d = defaultdict(list)
        for member in self.bot.get_all_members():
            d[member.id].append(member.guild.id)
            await self.bot.default_stats(member, member.guild)

        await asyncio.sleep(1)

        #now we're gonna go through each user and each guild that they are no longer in to reset their permissions
        #so if the user is kicked/banned when we're down they don't come back with all the perms. Necrobot Admins are
        #spared from this
        #In a second part we also set up all the tasks for the reminders, each reminder gets their remaining time 
        #calculated (and set to 0 if it's done) and then the task is set.

        #we actually don't wanna do this cause cache, instead we will catch it on the on_member_join
        for user in self.bot.users:
            # logged = set(self.bot.user_data[user.id]["perms"].keys())
            # for guild_id in logged - set(d[user.id]):
            #     if self.bot.user_data[user.id]["perms"][guild_id] < 6:
            #         self.bot.user_data[user.id]["perms"][guild_id] = 0
            #         await self.bot.query_executer(UPDATE_PERMS, 0, guild_id, user.id)

            for reminder in self.bot.user_data[user.id]["reminders"]:
                time = datetime.datetime.strptime(reminder["start"], '%Y-%m-%d %H:%M:%S.%f')
                timer = time_converter(reminder["timer"])

                sleep = timer - ((datetime.datetime.now() - time).total_seconds())
                if sleep < 0:
                    sleep = 0

                task = self.bot.loop.create_task(self.bot.reminder_task(user.id, reminder, sleep))
                reminder["task"] = task

        await msg.edit(content="**Bot Online**")
        await self.bot.change_presence(activity=discord.Game(name="n!help for help"))

    async def query_executer(self, query, *args, **kwargs):
        if self.bot.pool is None:
            return []

        conn = await self.bot.pool.acquire()
        result = []
        try:
            if query.upper().startswith("SELECT"):
                result = await conn.fetch(query, *args)
            elif "fetchval" in kwargs:
                result = await conn.fetchval(query, *args)
            else:
                await conn.execute(query, *args)
        except Exception as error:
            channel = self.bot.get_channel(415169176693506048)
            the_traceback = f"```py\n{' '.join(traceback.format_exception(type(error), error, error.__traceback__, chain=False))}\n```"
            embed = discord.Embed(title="DB Error", description=the_traceback, colour=discord.Colour(0x277b0))
            embed.add_field(name='Event', value=error)
            embed.add_field(name="Query", value=query)
            embed.add_field(name="Arguments", value=args)
            embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))
            await channel.send(embed=embed) 
        
        await self.bot.pool.release(conn)
        return result
            
            
    async def default_stats(self, member, guild):
        if member.id not in self.bot.user_data:
            self.bot.user_data[member.id] = {'money': 200, 'daily': '', 'title': '', 'exp': 0, 'perms': {}, 'badges':[], "waifu":{}, "warnings": defaultdict(list), "reminders":[], 'places':{1:"", 2:"", 3:"", 4:"", 5:"", 6:"", 7:"", 8:""}, "tutorial": False}
            await self.bot.query_executer("INSERT INTO necrobot.Users VALUES ($1, 200, 0, '          ', '', '', 'False');", member.id)
            await self.bot.query_executer("INSERT INTO necrobot.Badges VALUES ($1, 1, ''), ($1, 2, ''), ($1, 3, ''), ($1, 4, ''), ($1, 5, ''), ($1, 6, ''), ($1, 7, ''), ($1, 8, '');", member.id)

        if not guild:
            return

        if isinstance(member, discord.User):
            member = guild.get_member(member.id)

        if guild.id not in self.bot.user_data[member.id]["perms"]:
            if any(self.bot.user_data[member.id]["perms"][x] == 7 for x in self.bot.user_data[member.id]["perms"]):
                self.bot.user_data[member.id]["perms"][guild.id] = 7
            elif any(self.bot.user_data[member.id]["perms"][x] == 6 for x in self.bot.user_data[member.id]["perms"]):
                self.bot.user_data[member.id]["perms"][guild.id] = 6
            elif member.id == guild.owner.id:
                self.bot.user_data[member.id]["perms"][guild.id] = 5
            elif member.guild_permissions.administrator:
                self.bot.user_data[member.id]["perms"][guild.id] = 4
            else:
                self.bot.user_data[member.id]["perms"][guild.id] = 0

            await self.bot.query_executer("INSERT INTO necrobot.Permissions VALUES ($1,$2,$3);", guild.id, member.id, self.bot.user_data[member.id]["perms"][guild.id])

        if guild.id not in self.bot.user_data[member.id]["waifu"]:
            self.bot.user_data[member.id]["waifu"][guild.id] = {"waifu-value":50, "waifu-claimer":"", "affinity":"", "heart-changes":0, "divorces":0, "waifus":[], "flowers":0, "gifts":{}}
            await self.bot.query_executer("INSERT INTO necrobot.Waifu VALUES ($1,$2,50,0,0,0,0,0);", member.id, guild.id)

    async def guild_checker(self, guild):
        channels = [channel.id for channel in guild.channels]
        roles = [role.id for role in guild.roles] 
        g = self.bot.server_data[guild.id]

        if g["broadcast-channel"] not in channels:
            g["broadcast-channel"] = ""
            await self.bot.query_executer("UPDATE necrobot.Guilds SET broadcast_channel = 0 WHERE guild_id = $1;", guild.id)

        if g["starboard-channel"] not in channels:
            g["starboard"] = ""
            await self.bot.query_executer("UPDATE necrobot.Guilds SET starboard_channel = 0 WHERE guild_id = $1;", guild.id)

        if g["welcome-channel"] not in channels:
            g["welcome-channel"] = ""
            await self.bot.query_executer("UPDATE necrobot.Guilds SET welcome_channel = 0 WHERE guild_id = $1;", guild.id)

        if g["automod"] not in channels:
            g["automod"] = ""
            await self.bot.query_executer("UPDATE necrobot.Guilds SET automod_channel = 0 WHERE guild_id = $1;", guild.id) 

        if g["mute"] not in roles:
            g["mute"] = "" 
            await self.bot.query_executer("UPDATE necrobot.Guilds SET mute = 0 WHERE guild_id = $1;", guild.id)

        for role in [role for role in g["self-roles"] if role not in roles]:
            g["self-roles"].remove(role)
            await self.bot.query_executer("DELETE FROM necrobot.SelfRoles WHERE guild_id = $1 AND id = $2;", guild.id, role)

        try:
            invites = await guild.invites()
            for invite in invites:
                await self.bot.query_executer("""
                    INSERT INTO necrobot.Invites as inv VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (id)
                    DO UPDATE SET uses = $4 WHERE inv.id = $1""",
                    invite.id, guild.id, invite.url, invite.uses, invite.inviter.id
                )
        except (discord.Forbidden, AttributeError):
            pass

    async def reminder_task(self, user_id, reminder, time):
        try:
            await asyncio.sleep(time)
        except asyncio.CancelledError:
            return

        try:
            user = self.bot.get_user(user_id)
            channel = self.bot.get_channel(reminder["channel"])
            await channel.send(f":alarm_clock: | {user.mention} reminder: **{reminder['text']}**")

            r = next((item for item in self.bot.user_data[user_id]["reminders"] if item["start"] == reminder["start"]), None)
            self.bot.user_data[user_id]["reminders"].remove(r)
            await self.bot.query_executer("DELETE FROM necrobot.Reminders WHERE start_date = $1 AND user_id = $2", r["start"], user_id)
        except Exception as e:
            await self.bot.get_channel(415169176693506048).send(f"Reminder **{reminder[:30]}** has failed:\n{e}")

def setup(bot):
    bot.add_cog(Meta(bot))
