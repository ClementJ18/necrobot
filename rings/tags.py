import discord
from discord.ext import commands

from rings.utils.utils import react_menu, BotError
from rings.db import DatabaseError

import re

class Tag(commands.Converter):
    async def convert(self, ctx, argument):
        argument = argument.lower()
        tag = await ctx.bot.db.query_executer("""
            SELECT t.name, t.content, t.owner_id, t.uses, t.created_at FROM necrobot.Tags t, necrobot.Aliases a 
            WHERE t.name = a.original AND a.alias = $1 AND a.guild_id = $2 AND t.guild_id = $2
            """, argument, ctx.guild.id)
        
        if not tag:
            raise commands.BadArgument(f"Tag {argument} not found.")
            
        return tag[0]

class Tags(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.restricted = [x.name for x in  self.tag.commands]
        
    #######################################################################
    ## Functions
    #######################################################################

    async def is_tag_owner(self, ctx, tag):
        if ctx.author.id == tag["owner_id"]:
            return True
        
        if await self.bot.db.get_permission(ctx.author.id, ctx.guild.id) >= 4:
            return True
        
        raise commands.CheckFailure("You don't have permissions to modify this tag")
        
    #######################################################################
    ## Commands
    #######################################################################

    @commands.group(invoke_without_command = True, aliases=["t","tags"])
    @commands.guild_only()
    async def tag(self, ctx, tag : Tag, *tag_args):
        """The base of the tag system. Also used to summoned tags through the [tag] argument. Tags can also
        be called by mentionning the bot, however tags that need arguments will not work with this. In addition,
        multi word tags need to be wraped in quotation marks when being created.
        
        {usage}
        
        __Example__
        `{pre}tag necro` - prints the content of the tag 'necro' given that it exists on this server"""
        arg_dict = dict()
        index = 0
        for arg in tag_args:
            arg_dict[f"arg{index}"] = arg
            index += 1

        tag_content = tag["content"]
        try:
            await ctx.send(
                tag_content.format(
                    server=ctx.guild, 
                    member=ctx.author, 
                    channel=ctx.channel, 
                    content=ctx.message.content,
                    **arg_dict
                )
            )

            await self.bot.db.query_executer(
                "UPDATE necrobot.Tags SET uses = uses + 1 WHERE guild_id = $1 AND name = $2", 
                ctx.guild.id, tag["name"]
            )
            
        except KeyError as e:
            raise BotError(f"Expecting the following argument: {e.args[0]}")

    @tag.command(name="add")
    @commands.guild_only()
    async def tag_add(self, ctx, tag, *, content):
        """Assigns the [text] passed through to the tag named [name]. A few reserved keywords can be used to render the 
        tag dynamic.
        
        `{{server.keyword}}`
        Represents the server
        __Keywords__
        `name` - name of the server
        `id` - id of the server
        `created_at` - UTC tag of the creation time of the server
        `member_count` - returns the number of member
        
        `{{member.keyword}}`
        Represents the user that called the tag
        __Keywords__
        `display_name` - the user nick if they have one, else the user's username
        `name` - the user's username
        `discriminator` - the user's discriminator (the 4 digits at the end)
        `joined_at` - specifies at what time the user joined the server
        `id` - user's id
        `mention` - mentions the user
        `created_at` - returns the creation time of the account
        
        `{{channel.keyword}}`
        Represents the channel the tag was summoned in
        __Keywords__
        `name` - channel name
        `id` - channel id
        `topic` - the channel's topic
        `mention` - returns a mention of the channel
        
        `{{content}}`
        Represents the content of the message
        
        `{{argx}}`
        Represents an argument you pass into the tag, replace x by the argument number starting from 0.
        E.g: `{pre}tag test [arg0] [arg1] [arg2]` 
        
        {usage}
        
        __Example__
        `{pre}tag add test1 {{server.name}} is cool` - creates a tag that will replace `{{server.name}}` by the name of the server it is summoned in
        `{pre}tag add test2 {{arg0}} {{arg1}}` - creates a tag that will replace arg0 and arg1 by the arguments passed
        """
        tag = tag.lower()
        if tag in self.restricted:
            raise BotError("Tag not created, tag name is a reserved keyword")
         
        try:   
            await self.bot.db.query_executer(
                "INSERT INTO necrobot.Tags(guild_id, name, content, owner_id) VALUES ($1, $2, $3, $4)", 
                ctx.guild.id, tag, content, ctx.author.id
            )
            
            await self.bot.db.query_executer(
                "INSERT INTO necrobot.Aliases VALUES ($1, $1, $2)",
                tag, ctx.guild.id
            )
            
            await ctx.send(f":white_check_mark: | Tag {tag} added")
        except DatabaseError:
            raise BotError("A tag with this name already exists")

    @tag.group(name="delete", invoke_without_command=True)
    @commands.guild_only()
    async def tag_delete(self, ctx, *, tag : Tag):
        """Deletes the tag [tag] if the users calling the command is its owner or a Server Admin (4+)
        
        {usage}
        
        __Example__
        `{pre}tag delete necro` - removes the tag 'necro' if you are the owner of if you have a permission level of 4+"""
        await self.is_tag_owner(ctx, tag)

        await self.bot.db.query_executer(
            "DELETE FROM necrobot.Tags WHERE guild_id = $1 AND name = $2",
            ctx.guild.id, tag["name"]    
        )
        await ctx.send(f":white_check_mark: | Tag {tag['name']} and its aliases removed")

    @tag_delete.command(name="alias")
    @commands.guild_only()
    async def tag_delete_alias(self, ctx, *, alias : str):
        """Remove the alias to a tag. Only Server Admins and the tag owner can remove aliases and they can 
        remove any aliases.

        {usage}

        __Examples__
        `{pre}tag delete alias necro1` - remove the alias "necro1"

        """
        try:
            tag = await Tag().convert(ctx, alias)
        except commands.BadArgument:
            raise commands.BadArgument(f"Alias {alias} does not exist.")

        await self.is_tag_owner(ctx, tag)

        await self.bot.db.query_executer(
            "DELETE FROM necrobot.Aliases WHERE guild_id = $1 and alias = $2", 
            ctx.guild.id, alias
        )
        
        await ctx.send(f":white_check_mark: | Alias `{alias}` removed")

    @tag.command(name="edit")
    @commands.guild_only()
    async def tag_edit(self, ctx, tag : Tag, *, content):
        """Replaces the content of [tag] with the [text] given. Basically works as a delete + create function 
        but without the risk of losing the tag name ownership.
        
        {usage}
        
        __Example__
        `{pre}tag edit necro cool server` - replaces the content of the 'necro' tag with 'cool server'"""
        await self.is_tag_owner(ctx, tag)

        await self.bot.db.query_executer(
            "UPDATE necrobot.Tags SET content = $1 WHERE guild_id = $2 AND name = $3", 
            content, ctx.guild.id, tag["name"]
        )
        
        await ctx.send(f":white_check_mark: | Tag `{tag['name']}` modified")

    @tag.command(name="raw")
    @commands.guild_only()
    async def tag_raw(self, ctx, *, tag : Tag):
        """Returns the unformatted content of the tag [tag] so other users can see how it works.
        
        {usage}
        
        __Example__
        `{pre}raw necro` - prints the raw data of the 'necro' tag"""
        await ctx.send(f":notebook: | Source code for {tag['name']}: ```{tag['content']}```")

    @tag.command(name="list")
    @commands.guild_only()
    async def tag_list(self, ctx):
        """Returns the list of tags present on the guild.
        
        {usage}"""
        tag_list = await self.bot.db.query_executer(
            "SELECT alias from necrobot.Aliases WHERE guild_id = $1",
            ctx.guild.id    
        )
        
        def _embed_generator(index, entries):
            tag_str = "- " + "\n- ".join(entries)
            embed = discord.Embed(
                title=f"Tags on this server ({index[0]}/{index[1]})", 
                description=tag_str, 
                colour=discord.Colour(0x277b0)
            )
            
            embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))

            return embed

        await react_menu(ctx, [t["alias"] for t in tag_list], 10, _embed_generator)

    @tag.command(name="info")
    @commands.guild_only()
    async def tag_info(self, ctx, *, tag : Tag):
        """Returns information on the tag given.
        
        {usage}
        
        __Example__
        `{pre}tag info necro` - prints info for the tag 'necro'"""
        embed = discord.Embed(
            title=tag["name"],
            colour=discord.Colour(0x277b0), 
            description=f'Created on {tag["created_at"]}'
        )
        
        embed.add_field(name="Owner", value=ctx.guild.get_member(tag["owner_id"]).mention)
        embed.add_field(name="Uses", value=tag["uses"])
        embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))

        await ctx.send(embed=embed)

    @tag.command(name="alias")
    @commands.guild_only()
    async def tag_alias(self, ctx, tag : Tag, *, new_name : str):
        """Allows to create an alias for a tag, allowing to call the content of the
        tag by another name without changing the name or editing the content. Alias are
        merely a link, therefore any content updates to the original tag will be reflected 
        in its aliases. You cannot alias an an alias and nor can you edit an alias. Trying
        to alias or edit an alias will simply edit or alias the original.

        {usage}

        __Example__
        `{pre}tag alias necro super_necro` - You can now call the tag necro using the name "super_necro"
        """
        if new_name in self.restricted:
            raise BotError("Alias name is a reserved keyword")
          
        try:  
            await self.bot.db.query_executer(
                "INSERT INTO necrobot.Aliases VALUES ($1, $2, $3)", 
                new_name, tag['name'], ctx.guild.id
            )
            
            await ctx.send(":white_check_mark: | Alias successfully created")
        except DatabaseError:
            raise BotError("Alias already exists")

    #######################################################################
    ## Events
    #######################################################################

    @commands.Cog.listener()
    async def on_message(self, message):
        content = message.content.split(maxsplit=1)
        if re.match(f"<@!?{self.bot.user.id}>", message.content) is not None and len(content) > 1:
            content = content[1]
            ctx = await self.bot.get_context(message)
            command = self.bot.get_command("tag")
            
            try:
                tag = await Tag().convert(ctx, content)
            except commands.BadArgument:
                return

            await ctx.invoke(command, tag=tag)

def setup(bot):
    bot.add_cog(Tags(bot))
