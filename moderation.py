import discord
from discord.ext import commands
import inspect
import typing
import os
import re
import asyncio
import datetime

time_regex = re.compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([smhd])")
time_dict = {"h":3600, "s":1, "m":60, "d":86400}

class TimeConverter(commands.Converter):
    async def convert(self, ctx, argument):
        matches = time_regex.findall(argument.lower())
        time = 0
        for v, k in matches:
            try:
                time += time_dict[k]*float(v)
            except KeyError:
                raise commands.BadArgument("{} is an invalid time-key! h/m/s/d are valid!".format(k))
            except ValueError:
                raise commands.BadArgument("{} is not a number!".format(v))
        return datetime.timedelta(seconds=time)

class Moderation(commands.Cog):
    """All commands related to moderating the server."""
    def __init__(self, bot):
        self.bot = bot


    @commands.command(name="kick", brief="Kicks a member from the server")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, members:commands.Greedy[discord.Member], *, reason="No reason provided"):
        """Kicks all members specified from the server. Optionally, a reason can be specified for the action."""
        await ctx.message.delete()
        if not members:
            raise commands.MissingRequiredArgument(inspect.Parameter(name="members", kind=inspect.Parameter.POSITIONAL_ONLY))
        kicked = []
        failed = 0
        if len(members) == 1:
            member = members[0]
            id = member.id if isinstance(member, discord.User) else member
            try:
                await ctx.guild.ban(discord.Object(id=id))
            except Exception as e:
                await ctx.send(e)
                return
            self.bot.dispatch('mod_action', ':boot: Kick', ctx.author, member, reason)
            await ctx.send(f":boot: Successfully **kicked**  `{member.mention if isinstance(member, discord.User) else member}`!")
            return
        for member in members:
            try:
                await member.kick(reason=f"Action by {ctx.author}. ({reason})")
                self.bot.dispatch('mod_action', ':boot: Kick', ctx.author, member, reason)
                kicked.append(member)
            except Exception:
                failed += 1
        kicked_str = ", ".join(m.mention for m in kicked)
        if len(kicked_str) > 4000:
            kicked_str = f"{len(kicked)} members"
        dsc = f"Kicked {kicked_str}."
        if bool(failed):
            dsc += f"\nFailed to kick {failed} other member(s)"
        embed = discord.Embed(title="Kick Successful", description=dsc, color=self.bot.color)
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.command(name="ban", brief="Bans a user from the server")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, members:commands.Greedy[typing.Union[discord.User, int]], *, reason="No reason provided"):
        """Bans all members specified from the server. Optionally, a reason can be specified for the action."""
        await ctx.message.delete()
        if not members:
            raise commands.MissingRequiredArgument(inspect.Parameter(name="members", kind=inspect.Parameter.POSITIONAL_ONLY))
        banned = []
        failed = 0
        if len(members) == 1:
            member = members[0]
            id = member.id if isinstance(member, discord.User) else member
            try:
                await ctx.guild.ban(discord.Object(id=id))
            except Exception as e:
                await ctx.send(e)
                return
            self.bot.dispatch('mod_action', ':hammer: Ban', ctx.author, member, reason)
            await ctx.send(f":hammer: Successfully **banned** `{member}`!")
            return
        for member in members:
            try:
                id = member.id if isinstance(member, discord.User) else member
                await ctx.guild.ban(discord.Object(id=id))
                self.bot.dispatch('mod_action', ':hammer: Ban', ctx.author, member, reason)
                banned.append(member)
            except Exception:
                failed += 1
        kicked_str = ", ".join((m.mention if isinstance(m, discord.User) else m) for m in banned)
        if len(kicked_str) > 4000:
            kicked_str = f"{len(banned)} members"
        dsc = f"Banned {kicked_str}."
        if bool(failed):
            dsc += f"\nFailed to ban {failed} other member(s)"
        embed = discord.Embed(title="Ban Successful", description=dsc, color=self.bot.color)
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @commands.command(name="warn", brief="Warns a member")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member:discord.Member, *, reason="No reason provided"):
        """Warns a member as punishment."""
        await ctx.message.delete()
        await self.bot.conn.execute("INSERT INTO warns (user_id, mod_id, reason, timestamp) VALUES (?,?,?,?)", (member.id, ctx.author.id, reason, ctx.message.created_at.timestamp()))
        self.bot.dispatch('mod_action', ':warning: Warn', ctx.author, member, reason)
        warns = await self.bot.conn.fetchall("SELECT * FROM warns WHERE user_id=? ORDER BY timestamp DESC", (member.id,))
        current = warns[0]
        warn_id = current[0]
        await ctx.send(f":warning: Successfully **warned** `{member}`!")

    @commands.command(name="slowmode", aliases=['sm'])
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds:int=None):
        await ctx.message.delete()
        if not seconds:
            seconds = 0
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.send(f"Changed slowmode to {seconds} seconds.")

    @commands.command(name="delwarn", brief="Deletes a warning.")
    @commands.has_permissions(manage_roles=True)
    async def unwarn(self, ctx, id:int):
        """Deletes a member's warnings with the warn ID."""
        await ctx.message.delete()
        res = await self.bot.conn.fetchone("SELECT * FROM warns WHERE warn_id=?", (id,))
        if not res:
            await ctx.send("A warn with ID {id} does not exist.")
            return
        await self.bot.conn.execute("DELETE FROM warns WHERE warn_id=?", (id,))
        user = ctx.guild.get_member(res[1])
        remaining = await self.bot.conn.fetchall("SELECT * FROM warns WHERE user_id=?", (res[1],))
        embed = discord.Embed(title="Warning Deleted", description=f"Warning of <@{res[1]}> given by <@{res[2]}>, <t:{int(res[4])}:R> has been deleted.", color=self.bot.color)
        embed.set_footer(text=f"{user} has {len(remaining)} warns now.")
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        self.bot.dispatch('mod_action', ':warning: Delete Warn', ctx.author, user, "N/A")
        await ctx.reply(embed=embed)

    @commands.command(name="clearwarn", brief="Clears all warns for a user", aliases=["clearwarns"])
    @commands.has_permissions(administrator=True)
    async def clearwarn(self, ctx, member:discord.Member):
        """Clears all warnings a member has."""
        await ctx.message.delete()
        res = await self.bot.conn.fetchall("SELECT * FROM warns WHERE user_id=?", (member.id,))
        if not res:
            await ctx.send(f"{member} has no warnings.")
        await self.bot.conn.execute("DELETE FROM warns WHERE user_id=?", (member.id,))
        self.bot.dispatch('mod_action', ':warning: Clear Warns', ctx.author, member, "N/A")
        embed = discord.Embed(title="Warnings Deleted", description=f"**{len(res)}** warnings of {member.mention} have been deleted.", color=self.bot.color)
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @commands.command(name="warnings", brief="Shows all warnings of a member", aliases=['warns'])
    async def warnings(self, ctx, member:discord.Member):
        """Shows all warnings a member has"""
        res = await self.bot.conn.fetchall("SELECT * FROM warns WHERE user_id=?", (member.id,))
        embed = discord.Embed(title="All Warnings", color=self.bot.color)
        if res:
            embed.description = f"{member.mention} has {len(res)} warnings."
            for row in res:
                embed.add_field(name=f"Warn ID {row[0]}", value=f"**Moderator:** `Hidden.`\n**Reason:** `{row[3]}`\n**Time:** <t:{int(row[4])}:R>")
        else:
            embed.description = f"{member.mention} has no warnings."
        await ctx.send(embed=embed)

    @commands.command(name="lockdown", brief="Locks all channels")
    @commands.has_permissions(manage_roles=True)
    async def lock_all(self, ctx, *, reason="No reason provided"):
        """Locks all channels that are in the list of channels to be locked down."""
        res = await self.bot.conn.fetchall("SELECT * FROM to_lock")
        if not res:
            await ctx.send("No channel added to lockdown.")
            return
        embed = discord.Embed(title="This channel is locked.", description=reason, color=self.bot.color)
        s_str = ""
        for ch_id in res:
            ch_id = ch_id[0]
            ch = ctx.guild.get_channel(ch_id)
            if not ch:
                await ctx.send(f"Channel <#{ch_id}> not found.")
                continue
            try:
                await ch.set_permissions(ctx.guild.default_role, reason=reason, send_messages=False)
            except Exception as e:
                await ctx.send(f"Error while locking {ch.mention}: {e}")
                continue
            s_str += f"Locked {ch.mention}\n"
            await self.bot.conn.execute("INSERT INTO lockdown (channel_id) VALUES (?)", (ch_id,))
            await ch.send(embed=embed)
        await ctx.send(s_str)

    @commands.command(name="unlockdown", brief="Unlocks all channels")
    @commands.has_permissions(manage_roles=True)
    async def unlock_all(self, ctx):
        """Unlocks all channels that are currently locked down."""
        res = await self.bot.conn.fetchall("SELECT * FROM lockdown")
        s_str = ""
        for row in res:
            ch = ctx.guild.get_channel(row[0])
            if not ch:
                await ctx.send(f"Channel <#{row[0]}> not found.")
                continue
            try:
                await ch.set_permissions(ctx.guild.default_role, send_messages=True)
            except Exception as e:
                await ctx.send(f"Error while unlocking {ch.mention}: {e}")
                continue
            await self.bot.conn.execute("DELETE FROM lockdown WHERE channel_id=?", (ch.id,))
            await ch.send("This channel is now unlocked.")
            s_str += f"Unlocked {ch.mention}\n"
        await ctx.send(s_str)
    
    @commands.group(name="lockdownconfig", brief="Configuration of channels that have to be locked down", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def lockdownconfig(self, ctx):
        """
        Configurations of channels that are to be locked when the command `lockdown` is used.
        """
        res = await self.bot.conn.fetchall("SELECT * FROM to_lock")
        ch_str = ", ".join(ctx.guild.get_channel(row[0]).mention for row in res)
        embed = discord.Embed(title="Channels to lock down", description=ch_str, color=self.bot.color)
        await ctx.send(embed=embed)
    
    @lockdownconfig.command(name="add", brief="Adds a channel to be locked down.")
    @commands.has_permissions(administrator=True)
    async def add_channel(self, ctx, channel:discord.TextChannel):
        """Adds a channel to the list of channels to be locked down."""
        res = await self.bot.conn.fetchall("SELECT * FROM to_lock WHERE channel_id=?", (channel.id,))
        if res:
            await ctx.send(f"{channel.mention} is already in the lockdown list.")
            return
        await self.bot.conn.execute("INSERT INTO to_lock (channel_id) VALUES (?)", (channel.id,))
        await ctx.send(f"Added {channel.mention} to be locked down.")

    @lockdownconfig.command(name="remove", brief="Removes a channel from being locked down")
    @commands.has_permissions(administrator=True)
    async def remove_channel(self, ctx, channel:discord.TextChannel):
        """Removes a channel from the list of channels to be locked down."""
        await self.bot.conn.execute("DELETE FROM to_lock WHERE channel_id=?", (channel.id,))
        await ctx.send(f"Removed {channel.mention} from list of lockdown channels.")
    

    async def sleep_and_unban(self, seconds, guild, id):
        await asyncio.sleep(seconds)
        await guild.unban(discord.Object(id=id), reason=f"Tempban over")

    @commands.command(name="tempban", brief="Temporarily bans a user")
    @commands.has_permissions(ban_members=True)
    async def tempban(self, ctx, user:discord.User, delta:TimeConverter, *, reason="No reason provided"):
        """
        Bans a user, waits until the given time before unbanning the user.
        """
        await ctx.message.delete()
        await ctx.guild.ban(discord.Object(id=user.id), reason=f"Tempban by {ctx.author}")
        self.bot.dispatch('mod_action', ':hammer: Ban', ctx.author, user, reason)
        self.bot.loop.create_task(self.sleep_and_unban(delta.total_seconds(), ctx.guild, user.id))
        await ctx.send(f":hammer: Successfully **banned** `{member}` for `{delta}`!")

    @commands.command(name="muterole", brief="Sets the mute role")
    @commands.has_permissions(administrator=True)
    async def set_mute_role(self, ctx, role:discord.Role):
        """
        Sets a new role as the mute role.
        """
        os.environ["MUTE_ROLE_ID"] = str(role.id)
        await ctx.send("Mute role updated.")
    
    @commands.command(name="mute", brief="Mutes a member")
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member:discord.Member, *, reason="No reason provided"):
        """Adds the muted role to a member"""
        role = ctx.guild.get_role(int(os.environ.get("MUTE_ROLE_ID")))
        await member.add_roles(role, reason=reason)
        self.bot.dispatch('mod_action', ':mute: Mute', ctx.author, member, reason)
        await ctx.message.delete()
        await ctx.send(f":mute: Successfully **muted**  `{member}`!")
    
    @commands.command(name="unmute", brief="Unmutes a member")
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member:discord.Member):
        """Removes the muted role from a member"""
        role = ctx.guild.get_role(int(os.environ.get("MUTE_ROLE_ID")))
        await member.remove_roles(role)
        self.bot.dispatch('mod_action', ':loud_sound: Unmute', ctx.author, member, "N/A")
        await ctx.send(f":loud_sound: Successfully **unmuted** `{member}`!")
        await ctx.message.delete()
    

    async def sleep_and_unmute(self, member, seconds):
        await asyncio.sleep(seconds)
        role = member.guild.get_role(int(os.environ.get("MUTE_ROLE_ID")))
        await member.remove_roles(role)

    @commands.command(name="tempmute", brief="Temporarily mutes a member")
    @commands.has_permissions(manage_roles=True)
    async def tempmute(self, ctx, member:discord.Member, delta:TimeConverter, *, reason="No reason provided"):
        """Mutes a member, waits until the given time before unmuting."""
        role = ctx.guild.get_role(int(os.environ.get("MUTE_ROLE_ID")))
        await member.add_roles(role)
        self.bot.dispatch('mod_action', ':mute: Mute', ctx.author, member, reason)
        self.bot.loop.create_task(self.sleep_and_unmute(member, delta.total_seconds()))
        await ctx.message.delete()
        await ctx.send(f":mute: Successfully **muted** `{member}` for `{delta}`!")



        
        



            
        
    
            


    


def setup(bot):
    bot.add_cog(Moderation(bot))
