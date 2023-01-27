import discord
from discord.ext import commands
import datetime

class ModerationLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_id = 1068497895613018172

    @property
    def log(self):
        return self.bot.get_channel(self.log_id)
    

    @commands.Cog.listener('on_mod_action')
    async def listener(self, action, mod, target, reason):
        if (isinstance(target, discord.Member) or isinstance(target, discord.User)):
            tar_str1 = target.display_name
            tar_str2 = f"{target.mention}\nID: `{target.id}`"
        else:
            tar_str1 = target
            tar_str2 = target
        embed = discord.Embed(title=action, description=f"{tar_str1} was {action}ed by {mod.display_name}\n```ahk\nReason: {reason}```", color=self.bot.color)
        embed.add_field(name="Moderator", value=f"{mod.mention}\nID: `{mod.id}`")
        embed.add_field(name="Target", value=tar_str2)
        embed.timestamp = datetime.datetime.utcnow()
        await self.log.send(embed=embed)
        await target.send(f"You were {action}ed by {mod.display_name} in {mod.guild.name} for {reason}.")
        
        
def setup(bot):
    bot.add_cog(ModerationLogs(bot))