# Commands Listed for Potential Removal

## mute
* Native Discord Alternative: Timeout

Mutes are no longer necessary as discord now provides a native timeout function. The only
thing that discord timeout cannot do is allow users to type in only certain channels. Additionally
timeouts only restrict one's ability to type but not to view a channel.

Impacts:
* mute
* unmute
* mute role
* mute role create
* mute task
* mute events

## ban
* Native Discord Alternative: Bans

Discord has always supported bans, this command was redudant the day it was created.

Impacts
* ban

## rename
* Native Discord Alternative: Edit Nickname

Same as with ban

Impacts
* rename

## permissions
* Native Discord Alternative: Slash Commands

The permission system as a whole was meant as a way to dissociate the bot commands from the standard 
server permissions. A user could then hold no power over the server and stil be able to take moderation 
actions. Now that slash commands offer this dissociation natively there no need for this complicated system. 
As such it will need to be phased out eventually and replaced entirely with slash command default
permissions.

## bmp convert
* Native Discord Alternative: Context Menu

Instead of automatically converting pictures add a context menu command to allow a user to select
a message from which they want to convert the attachements.

## bot dm delete
* Native Discord Alternative: Context Menu

Instead of using a reaction based flow to delete a bot DM use a context menu to allow a user
to select a message to delete in DMs.

## starboard force
* Native Discord Alternative: Context Menu

Instead of using a command to force a message to starboard use a context menu to make it easier
for the user to select which message they want to force.


