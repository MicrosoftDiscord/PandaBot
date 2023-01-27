import os
import discord
from discord.ext import commands
import asqlite
import asyncio
from keep_repl_alive import keep_alive
import jishaku

INITIAL_COGS = [
    "moderation",
    "utilities",
    "modlogs"
]

class HelpCommand(commands.MinimalHelpCommand):
    """The customized help command."""


    async def send_pages(self):
        destination = self.get_destination()
        for page in self.paginator.pages:
            embed = discord.Embed(title="Help", description=page, color=discord.Color.from_rgb(4, 252, 196))
            embed.set_footer(text="Animal HQ")
            await destination.send(embed=embed)
    

class Bot(commands.Bot):
    """The subclass of commands.Bot to override is_owner"""

    async def is_owner(self, user):
        return user.id in [851803979914805328]


intents = discord.Intents.default()
intents.members = True

bot = Bot(
    command_prefix=">", 
    description = "Made by Cyan.",
    status=discord.Status.online, 
    help_command=HelpCommand(),
    intents=intents,
    activity=discord.Activity(name="over the network!", type=discord.ActivityType.watching)
    )

loop = asyncio.get_event_loop()

bot.conn = loop.run_until_complete(asqlite.connect('database.sqlite'))

bot.color = discord.Color.from_rgb(4, 252, 196)



for cog in INITIAL_COGS:
    bot.load_extension(cog)
    print(f"Loaded {cog} extension.")


@bot.event
async def on_ready():
    bot.load_extension("jishaku")
    for ext in os.listdir("./cogs"):
        if ext.endswith(".py"):
            bot.load_extension(f"cogs.{ext[:-3]}")
    print("Bot is Ready!")


keep_alive()



bot.run(os.environ['TOKEN'])
