import discord
from discord.ext import commands
import time



class Timer:
    def __init__(self):
        self._start = None
        self._end = None

    def start(self):
        self._start = time.perf_counter()

    def stop(self):
        self._end = time.perf_counter()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def __int__(self):
        return round(self.time)

    def __float__(self):
        return self.time

    def __str__(self):
        return str(self.time)

    def __repr__(self):
        return f"<Timer time={self.time}>"

    @property
    def time(self):
        if self._end is None:
            raise ValueError("Timer has not been ended.")
        return self._end - self._start

class Utilities(commands.Cog):
    """Helpful commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping", brief="Shows the latency of the bot.")
    async def ping_command(self, ctx):
        """Calculates the time the bot takes to reply"""
        with Timer() as message_latency:
            msg = await ctx.send("Ping?")
        embed = discord.Embed(title = "Pong!", description=f"Average websocket latency: `{round(self.bot.latency * 1000, 3)} ms`", color=self.bot.color)
        embed.add_field(name="API", value=f"`{message_latency.time * 1000:,.2f}` ms")
        await msg.edit(content=None, embed = embed)
    
    @commands.Cog.listener('on_command_error')
    async def error_handler(self, ctx, error):
        await ctx.send(f"Error in {ctx.command.qualified_name}: {error.__class__.__name__}: {error}")


    @commands.command(name="userinfo", brief="Gives a short description about the user")
    async def userinfo(self, ctx, member:discord.User=None):
        member = member or ctx.author
        embed = discord.Embed(title=f"User Information", description=member.mention, color=self.bot.color)
        embed.set_author(name=member, icon_url=member.avatar_url, url=f"https://discord.com/users/{member.id}")
        embed.add_field(name="Account Details", value=f"Created <t:{int(member.created_at.timestamp())}:f> <t:{int(member.created_at.timestamp())}:R>\nJoined  <t:{int(member.joined_at.timestamp())}:f> <t:{int(member.joined_at.timestamp())}:R>")
        role_str = ", ".join(r.mention for r in member.roles if r.id != ctx.guild.id)
        role_str = role_str or "No roles"
        if len(role_str) > 1000:
            role_str = f"Too many roles ({len(member.roles)})"
        embed.add_field(name="Booster", value=f"Started boosting <t:{int(member.premium_since.timestamp())}:R>" if bool(member.premium_since) else "Not Boosting")
        await ctx.reply(embed=embed)
        

















def setup(bot):
    bot.add_cog(Utilities(bot))