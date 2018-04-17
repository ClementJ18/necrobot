import json

raw_user_data = json.load(open("rings/utils/data/user_data.json", "r"))
raw_server_data = json.load(open("rings/utils/data/server_data.json", "r"))

def get_users():
    user_query = """INSERT INTO necrobot.Users VALUES ({}, {}, {}, '{}', '{}', '{}', 'False');"""

    for user in raw_user_data:
        users = raw_user_data[user]
        print(user_query.format(user, users["money"], users["exp"], users["daily"], ",".join(users["badges"]), users["title"]))

def get_guilds():
    guild_query = """INSERT INTO necrobot.Guilds VALUES ({}, {}, {}, {}, '{}','{}', '{}', {}, '{}', {}, {}, {}, {}, 0);"""

    for guild in raw_server_data:
        if guild != "starred-messages":
            guilds = raw_server_data[guild]
            print(guild_query.format(guild, guilds["mute"] if guilds["mute"] != "" else 0 , guilds["automod"] if guilds["automod"] != "" else 0, guilds["welcome-channel"] if guilds["welcome-channel"] != "" else 0, guilds["welcome"].replace("'", "''"), guilds["goodbye"].replace("'", "''"), guilds["prefix"].replace("'", "''"), guilds["broadcast-channel"] if guilds["broadcast-channel"] != "" else 0, guilds["broadcast"].replace("'", "''"), guilds["broadcast-time"], guilds["starboard-channel"], guilds["starboard-limit"], guilds["auto-role"] if guilds["auto-role"] != "" else 0))

def get_disabled():
    disabled_query = """INSERT INTO necrobot.Disabled VALUES ({},'{}');"""

    for guild in raw_server_data:
            if guild != "starred-messages":
                for command in raw_server_data[guild]["disabled"]:
                    print(disabled_query.format(guild, command))

def get_ignore_automod():
    automod_query = """INSERT INTO necrobot.IgnoreAutomod VALUES ({},{});"""

    for guild in raw_server_data:
            if guild != "starred-messages":
                for id in raw_server_data[guild]["ignoreAutomod"]:
                    print(automod_query.format(guild, id))


def get_ignore_command():
    command_query = """INSERT INTO necrobot.IgnoreCommand VALUES ({},{});"""

    for guild in raw_server_data:
            if guild != "starred-messages":
                for id in raw_server_data[guild]["ignoreCommand"]:
                    print(command_query.format(guild, id))

def get_self_roles():
    self_query = """INSERT INTO necrobot.SelfRoles VALUES ({},{});"""

    for guild in raw_server_data:
            if guild != "starred-messages":
                for id in raw_server_data[guild]["selfRoles"]:
                    print(self_query.format(guild, id))

def get_tags():
    tags_query = """INSERT INTO necrobot.Tags VALUES ({}, '{}', '{}', {}, {}, '{}');"""

    for guild in raw_server_data:
        if guild != "starred-messages":
            for tag in raw_server_data[guild]["tags"]:
                tags = raw_server_data[guild]["tags"][tag]
                print(tags_query.format(guild, tag, tags["content"].replace("'", "''"), tags["owner"], tags["counter"], tags["created"]))

def get_perms():
    perms_query = """INSERT INTO necrobot.Permissions VALUES ({}, {}, {});"""
    for user in raw_user_data:
        for guild in raw_user_data[user]["perms"]:
            print(perms_query.format(guild, user, raw_user_data[user]["perms"][guild]))

def get_badges():
    badge_query = """INSERT INTO necrobot.Badges VALUES ({}, {}, '{}');"""

    for user in raw_user_data:
        for place in raw_user_data[user]["places"]:
            print(badge_query.format(user, place,raw_user_data[user]["places"][place] ))

def get_gifts():
    gift_query = """INSERT INTO necrobot.Gifts VALUES ({}, {}, '{}', {});"""

    for user in raw_user_data:
        for guild in raw_user_data[user]:
            if guild.isdigit():
                for gift in raw_user_data[user][guild]["gifts"]:
                    if raw_user_data[user][guild]["gifts"][gift] > 0:
                        print(gift_query.format(user, guild, gift, raw_user_data[user][guild]["gifts"][gift]))



def get_waifus():
    waifus_query = """INSERT INTO necrobot.Waifus VALUES ({}, {}, {});"""

    for user in raw_user_data:
        for guild in raw_user_data[user]:
            if guild.isdigit():
                for waifu in raw_user_data[user][guild]["waifus"]:
                    print(waifus_query.format(user, guild, waifu))



def get_waifu():
    waifu_query = """INSERT INTO necrobot.Waifu VALUES ({}, {}, {}, {}, {}, {}, {}, {});"""
    for user in raw_user_data:
        for guild in raw_user_data[user]:
            if guild.isdigit():
                waifu = raw_user_data[user][guild]
                print(waifu_query.format(user, guild, waifu["waifu-value"], waifu["waifu-claimer"], waifu["affinity"], waifu["heart-changes"], waifu["divorces"], waifu["flowers"]))

#guilds
get_guilds()
get_disabled()
get_ignore_automod()
get_ignore_command()
get_self_roles()
get_tags()
get_perms()

#users    
get_users()
get_badges()
get_gifts()
get_waifus()
get_waifu()
