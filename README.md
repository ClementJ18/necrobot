# NecroBot

NecroBot has two very specific reason to be, it is meant to increase the Discord Moderation abilities tenfold but more importantly it is meant to be the first bot to support mod creators throughout the world. The bot will work hand in hand with modders all across Discord to help them showcase their content on their servers through rich embeds. NecroBot also contains it's own hierarchy system which means that server owners no longer need to give users specific permissions on their servers for them to use the bot, simply set their NecroBot permission level to be as you wish using `n!perms`. Not sure what permission level to use? Just have a look at `n!help` for help. Bot prefix is 'n![command]'.

__Hierachy Ladder:__
* 7: The Bot Smith - Bot Owner & Close Collaborators
* 6: NecroBot Admin - Trusted Members of the NecroBot server
* 5: Server Owner - Given to owners of a server using NecroBot
* 4: Admin - Trusted members of individual servers
* 3: Semi-Admin - "Trainee" admins
* 2: Mods - active, helpful and mature members of individual servers
* 1: Helpers - helpful members of individual servers
* 0: Users - members of servers

__User Pofile__ <br>
* **Money** - users can claim dailies and check their money
* **Badges** - users can put cool stickers on their profiles to show their favorite factions (BFME)

__Moderation Features__
* **Message Deletion Tracking** - tracks deleted messages and prints deleted messages in a separate channel
* **Message Edition Tracking** - tracks edits made to messages and prints the before and after in a separate channel
* **User Welcome** - welcome new users with a message and assigns them their own username as their server nickname
* **Invite Tracking** - track which user joins with what invite
* **Persistent Mutes** - user leaving while muted? When they join back they'll get their mute back

All commands can be seen on the discord provided below. This bot uses the rewrite branch of the d.py library written by Rapptz. In addition, the source is provided mostly as backup, running your own instance of the bot is not recommended as things tend to break and not all the code you need is present on this repo. 

Note: This readme has a tendency to be out of date. Join the server to see the latest version of capabilities of the bot.

Join to see in action: https://discord.gg/sce7jmB <br>

## Dev stuff
```
python3 -m black bot.py rings/ tests/ -l 110
```

