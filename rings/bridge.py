import discord
from discord.ext import commands

from rings.utils.utils import BotError, react_menu
from rings.utils.config import MU_Username, MU_Password
from rings.utils.converters import MemberConverter, MUConverter
from rings.utils.checks import mu_moderator, mu_moderator_check, guild_only

import re
import asyncio
import logging
import traceback
from bs4 import BeautifulSoup
from robobrowser.forms.form import Form

class Bridge(commands.Cog):
    """A cog for all commands specific to certain servers."""
    def __init__(self, bot):
        self.bot = bot
        self.mu_channels = [722040731946057789, 722474242762997868]
        self.cookies = False
        self.in_process = []
        self.task = self.bot.loop.create_task(self.post_task())
        self.mapping = {
            "angmar": {"id": 687748138345169075, "url": "https://modding-union.com/index.php/topic,33016.0.html"},
            "erebor": {"id": 687748357543952417, "url": "https://modding-union.com/index.php/topic,31202.0.html"},
            "gondor": {"id": 687747730684117012, "url": "https://modding-union.com/index.php/topic,30434.0.html"},
            "imladris": {"id": 687748566105849890, "url": "https://modding-union.com/index.php/topic,33678.0.html"},
            "isengard": {"id": 687748680182530086, "url": "https://modding-union.com/index.php/topic,30436.0.html"},
            "lothlorien": {"id": 687748760054661152, "url": "https://modding-union.com/index.php/topic,32089.0.html"},
            "mm": {"id": 688040356184588423, "url": ""},
            "mordor": {"id": 687749364692549651, "url": "https://modding-union.com/index.php/topic,30433.0.html"},
            "rohan": {"id": 687747731716177930, "url": "https://modding-union.com/index.php/topic,30435.0.html"},
            "eothain": {"id": 361473129253568513, "url": "https://modding-union.com/index.php/topic,30438.0.html"}, #CAH
            "onering": {"id": 342033729637711872, "url": "https://modding-union.com/index.php/topic,30437.0.html"}, #WotR
            "LUL": {"id": 778021945685704724, "url": "https://modding-union.com/index.php/topic,31224.0.html"}, #Audio
            "mu": {"id": 733692917318942801, "url": "https://modding-union.com/index.php/topic,35939.0.html"}, #Horde Maps
            "edain": {"id": 339025957136629772, "url": "https://modding-union.com/index.php/topic,33017.0.html"}, #General
            "dwarf_f": {"id": 778019875120742400, "url": "https://modding-union.com/index.php/topic,30440.0.html"}, #Maps
            "gildor": {"id": 340577178192445441, "url": "https://modding-union.com/index.php/topic,30439.0.html"}, # AI

        }

    
    #######################################################################
    ## Cog Functions
    #######################################################################
    
    def cog_unload(self):
        self.task.cancel()
        
    #######################################################################
    ## Functions
    #######################################################################
        
    async def post_task(self):
        while True:
            try:
                post = await self.bot.queued_posts.get()
                await post["message"].remove_reaction("\N{SLEEPING SYMBOL}", post["message"].guild.me)
                await self.mu_poster(post)
                await asyncio.sleep(120)
            except Exception as e:
                await post["message"].channel.send(f":negative_squared_cross_mark: | Error while sending: {e}")
                self.bot.pending_posts[post["message"].id] = post
                await post["message"].remove_reaction("\N{GEAR}", post["message"].guild.me)
                error_traceback = " ".join(traceback.format_exception(type(e), e, e.__traceback__, chain=True))
                logging.error(error_traceback) 
        
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
        form["cookielength"].value = '-1'
        
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
                await self.mu_poster(pending, retry+1)
            else:
                raise ValueError(f"Retried three times, unable to get form for {pending['message'].id}")

        form["message"].value = pending["content"]

        # del form.fields["attachment[]"]
        del form.fields["preview"]
        
        if pending["message"].channel.id == 722040731946057789:
            await self.bot.get_bot_channel().send(f"Payload sent. {form.serialize().data}") #dud debug test
        else: 
            await self.submit_form(form) #actual submit
        
        await pending["message"].delete()
        
    async def mu_parser(self, message, react=True):
        regex = r"https:\/\/modding-union\.com\/index\.php(?:\/|\?)topic(?:=|,)([0-9]*)\S*"
        match = re.search(regex, message.content)
        if match is None:
            if (await self.bot.db.get_permission(message.author.id, message.guild.id)) == 0 and not message.author.bot:
                await message.delete()
                await message.channel.send(f"{message.author.mention} | Could not find a valid thread url", delete_after=10)
            
            return
            
        url_template = "https://modding-union.com/index.php?action=post;topic={}"   
        thread = url_template.format(match.group(1))
        text = message.content.split(match.group(0))[-1].strip()
        
        if text == "":
            await message.delete()
            await message.channel.send(f"{message.author.mention} | Cannot send an empty message")
            return
        
        if react:
            await message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
            await message.add_reaction("\N{NEGATIVE SQUARED CROSS MARK}")
        
        self.bot.pending_posts[message.id] = {
            "message": message,
            "url": thread,
            "text": text,
            "thread": match.group(0)
        } 
    
    #######################################################################
    ## Commands
    #######################################################################
    
    @commands.group(invoke_without_command=True, enabled=False, hidden=True)
    @guild_only(327175434754326539)
    async def mu(self, ctx, user : MUConverter = None):
        """Get info about the number of posts a user has made and their username.
        
        {usage}
        
        __Examples__
        `{pre}mu` - get info about your own MU account
        `{pre}mu @NecroBot` - get info about necrobot's MU account
        """
        if user is None:
            user = ctx.author
            
        username = await self.bot.db.query(
            "SELECT (username, active) FROM necrobot.MU_Users WHERE user_id = $1",
            user.id, fetchval=True
        )
        
        if not username:
            raise BotError("This user is not currently registered to use the MU-Discord system.")
            
        posts = await self.bot.db.query(
            """SELECT post_date, ARRAY_AGG((url, approver_id)) FROM necrobot.MU WHERE user_id = $1 AND guild_id = $2 
            GROUP BY post_date ORDER BY post_date DESC""",
            user.id, ctx.guild.id    
        )
        
        total = await self.bot.db.query(
            "SELECT COUNT(url) FROM necrobot.MU WHERE user_id = $1 AND guild_id = $2",
            user.id, ctx.guild.id, fetchval=True    
        )
        
        def embed_maker(index, entries):
            embed = discord.Embed(
                title=f"{user.display_name} ({index[0]}/{index[1]})", 
                description=f"Username: {username[0]}\nStatus: {'Active' if username[1] else 'Banned'}\nTotal Posts: {total}",
                colour=self.bot.bot_color
            )
            
            embed.set_footer(**self.bot.bot_footer)
            
            for entry in entries:
                threads = []
                for url, approver in reversed(entry[1]):
                    approver_obj = ctx.guild.get_member(approver)
                    threads.append(f"[{url.split('#')[-1]}]({url}) - {approver_obj.mention if approver_obj is not None else 'User has left'}")
                
                embed.add_field(name=str(entry[0]), value="\n".join(threads), inline=False)
                
            return embed
        
        await react_menu(ctx, posts, 5, embed_maker)
    
    @mu.command(name="register")
    @guild_only(327175434754326539)    
    async def mu_register(self, ctx, username : str = None):
        """Register yourself to use the bot's modding-union capabilities. This forces you to pick a name and keep it, once
        you've registered your name you won't be able to change it without admin assistance so pick it with care. Names are
        on a first come first served basis, if you want a specific username get it before someone else does
        
        {usage}
        
        __Examples__
        `{pre}mu register Necro` - register yourself as user Necro
        `{pre}mu register` - see all registered users
        """
        if username is None:
            users = await self.bot.db.query(
                "SELECT user_id, username FROM necrobot.MU_Users WHERE active = True"    
            )
            
            def embed_maker(index, entries):
                string = "​"
                for user_id, username in entries:
                    user = self.bot.get_user(user_id)
                    if user is not None:
                        string += f"{user.mention} - {username}\n"
                        
                embed = discord.Embed(
                    title=f"MU Users ({index[0]}/{index[1]})", 
                    description=string,
                    colour=self.bot.bot_color
                )
            
                embed.set_footer(**self.bot.bot_footer)
                
                return embed
            
            return await react_menu(ctx, users, 10, embed_maker)
        
        if len(username) > 200:
            raise BotError("Username too long, please keep the username below 200 characters")
        
        if username.lower() in self.in_process:
            raise BotError("A registration for that nickname is currently in progress. Please wait for it to complete, if the registration successfully completed please pick another nickname.")
            
        already_registered = await self.bot.db.query(
            "SELECT * FROM necrobot.MU_Users WHERE user_id = $1 OR username_lower = $2",
            ctx.author.id, username.lower()    
        )
        
        if already_registered:
            raise BotError("You are already registered or that username is taken.")
        
        self.in_process.append(username.lower())
        msg = await ctx.send(f"By registering to use the bot's MU-Discord communication service you agree to the following forum rules: <https://modding-union.com/index.php/topic,30385.0.html>. If you break these rules, access to the channel may be restricted or taken away. React with :white_check_mark: if you agree or with :negative_squared_cross_mark: if you do not agree.")

        async def cleanup():
            await msg.edit(content=":negative_squared_cross_mark: | User was too slow, please react within 5 minutes next time.")
            await msg.clear_reactions()
            self.in_process.remove(username.lower())
            

        result = await self.bot.confirmation_menu(msg, ctx.author, cleanup=cleanup)
        if result:
            await self.bot.db.query(
                "INSERT INTO necrobot.MU_Users VALUES($1, $2, $3, True)", 
                ctx.author.id, username, username.lower(), 
            )
            await msg.edit(content=":white_check_mark: | You have now succesfully registered to the bot's modding union channel. You may now post in it.")
        else:
            await msg.edit(content=":negative_squared_cross_mark: | User did not agree to forum rules.")

        self.in_process.remove(username.lower())

    @mu.command(name="rename")
    @guild_only(327175434754326539)
    @mu_moderator_check()
    async def mu_rename(self, ctx, user : MemberConverter, new_username : str):
        """Rename users, use sparingly. This command can only be used by forum moderators.
        
        {usage}
        
        __Examples__
        `{pre}mu rename @Necro NotNecro` - rename user Necro to NotNecro on their MU profile
        """
        try:
            await self.bot.db.query(
                "UPDATE FROM necrobot.MU_Users SET username=$1, username_lower=$2 WHERE user_id=$3", 
                new_username, new_username.lower(), user.id
            )
            await ctx.send(":white_check_mark: | MU username successfully changed.")
        except:
            raise BotError("That username is already taken.")
            
    @mu.command(name="ban")
    @guild_only(327175434754326539)
    @mu_moderator_check()
    async def mu_ban(self, ctx, *users : MemberConverter):
        """Ban users from using the system, they will still be registered but unable to use the system. This
        command can only be used by forum moderators.
        
        {usage}
        
        __Examples__
        `{pre}mu ban @Necro @Necrobot` - ban both users
        """
        await self.bot.db.query(
            "UPDATE necrobot.MU_Users SET active=False WHERE user_id = any($1)",
            [user.id for user in users]    
        )
        
        await ctx.send(":white_check_mark: | All users banned")
        
    @mu.command(name="unban")
    @guild_only(327175434754326539)
    @mu_moderator_check()
    async def mu_unban(self, ctx, *users : MemberConverter):
        """Unban users from the system, they will be able to once again use their accounts and create posts. This
        command can only be used by forum moderators.
        
        {usage}
        
        __Examples__
        `{pre}mu unban @Necro @Necrobot` - unban both users
        """
        await self.bot.db.query(
            "UPDATE necrobot.MU_Users SET active=True WHERE user_id = any($1)",
            [user.id for user in users]    
        )
        
        await ctx.send(":white_check_mark: | All users unbanned")

    @mu.command(name="pending")
    @guild_only(327175434754326539)
    async def mu_pending(self, ctx, user : MUConverter = None):
        """List the posts currently waiting for approval with their contents and the thread they are going 
        to be posted to. Potentially list all the pending threads for a single user.
        
        {usage}
        
        __Examples__
        `{pre}mu pending` - list all pending posts
        `{pre}mu pending Necro` - list all pending posts for Necro
        
        """
        if user is not None:
            messages = [x for x in self.bot.pending_posts.values() if x["message"].author.id == user.id]
        else:
            messages = list(self.bot.pending_posts.values())
            
        def embed_maker(index, entry):
            user = entry["message"].author
            
            embed = discord.Embed(
                title=f"{user.display_name} ({index[0]}/{index[1]})", 
                description=entry["text"],
                colour=self.bot.bot_color
            )
            
            embed.add_field(name="Thread", value=entry["thread"])
            embed.set_footer(**self.bot.bot_footer)
            
            return embed
            
        await react_menu(ctx, messages, 1, embed_maker)
        
    @mu.command(name="denied")
    @guild_only(327175434754326539)
    async def mu_denied(self, ctx, user : MUConverter = None):
        """List the posts recently denied with their contents and the thread they were going 
        to be posted to. Potentially list all the recently denied threads for a single user.
        
        {usage}
        
        __Examples__
        `{pre}mu denied` - list all pending posts
        `{pre}mu denied Necro` - list all pending posts for Necro
        
        """
        if user is not None:
            messages = [x for x in self.bot.denied_posts if x["message"].author.id == user.id]
        else:
            messages = self.bot.denied_posts
            
        def embed_maker(index, entry):
            user = entry["message"].author
            
            embed = discord.Embed(
                title=f"{user.display_name} ({index[0]}/{index[1]})", 
                description=entry["text"],
                colour=self.bot.bot_color
            )
            
            embed.add_field(name="Thread", value=entry["thread"])
            
            denier = self.bot.get_user(entry["denier"])
            embed.add_field(name="Denier", value=denier.mention if denier else 'User Left')
            embed.set_footer(**self.bot.bot_footer)
            
            return embed
            
        await react_menu(ctx, messages, 1, embed_maker)
        
    #######################################################################
    ## Events
    #######################################################################
        
    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        if payload.message_id in self.bot.pending_posts:
            self.bot.pending_posts[payload.message_id]["message"]._update(payload.data)
            self.bot.pending_posts[payload.message_id]["content"] = self.bot.pending_posts[payload.message_id]["message"].content
            
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
        
        perms = await self.bot.db.get_permission(message.author.id, message.guild.id)
        if perms > 0:
            return

        self.bot.pending_posts[message.id] = {"message": message, "content": message.content}

        for reaction in self.mapping:
            reaction_id = self.mapping[reaction]["id"]
            await message.add_reaction(f"{reaction}:{reaction_id}")
        
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if self.bot.blacklist_check(payload.user_id):
            return
        
        if not payload.channel_id in self.mu_channels:
            return
            
        if not payload.message_id in self.bot.pending_posts:
            return

        if not payload.user_id == 241942232867799040:
            return

        if not payload.emoji.name in self.mapping:
            return

        post = self.bot.pending_posts.pop(payload.message_id)
        await post["message"].clear_reactions()
        await post["message"].add_reaction("\N{GEAR}")
        await post["message"].add_reaction("\N{SLEEPING SYMBOL}")
        post["approver"] = payload.user_id
        post["url"] = self.mapping[payload.emoji.name]["url"]
        await self.bot.queued_posts.put(post)

            
        # ids = mu_moderator(self.bot.get_guild(payload.guild_id))
        # if str(payload.emoji) == "\N{WHITE HEAVY CHECK MARK}":
        #     if payload.user_id in ids:
        #         post = self.bot.pending_posts.pop(payload.message_id)
        #         await post["message"].add_reaction("\N{GEAR}")
        #         await post["message"].add_reaction("\N{SLEEPING SYMBOL}")
        #         post["approver"] = payload.user_id
        #         await self.bot.queued_posts.put(post)
        # elif str(payload.emoji) == "\N{NEGATIVE SQUARED CROSS MARK}":
        #     ids.append(self.bot.pending_posts[payload.message_id]["message"].author.id)
        #     if payload.user_id in ids:
        #         post = self.bot.pending_posts.pop(payload.message_id)
        #         post["denier"] = payload.user_id
        #         self.bot.denied_posts.append(post)
        #         await post["message"].delete() 
 
def setup(bot):
    bot.add_cog(Bridge(bot))
