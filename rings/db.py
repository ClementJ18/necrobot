import discord
from discord.ext import commands

from rings.utils.config import dbpass, dbusername

import asyncpg
import psycopg2
import traceback
from datetime import datetime
from psycopg2.extras import RealDictCursor

class DatabaseError(Exception):
    def __init__(self, message, query = None, args = tuple()):
        super().__init__(message)
        self.message = message
        self.query = query
        self.args = args
        
    def embed(self, bot):
        formatted = traceback.format_exception(type(self), self, self.__traceback__, chain=False)
        msg = f"```py\n{' '.join(formatted)}\n```"
        
        embed = discord.Embed(title="DB Error", description=msg, colour=bot.bot_color)
        embed.add_field(name='Event', value=self.message, inline=False)
        embed.add_field(name="Query", value=self.query, inline=False)
        embed.add_field(name="Arguments", value=self.args, inline=False)
        embed.set_footer(**bot.bot_footer)
        
        return embed
        
    def __str__(self):
        return self.message

class Database(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    def math_builder(self, arg, pos, update, add):
        if update is not None:
            return f"${pos}"
        
        if add is not None:
            return f"{arg} + ${pos}"
        
        raise DatabaseError("No operation mode specified for update")
        
    def guild_builder(self, guild, pos):
        if guild is None:
            return ""
        
        return f"AND guild_id = ${pos}"
    
    async def create_pool(self):
        self.bot.pool = await asyncpg.create_pool(database="postgres", user=dbusername, password=dbpass)
        
    async def get_conn(self):
        if self.bot.pool is None:
            await self.create_pool()
            
        return await self.bot.pool.acquire()
        
    async def get_money(self, user_id):
        return await self.query(
            "SELECT necroins FROM necrobot.Users WHERE user_id = $1", 
            user_id, fetchval=True
        )
        
    async def update_money(self, user_id, *, update=None, add=None):
        query = "UPDATE necrobot.Users SET necroins = {} WHERE user_id = $1 RETURNING necroins".format(
            self.math_builder('necroins', 2, update, add), 
        )
        
        return await self.query(query, user_id, update if update is not None else add)
        
    async def transfer_money(self, payer_id, amount, payee_id):
        conn = await self.get_conn()
        
        async with conn.transaction():
            await self.query(
                "UPDATE necrobot.Users SET necroins = necroins - $2 WHERE user_id = $1",
                payer_id, amount, cn=conn    
            )
            
            await self.query(
                "UPDATE necrobot.Users SET necroins = necroins + $2 WHERE user_id = $1",
                payee_id, amount, cn=conn    
            )
            
        await self.bot.pool.release(conn)
        
    async def get_user(self, user_id):
        return await self.query(
            "SELECT * FROM necrobot.Users WHERE user_id = $1",
            user_id    
        )
            
    async def get_permission(self, user_id, guild_id = None):
        if guild_id is None:
            query = "SELECT guild_id, level FROM necrobot.Permissions WHERE user_id = $1"
            return await self.query(query, user_id)
        
        query = "SELECT level FROM necrobot.Permissions WHERE user_id = $1 AND guild_id = $2"
        return await self.query(query, user_id, guild_id, fetchval=True)
        
    async def compare_user_permission(self, user_id, guild_id, compared_user):
        #negative number: user_id has lower permissions than compared users
        return await self.query(
            """SELECT u1.level - u2.level FROM necrobot.Permissions u1, necrobot.Permissions u2
            WHERE u1.user_id = $1 AND u2.user_id = $2 
            AND u1.guild_id = $3 AND u2.guild_id = $3""",
            user_id, compared_user, guild_id, fetchval=True    
        )
        
    async def is_admin(self, user_id):
        perms = await self.get_permission(user_id)
        return any(x["level"] >= 6 for x in perms)
        
    async def update_permission(self, user_id, guild_id=None, *, update=None, add=None):        
        if guild_id is None:
            query = "UPDATE necrobot.Permissions SET level = {} WHERE user_id = $1 RETURNING level".format(
                self.math_builder('level', 2, update, add), 
            )
            return await self.query(query, user_id, update if update is not None else add)
        
        query = "UPDATE necrobot.Permissions SET level = {} WHERE user_id = $1 AND guild_id = $2 RETURNING level".format(
            self.math_builder('level', 3, update, add), 
        )
        return await self.query(query, user_id, guild_id, update if update is not None else add)
        
    async def insert_permission(self, user_id, guild_id, level):
        await self.query(
            "INSERT INTO necrobot.Permissions VALUES ($1,$2,$3)",
            guild_id, user_id, level    
        )
        
    async def delete_permission(self, user_id, guild_id):
        await self.query(
            "DELETE FROM necrobot.Permissions WHERE user_id = $1 AND guild_id = $2",
            user_id, guild_id    
        )
        
    async def get_title(self, user_id):
        return await self.query(
            "SELECT title FROM necrobot.Users WHERE user_id = $1", 
            user_id, fetchval=True
        )
        
    async def update_title(self, user_id, title):
        return await self.query(
            "UPDATE necrobot.Users SET title = $1 WHERE user_id = $2 RETURNING title",
            title, user_id, fetchval=True    
        )
        
    async def update_warning_setting(self, guild_id, setting):
        await self.query(
            "UPDATE necrobot.Guilds SET pm_warning = $1 WHERE guild_id = $2",
            setting, guild_id    
        )
        
        self.bot.guild_data[guild_id]["pm-warning"] = setting
        
    async def insert_warning(self, user_id, issuer_id, guild_id, message):
        return await self.query(
            """
            INSERT INTO necrobot.Warnings (user_id, issuer_id, guild_id, warning_content) 
            VALUES ($1, $2, $3, $4)
            RETURNING warn_id;
            """, 
            user_id, issuer_id, guild_id, message, fetchval=True
        )
        
    async def delete_warning(self, warning_id, guild_id):
        return await self.query(
            "DELETE FROM necrobot.Warnings WHERE warn_id = $1 AND guild_id = $2 RETURNING user_id",
            warning_id, guild_id, fetchval=True
        )
        
    async def insert_disabled(self, guild_id, *commands):
        await self.query(
            "INSERT INTO necrobot.Disabled VALUES ($1, $2)",
            [(guild_id, x) for x in commands], many=True    
        )
        self.bot.guild_data[guild_id]["disabled"].extend(commands)
        
    async def delete_disabled(self, guild_id, *commands):
        await self.query(
            "DELETE FROM necrobot.Disabled WHERE guild_id = $1 AND command = any($2)",
            guild_id, commands    
        )        
        self.bot.guild_data[guild_id]["disabled"] = [x for x in self.bot.guild_data[guild_id]["disabled"] if x not in commands]

    async def get_badges(self, user_id, *, badge = None, spot = None):
        if badge is None and spot is None:
            return await self.query(
                """SELECT s.name, s.file_name, b.spot FROM necrobot.Badges b, necrobot.BadgeShop s
                WHERE b.user_id = $1 AND s.name = b.badge""",
                user_id    
            )
        
        if badge is not None and spot is not None:
            return await self.query(
                """SELECT s.name, s.file_name, b.spot FROM necrobot.Badges b, necrobot.BadgeShop s
                WHERE B.user_id = $1 AND b.spot = $3 AND s.name = $2 AND s.name = b.badge""",
                user_id, badge, spot
            )
        
        if badge is not None:
            return await self.query(
                """SELECT s.name, s.file_name, b.spot FROM necrobot.Badges b, necrobot.BadgeShop s
                WHERE s.name = b.badge AND s.name = $1 AND b.user_id = $2""",
                badge, user_id    
            )
        
        if spot is not None:
            return await self.query(
                """SELECT s.name, s.file_name, b.spot FROM necrobot.Badges b, necrobot.BadgeShop s
                WHERE s.name = b.badge AND b.spot = $1 AND b.user_id = $2""",
                spot, user_id
            )
        
        raise DatabaseError("Something went wrong with badge selection")
    
    async def insert_badge(self, user_id, badge, spot = 0):
        await self.query(
            "INSERT INTO necrobot.Badges VALUES ($1, $2, $3)",
            user_id, badge, spot
        )
        
    async def delete_badge(self, user_id, badge = None):
        if badge is None:
            await self.query(
                "DELETE FROM necrobot.Badges WHERE user_id = $1",
                user_id
            )
        else:
            await self.query(
                "DELETE FROM necrobot.Badges WHERE user_id = $1 AND badge = $2",
                user_id, badge
            )
        
    async def update_spot_badge(self, user_id, spot, badge = None):
        await self.query(
            "UPDATE necrobot.Badges SET spot = 0 WHERE spot = $1 AND user_id = $2",
            spot, user_id
        )
        
        if badge is not None:
            await self.query(
                "UPDATE necrobot.Badges SET spot = $1 WHERE badge = $2 AND user_id = $3",
                spot, badge, user_id    
            )      
        
    async def get_badge_from_shop(self, *, name = None):
        if name is None:
            return await self.query(
                "SELECT * FROM necrobot.BadgeShop"    
            )            
        
        return await self.query(
            "SELECT * FROM necrobot.BadgeShop WHERE name = $1",
            name    
        )
        
    async def get_tutorial(self, user_id):
        return await self.query(
            "SELECT tutorial FROM necrobot.Users WHERE user_id = $1",
            user_id, fetchval=True
        )
                
    async def update_tutorial(self, user_id, value = True):
        await self.query(
            "UPDATE necrobot.Users SET tutorial = $2 WHERE user_id = $1",
            user_id, value
        )
        
    # mixup with column names
    # - 'starred' in the code is the message that has received the stars
    # - 'starred' in the db is the message that ctx.send to the starboard
    async def add_star(self, starred, message, stars):
        await self.query(
            "INSERT INTO necrobot.Starred VALUES ($1, $2, $3, $4, $5, $6);",
            starred.id, message.id, starred.guild.id, starred.author.id, stars, starred.jump_url
        )

    async def update_stars(self, message_id, user_id, increment):
        await self.query(
            "UPDATE necrobot.Starred SET stars = stars + $3 WHERE message_id = $1 AND user_id != $2",
            message_id, user_id, increment
        )
        
    async def update_prefix(self, guild_id, prefix):
        await self.bot.db.query(
            "UPDATE necrobot.Guilds SET prefix = $1 WHERE guild_id = $2",
            prefix, guild_id    
        )
        self.bot.guild_data[guild_id]["prefix"] = prefix
        
    async def update_starboard_channel(self, guild_id, channel_id = 0):
        await self.query(
            "UPDATE necrobot.Guilds SET starboard_channel = $2 WHERE guild_id = $1;", 
            guild_id, channel_id if channel_id else 0
        )
        self.bot.guild_data[guild_id]["starboard-channel"] = channel_id
        
    async def update_starboard_limit(self, guild_id, limit = 1):
        await self.query(
            "UPDATE necrobot.Guilds SET starboard_limit = $2 WHERE guild_id = $1",
            guild_id, limit    
        )
        self.bot.guild_data[guild_id]["starboard-limit"] = limit
        
    async def update_greeting_channel(self, guild_id, channel_id = 0):
        await self.query(
            "UPDATE necrobot.Guilds SET welcome_channel = $2 WHERE guild_id = $1;", 
            guild_id, channel_id if channel_id else 0
        )
        self.bot.guild_data[guild_id]["welcome-channel"] = channel_id
        
    async def update_welcome_message(self, guild_id, message):
        await self.query(
            "UPDATE necrobot.Guilds SET welcome_message = $1 WHERE guild_id = $2",
            message, guild_id    
        )
        self.bot.guild_data[guild_id]["welcome"] = message
        
    async def update_farewell_message(self, guild_id, message):
        await self.query(
            "UPDATE necrobot.Guilds SET goodbye_message = $1 WHERE guild_id = $2",
            message, guild_id    
        )
        
        self.bot.guild_data[guild_id]["goodbye"] = message

    async def update_automod_channel(self, guild_id, channel_id = 0):
        self.bot.guild_data[guild_id]["automod"] = channel_id
        await self.query(
            "UPDATE necrobot.Guilds SET automod_channel = $2 WHERE guild_id = $1;",
            guild_id, channel_id if channel_id else 0
        )
        
    async def insert_automod_ignore(self, guild_id, *objects_id):
        if not objects_id:
            return
            
        await self.query(
            "INSERT INTO necrobot.IgnoreAutomod VALUES($1, $2)",
            [(guild_id, x) for x in objects_id], many=True    
        )

        self.bot.guild_data[guild_id]["ignore-automod"].extend(objects_id)
        
    async def delete_automod_ignore(self, guild_id, *objects_id):
        if not objects_id:
            return
        
        await self.query(
            "DELETE FROM necrobot.IgnoreAutomod WHERE guild_id = $1 AND id = any($2)",
            guild_id, objects_id    
        )
        
        self.bot.guild_data[guild_id]["ignore-automod"] = [x for x in self.bot.guild_data[guild_id]["ignore-automod"] if x not in objects_id]
        
    async def insert_command_ignore(self, guild_id, *objects_id):
        if not objects_id:
            return
        
        await self.query(
            "INSERT INTO necrobot.IgnoreCommand VALUES($1, $2)",
            [(guild_id, x) for x in objects_id], many=True    
        )
        
        self.bot.guild_data[guild_id]["ignore-command"].extend(objects_id)
        
    async def delete_command_ignore(self, guild_id, *objects_id):
        if not objects_id:
            return

        await self.query(
            "DELETE FROM necrobot.IgnoreCommand WHERE guild_id = $1 AND id = any($2)",
            guild_id, objects_id    
        )
        
        self.bot.guild_data[guild_id]["ignore-command"] = [x for x in self.bot.guild_data[guild_id]["ignore-command"] if x not in objects_id]
        
    async def update_mute_role(self, guild_id, role_id = 0):
        await self.query(
            "UPDATE necrobot.Guilds SET mute = $2 WHERE guild_id = $1;", 
            guild_id, role_id
        )
        
        self.bot.guild_data[guild_id]["mute"] = role_id
        
    async def update_auto_role(self, guild_id, role_id = 0, timer = 0):
        await self.query(
            "UPDATE necrobot.Guilds SET auto_role = $2, auto_role_timer = $3 WHERE guild_id = $1;", 
            guild_id, role_id, timer
        )
        
        self.bot.guild_data[guild_id]["auto-role"] = role_id
        self.bot.guild_data[guild_id]["auto-role-timer"] = timer
        
    async def insert_self_roles(self, guild_id, *roles_id):
        if not roles_id:
            return
            
        await self.bot.db.query(
            "INSERT INTO necrobot.SelfRoles VALUES($1, $2)",
            [(guild_id, role_id) for role_id in roles_id], many=True  
        )
        
        self.bot.guild_data[guild_id]["self-roles"].extend(
            [x for x in roles_id if x not in self.bot.guild_data[guild_id]["self-roles"]]
        )
        
    async def delete_self_roles(self, guild_id, *roles_id):
        if not roles_id:
            return
            
        await self.query(
            "DELETE FROM necrobot.SelfRoles WHERE guild_id = $1 AND id = ANY($2);",
            guild_id, roles_id
        )
            
        self.bot.guild_data[guild_id]["self-roles"] = [
            x for x in self.bot.guild_data[guild_id]["self-roles"] if x not in roles_id
        ]
        
    async def insert_invite(self, invite):
        await self.query(
            "INSERT INTO necrobot.Invites VALUES($1, $2, $3, $4, $5)",
            invite.id, invite.guild.id, invite.url, invite.uses, invite.inviter.id if invite.inviter else 000
        )
    
    async def delete_invite(self, invite):
        await self.query(
            "DELETE FROM necrobot.Invites WHERE id=$1",
            invite.id    
        )
       
    async def update_invites(self, guild):
        try:
            invites = sorted(await guild.invites(), key=lambda x: x.created_at)
        except discord.Forbidden:
            return

        return_invite = None
        for invite in invites:
            changed = await self.query(
                "UPDATE necrobot.Invites SET uses = $2 WHERE id = $1 AND uses < $2 RETURNING url",
                invite.id, invite.uses
            )

            if changed and return_invite is None:
                return_invite = invite

        return return_invite

    async def sync_invites(self, guild):
        try:
            invites = sorted(await guild.invites(), key=lambda x: x.created_at)
        except discord.Forbidden:
            return

        #insert
        #update
        for invite in invites:
            await self.query(
                """
                    INSERT INTO necrobot.Invites as inv VALUES($1, $2, $3, $4, $5)
                    ON CONFLICT (id)
                    DO UPDATE SET uses = $4 WHERE inv.id = $1""",
                invite.id, guild.id, invite.url, invite.uses, invite.inviter.id if invite.inviter else 000, fetchval=True
            )

        #delete
        await self.query(
            "DELETE FROM necrobot.Invites WHERE NOT(id = ANY($1)) AND guild_id = $2",
            [x.id for x in invites], guild.id
        )
        
    async def get_reminders(self, user_id = None):
        if user_id is None:
            return await self.query(
                "SELECT * FROM necrobot.Reminders"    
            )
        
        return await self.query(
            "SELECT * FROM necrobot.Reminders WHERE user_id = $1",
            user_id
        )
            
    async def insert_reminder(self, user_id, channel_id, reminder, timer, start_date):
        return await self.query(
            """INSERT INTO necrobot.Reminders(user_id, channel_id, reminder, timer, start_date) 
            VALUES($1, $2, $3, $4, $5) RETURNING id""",
            user_id, channel_id, reminder, timer, start_date, fetchval = True    
        )
            
    async def delete_reminder(self, reminder_id):
        return await self.query(
            "DELETE FROM necrobot.Reminders WHERE id = $1 RETURNING id",
            reminder_id, fetchval=True    
        )
        
    async def get_leaderboard(self, guild_id):
        return (await self.query(
            "SELECT message, symbol FROM necrobot.Leaderboards WHERE guild_id = $1",
            guild_id
        ))[0]
        
    async def insert_leaderboard(self, guild_id):
        await self.query(
            """
            INSERT INTO necrobot.Leaderboards VALUES ($1, '', 'points') 
            ON CONFLICT (guild_id) DO NOTHING
            """,
            guild_id,     
        )
        
    async def update_leaderboard(self, guild_id, *, symbol = None, message = None):
        if not symbol is None:
            await self.query(
                "UPDATE necrobot.Leaderboards SET symbol=$1 WHERE guild_id=$2", 
                symbol, guild_id
            )
        elif not message is None:
            await self.query(
                "UPDATE necrobot.Leaderboards SET message=$1 WHERE guild_id=$2",
                message, guild_id    
            )    
        else:
            raise DatabaseError("No keyword selected")
               
    async def insert_leaderboard_member(self, guild_id, member_id):
        await self.query(
            "INSERT INTO necrobot.LeaderboardPoints VALUES($1, $2, 0) ON CONFLICT (user_id, guild_id) DO NOTHING", 
            member_id, guild_id
        )
        
    async def update_leaderboard_member(self, guild_id, member_id, point):
        await self.query(
            "UPDATE necrobot.LeaderboardPoints SET points = points + $1 WHERE user_id=$2 AND guild_id=$3", 
            point, member_id, guild_id
        )
        
    async def get_yt_rss(self, guild_id = None):
        if guild_id is not None:
            return await self.query(
                "SELECT * FROM necrobot.Youtube WHERE guild_id = $1", 
                guild_id
            )
        
        return await self.query("SELECT * FROM necrobot.Youtube")

    async def get_tw_rss(self, guild_id = None):
        if guild_id is not None:
            return await self.query(
                "SELECT * FROM necrobot.Twitch WHERE guild_id = $1", 
                guild_id
            )
        
        return await self.query("SELECT * FROM necrobot.Twitch")
            
    async def upsert_yt_rss(self, guild_id, channel_id, youtuber_id, youtuber_name):
        await self.query(
            """INSERT INTO necrobot.Youtube AS yt VALUES ($1, $2, $3, NOW(), '', $4) 
            ON CONFLICT (guild_id,youtuber_id) 
            DO UPDATE SET channel_id = $2, youtuber_name = $4 WHERE yt.guild_id = $1 AND yt.youtuber_id = $3""",
            guild_id, channel_id, youtuber_id, youtuber_name
        )

    async def upsert_tw_rss(self, guild_id, channel_id, twitch_id, twitch_name):
        await self.query(
            """INSERT INTO necrobot.Twitch AS tw VALUES ($1, $2, $3, NOW(), '', $4) 
            ON CONFLICT (guild_id,twitch_id) 
            DO UPDATE SET channel_id = $2, twitch_name = $4 WHERE tw.guild_id = $1 AND tw.twitch_id = $3""",
            guild_id, channel_id, twitch_id, twitch_name
        )
        
    async def update_yt_filter(self, guild_id, youtuber_name, text):
        return await self.bot.db.query(
            "UPDATE necrobot.Youtube SET filter = $3 WHERE guild_id = $1 and LOWER(youtuber_name) = LOWER($2) RETURNING youtuber_name", 
            guild_id, youtuber_name, text,
            fetchval=True
        )

    async def update_tw_filter(self, guild_id, twitch_name, text):
        return await self.bot.db.query(
            "UPDATE necrobot.Twitch SET filter = $3 WHERE guild_id = $1 and LOWER(twitch_name) = LOWER($2) RETURNING twitch_name", 
            guild_id, twitch_name, text,
            fetchval=True
        )
            
    async def update_yt_rss(self, guild_id = None):
        return await self.query(
            "UPDATE necrobot.Youtube SET last_update = NOW() RETURNING last_update",
            fetchval=True
        )

    async def update_tw_rss(self, guild_id = None):
        return await self.query(
            "UPDATE necrobot.Twitch SET last_update = NOW() RETURNING last_update",
            fetchval=True
        )
        
    async def delete_yt_rss_channel(self, guild_id, *, channel_id = None, youtuber_name = None):            
        if channel_id is not None:
            return await self.query(
                "DELETE FROM necrobot.Youtube WHERE guild_id = $1 AND channel_id = $2", 
                guild_id, channel_id
            )
            
        if youtuber_name is not None:
            return await self.query(
                "DELETE from necrobot.Youtube WHERE guild_id = $1 AND LOWER(youtuber_name) = LOWER($2)",
                guild_id, youtuber_name  
            )
            
        return await self.query(
            "DELETE FROM necrobot.Youtube WHERE guild_id = $1", 
            guild_id
        )

    async def delete_tw_rss_channel(self, guild_id, *, channel_id = None, twitch_name = None):            
        if channel_id is not None:
            return await self.query(
                "DELETE FROM necrobot.Twitch WHERE guild_id = $1 AND channel_id = $2", 
                guild_id, channel_id
            )
            
        if twitch_name is not None:
            return await self.query(
                "DELETE from necrobot.Twitch WHERE guild_id = $1 AND LOWER(twitch_name) = LOWER($2)",
                guild_id, twitch_name  
            )
            
        return await self.query(
            "DELETE FROM necrobot.Twitch WHERE guild_id = $1", 
            guild_id
        )

    async def query(self, query, *args, fetchval = False, many = False, cn = None, **kwargs):
        if cn is None:
            conn = await self.get_conn()
        else:
            conn = cn
                    
        try:
            if fetchval:
                result = await conn.fetchval(query, *args)
            elif many:
                result = await conn.executemany(query, *args)
            else:
                result = await conn.fetch(query, *args)
        except Exception as e:
            await self.bot.pool.release(conn)
            raise DatabaseError(str(e), query, args)
        
        if cn is None:
            await self.bot.pool.release(conn)
            
        return result

class SyncDatabase:
    def __init__(self):
        self.conn = psycopg2.connect(dbname="postgres", user=dbusername, password=dbpass, cursor_factory=RealDictCursor)
        self.cur = self.conn.cursor()
        
    def load_guilds(self):
        guilds = {}
        
        self.cur.execute("SELECT * FROM necrobot.Guilds;")
        for g in self.cur.fetchall():
            guilds[g["guild_id"]] = {
                "mute": g["mute"], 
                "automod":g["automod_channel"], 
                "welcome-channel":g["welcome_channel"], 
                "welcome":g["welcome_message"], 
                "goodbye":g["goodbye_message"], 
                "prefix":g["prefix"],
                "starboard-channel":g["starboard_channel"],
                "starboard-limit":g["starboard_limit"],
                "auto-role":g["auto_role"],
                "auto-role-timer":g["auto_role_timer"],
                "pm-warning": g["pm_warning"],
                "ignore-command":[],
                "ignore-automod":[],
                "disabled":[],
                "self-roles": [],
                "mutes": []
            }
            
        self.cur.execute("SELECT guild_id, array_agg(command) as commands FROM necrobot.Disabled GROUP BY guild_id;")
        for g in self.cur.fetchall():
            guilds[g["guild_id"]]["disabled"] = g["commands"]

        self.cur.execute("SELECT guild_id, array_agg(id) as ids FROM necrobot.IgnoreAutomod GROUP BY guild_id;")
        for g in self.cur.fetchall():
            guilds[g["guild_id"]]["ignore-automod"] = g["ids"]

        self.cur.execute("SELECT guild_id, array_agg(id) as ids FROM necrobot.IgnoreCommand GROUP BY guild_id;")
        for g in self.cur.fetchall():
            guilds[g["guild_id"]]["ignore-command"] = g["ids"]
            
        self.cur.execute("SELECT guild_id, array_agg(id) as roles FROM necrobot.SelfRoles GROUP BY guild_id;")
        for g in self.cur.fetchall():
            guilds[g["guild_id"]]["self-roles"] = g["roles"]
            
        return guilds
        
    def load_polls(self): 
        polls = {}
        self.cur.execute("SELECT message_id, votes, emoji_list FROM necrobot.Polls")
        for u in self.cur.fetchall():
            polls[u["message_id"]] = {'votes': u["votes"], 'voters':[], 'list': u["emoji_list"] if u["emoji_list"] else []}
            
        self.cur.execute("SELECT message_id, array_agg(user_id) as user_ids FROM necrobot.Votes GROUP BY message_id;")
        for u in self.cur.fetchall():
            polls[u["message_id"]]["voters"] = u["user_ids"]
            
        return polls

def setup(bot):
    bot.add_cog(Database(bot))
