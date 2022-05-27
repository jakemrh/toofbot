"""Basic commands for Toof"""

import os
import datetime as dt
from random import choice
from typing import Union

from PIL import Image
import pillow_heif
import discord
from discord.ext import commands, tasks
from discord import FFmpegPCMAudio
import deepl

import toof

class ToofCommands(commands.Cog):
    """Basic general commands for Toof"""

    def __init__(self, bot: toof.ToofBot):
        self.bot = bot
        self.toofpics = []

        for filename in os.listdir('./attachments/toofpics'):
            self.toofpics.append(f'./attachments/toofpics/{filename}')

    # Equivalent of "ping" command that other bots have
    # Gives the latency, and if the user is in a voice channel,
    # Connects to that channel and plays a funny noise
    @commands.command(aliases=["ping"])
    async def speak(self, ctx: commands.Context):
        """Equivalent of \"ping\" command"""
        await ctx.send(f"woof. ({round(self.bot.latency * 1000)}ms)")
        # Plays the vine thud sound effect if the user is in a voice channel
        if ctx.author.voice:
            if ctx.voice_client:
                return
            voice = await ctx.author.voice.channel.connect()
            source = FFmpegPCMAudio('./attachments/audio/thud.wav')
            voice.play(source)
            
    # Makes Toof curl up in the users lap.
    # Shuts down the bot if called by Jacob
    @commands.command(aliases=["shutdown"])
    async def sleep(self, ctx: commands.Context):
        """Make Toof take a nap"""
        # Makes sure only I can disable the bot
        if ctx.author.id == 243845903146811393:
            await ctx.send('*fucking dies*')
            await self.bot.toof_shut_down()
        # Kindly lets the user know they can't do that
        else:
            await ctx.send(f"*snuggles in {ctx.author.display_name}'s lap*")

    # Sends a random picture of Toof
    @commands.group(aliases=["picture"])
    async def pic(self, ctx: commands.Context):
        """Sends a random toofpic"""
        if ctx.invoked_subcommand:
            return
        
        filename = choice(self.toofpics)
        with open(filename, 'rb') as fp:
            pic = discord.File(fp, filename=filename)
            await ctx.send(file=pic)

    # Adds a toofpic to the folder
    @pic.command(hidden=True)
    async def add(self, ctx: commands.Context):
        """Adds a picture to toof pics folder"""
        if ctx.author.id != 243845903146811393:
            await ctx.message.add_reaction("❌")
            return

        if not ctx.message.attachments:
            await ctx.message.add_reaction("❓")
            return
        
        fileaddress = f"attachments/toofpics/{len(self.toofpics) + 1}.jpg"

        file:discord.Attachment = ctx.message.attachments[0]

        # No conversion necessary, saves directly
        if file.filename.endswith(".jpg"):
            with open(fileaddress, 'wb') as fp:
                await file.save(fp)

            self.toofpics.append(fileaddress)
            await ctx.message.add_reaction("👍")
        # Converts image from png to jpg, then saves it
        elif file.filename.endswith(".png"):
            with open('temp.png', 'wb') as fp:
                await file.save(fp)

            png = Image.open('temp.png')
            jpg = png.convert("RGB")
            jpg.save(fileaddress)
            os.remove('temp.png')

            self.toofpics.append(fileaddress)
            await ctx.message.add_reaction("👍")
        # Converts HEIC to jpg, then saves it
        elif file.filename.endswith(".heic"):
            with open('temp.heic', 'wb') as fp:
                await file.save(fp)

            with open('temp.heic', 'rb') as fp:    
                heif_file = pillow_heif.open_heif(fp)
            image = Image.frombytes(
                heif_file.mode,
                heif_file.size,
                heif_file.data,
                "raw",
            )
            image.save(fileaddress)
            os.remove('temp.heic')

            self.toofpics.append(fileaddress)
            await ctx.message.add_reaction("👍")
        # Can't convert other formats
        else:
            await ctx.message.add_reaction("👎")

    # Gives the user's age
    @commands.command()
    async def age(self, ctx: commands.Context, member:discord.User=None):
        """Gives the members age (years, months, days)"""
        if not member:
            member = ctx.author
        age:dt.timedelta = dt.datetime.now() - member.created_at

        if age.days < 1:
            years = 0
            months = 0
            days = 0
        else:
            years = age.days // 365
            months = age.days % 365 // 30
            days = age.days - (years * 365) - (months * 30)

        message = ""
        if years == 0:
            message += "..."
        else:
            for i in range(years):
                message += "woof "
        message += "\n"
        if months == 0:
            message += "..."
        else:
            for i in range(months):
                message += "bark "
        message += "\n"
        if days == 0:
            message += "..."
        else:
            for i in range(days):
                message += "ruff "
        
        await ctx.send(message)

    # Adds a message to the quoteboard
    @commands.command()
    async def quote(self, ctx: commands.Context, member:Union[discord.Member, str]=None, *, quote:str=None):
        """
        Adds something to the quoteboard\n
        You can either use this in a reply to an original message,
        Or you can use it by doing: 
            'toof, quote \"the person's name\" {the quote body}'
        """

        quote_channel = discord.utils.find(
            lambda c : c.id == self.bot.serverconf['channels']['quotes'],
            ctx.guild.channels
        )

        # If the command is a reply, adds the original message to the quoteboard
        if ctx.message.reference:
            if ctx.message.reference.message_id in self.bot.quotes:
                return
            
            message = ctx.message.reference.cached_message

            if message:
                if message.content:
                    embed = discord.Embed(
                        description=message.content,
                        color=discord.Color.blurple()
                    )
                else:
                    embed = discord.Embed(colour=discord.Colour.blurple())
                if message.attachments:
                    attachment_url = message.attachments[0].url
                    embed.set_image(url=attachment_url)

                embed.set_author(
                    name=f"{message.author.name}#{message.author.discriminator} (click to jump):",
                    url=message.jump_url,
                    icon_url=message.author.avatar_url
                )
        
                date = message.created_at.strftime("%m/%d/%Y")
                embed.set_footer(text=date)

                self.bot.quotes.append(message.id)

            else:
                await ctx.message.add_reaction("👎")
                return
        # If it is not a reply, uses the normal functionality
        else:
            if member is None or quote is None:
                await ctx.message.add_reaction("👎")
                return
            
            embed = discord.Embed(
                description=quote,
                color=discord.Color.blurple()
            )

            if isinstance(member, discord.Member):
                embed.set_author(
                    name=f"{member.name}#{member.discriminator} (allegedly) (click to jump):",
                    url=ctx.message.jump_url,
                    icon_url=member.avatar_url
                )
            elif isinstance(member, str):
                embed.set_author(
                    name=f"{member} (allegedly) (click to jump):",
                    url=ctx.message.jump_url
                )
            else:
                await ctx.message.add_reaction("❓")
                return
            
            if ctx.message.attachments:
                attachment_url = ctx.message.attachments[0].url
                embed.set_image(url=attachment_url)
            
            date = ctx.message.created_at.strftime("%m/%d/%Y")
            embed.set_footer(text=date)

            self.bot.quotes.append(ctx.message.id)

        await quote_channel.send(
            content=f"{ctx.author.mention} submitted a quote:",
            embed=embed
        )

class ToofEvents(commands.Cog):
    """Cog that contains basic event handling"""

    def __init__(self, bot: toof.ToofBot):
        self.bot = bot
        self.translator = deepl.Translator(os.getenv('DEEPLKEY'))
        self.cachedmessages:list[discord.Message] = None

    # Starts loops
    @commands.Cog.listener()
    async def on_ready(self):
        self.change_status.start()

    @commands.Cog.listener()
    async def on_member_join(self, member:discord.Member):
        """Sends a message to the welcome channel when a new member joins"""
        welcome_channel = discord.utils.find(
            lambda c : c.id == self.bot.serverconf['channels']['welcome'],
            member.guild.channels
        )
        rules_channel = discord.utils.find(
            lambda c : c.id == self.bot.serverconf['channels']['rules'],
            member.guild.channels
        )

        await welcome_channel.send(
            f"henlo {member.mention} welcime to server. read {rules_channel.mention} pls. say 'woof' when ur done 🐶"
        )

    # Replies to messages that have certain phrases in them    
    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        """Listens for specific messages"""

        # Ignores messages sent by the bot and messages sent in the welcome channel
        if msg.author == self.bot.user or msg.channel.id == self.bot.serverconf['channels']['welcome']:
            return
        
        # Responds to messages with certain phrases
        content = msg.content
        if "car ride" in content.lower():
            print("CAR RIDE?")
            await msg.channel.send("WOOF.")
        elif "good boy" in content.lower():
            print("I'M A GOOD BOY!!")
            await msg.channel.send("WOOF.")
        elif "Connor" in content:
            await msg.channel.send("connor*")

        # Handles ping replies
        if msg.mentions and msg.reference:
            emoji = discord.utils.find(lambda e : e.name == 'toofping', msg.guild.emojis)
            if emoji:
                await msg.add_reaction(emoji)
            else:
                await msg.add_reaction("🇵")
                await msg.add_reaction("🇮")
                await msg.add_reaction("🇳")
                await msg.add_reaction("🇬")            
        
    # Kicks people for listening to Say So by Doja Cat
    @commands.Cog.listener()
    async def on_member_update(self, before:discord.Member, after:discord.Member):
        for activity in after.activities:
            if isinstance(activity, discord.Spotify):
                if activity.title == "Say So" and activity.artist == "Doja Cat":
                    await after.send("You were kicked for listening to Say So by Doja Cat")
                    await after.kick(reason="Listening to Say So by Doja Cat")

    # Translates messages using DeepL API
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction:discord.Reaction, user:discord.Member):
        # Ignore reactions added by the bot
        if user == self.bot.user:
            return

        # Translates to English using DeepL API
        if reaction.emoji == '🇬🇧' or reaction.emoji == '🇺🇸' and reaction.count == 1:
            result = self.translator.translate_text(str(reaction.message.content), target_lang="EN-US")
            await reaction.message.reply(f'{result.detected_source_lang} -> EN: "{result.text}"')
            return
        # Translates to Japanese using DeepL API
        if reaction.emoji == '🇯🇵' and reaction.count == 1:
            result = self.translator.translate_text(str(reaction.message.content), target_lang="JA")
            await reaction.message.reply(f'{result.detected_source_lang} -> JA: "{result.text}"')
            return
                    
    # Changes the status on a loop
    @tasks.loop(seconds=180)
    async def change_status(self):
        """Changes the status on a 180s loop"""
        await self.bot.change_presence(activity=choice(self.bot.activities))


def setup(bot:toof.ToofBot):
    bot.add_cog(ToofCommands(bot))
    bot.add_cog(ToofEvents(bot))