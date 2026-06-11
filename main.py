import os
import discord
import aiosqlite
import re
from discord.ext import commands
from datetime import datetime, timedelta

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
MOD_LOG = int(os.getenv("MOD_LOG_CHANNEL_ID"))
WELCOME_ID = int(os.getenv("WELCOME_CHANNEL_ID"))
LEAVE_ID = int(os.getenv("LEAVE_CHANNEL_ID"))
AUTO_ROLE_ID = os.getenv("AUTO_ROLE_ID")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- Database ----------
async def init_db():
    async with aiosqlite.connect("guard.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS warns (
            user_id INTEGER, mod_id INTEGER, reason TEXT, time TEXT)""")
        await db.commit()

async def log(action, mod, target, reason="-"):
    ch = bot.get_channel(MOD_LOG)
    if not ch: return
    e = discord.Embed(title=action, color=0x5865F2, timestamp=datetime.utcnow())
    e.add_field(name="Moderator", value=mod.mention)
    e.add_field(name="Target", value=f"{target} ({target.id})")
    e.add_field(name="Reason", value=reason, inline=False)
    await ch.send(embed=e)

# ---------- Events ----------
@bot.event
async def on_ready():
    await init_db()
    guild = discord.Object(id=GUILD_ID)
    bot.tree.clear_commands(guild=guild)   # <--- PASTE THIS LINE HERE
    synced = await bot.tree.sync(guild=guild)
    print(f"Windowra Guard PRO online - {len(synced)} commands synced")

@bot.event
async def on_member_join(member):
    if AUTO_ROLE_ID and AUTO_ROLE_ID.isdigit():
        role = member.guild.get_role(int(AUTO_ROLE_ID))
        if role:
            try: await member.add_roles(role, reason="Auto-role")
            except: pass
    ch = bot.get_channel(WELCOME_ID)
    if ch:
        e = discord.Embed(title=f"Welcome to Windowra, {member.name}!",
                         description="Please read #rules and enjoy your stay!",
                         color=0x57F287)
        e.set_thumbnail(url=member.display_avatar.url)
        e.set_footer(text=f"Member #{member.guild.member_count}")
        await ch.send(content=member.mention, embed=e)

@bot.event
async def on_member_remove(member):
    ch = bot.get_channel(LEAVE_ID)
    if ch:
        e = discord.Embed(description=f"**{member.name}** has left Windowra",
                         color=0xED4245, timestamp=datetime.utcnow())
        e.set_footer(text=f"We now have {member.guild.member_count} members")
        await ch.send(embed=e)

# ---------- Auto-Mod ----------
SPAM_TRACK = {}
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return
    # Spam (5 messages in 5 seconds)
    now = datetime.utcnow()
    SPAM_TRACK.setdefault(message.author.id, [])
    SPAM_TRACK[message.author.id].append(now)
    SPAM_TRACK[message.author.id] = [t for t in SPAM_TRACK[message.author.id] if (now - t).total_seconds() < 5]
    if len(SPAM_TRACK[message.author.id]) > 5:
        try:
            await message.delete()
            await message.author.timeout(timedelta(minutes=5), reason="Auto-mod: Spam")
            await message.channel.send(f"{message.author.mention} timed out for spamming", delete_after=5)
        except: pass

    # Link filter
    if re.search(r"discord\.gg/|discord\.com/invite/", message.content):
        if not message.author.guild_permissions.manage_messages:
            try: await message.delete()
            except: pass

    await bot.process_commands(message)

# ---------- Slash Commands ----------
guild = discord.Object(id=GUILD_ID)

@bot.tree.command(guild=guild, description="Ban a member permanently")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    await log("BAN", interaction.user, member, reason)
    await interaction.response.send_message(f"🔨 Banned {member}", ephemeral=True)

@bot.tree.command(guild=guild, description="Kick a member")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    await log("KICK", interaction.user, member, reason)
    await interaction.response.send_message(f"👢 Kicked {member}", ephemeral=True)

@bot.tree.command(guild=guild, description="Timeout a member")
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await log("TIMEOUT", interaction.user, member, f"{minutes}m - {reason}")
    await interaction.response.send_message(f"⏱️ {member} timed out for {minutes} minutes", ephemeral=True)

@bot.tree.command(guild=guild, description="Remove timeout from member")
async def untimeout(interaction: discord.Interaction, member: discord.Member):
    await member.timeout(None)
    await log("UNTIMEOUT", interaction.user, member)
    await interaction.response.send_message(f"✅ Removed timeout from {member}", ephemeral=True)

@bot.tree.command(guild=guild, description="Delete multiple messages")
async def purge(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 Deleted {len(deleted)} messages", ephemeral=True)

@bot.tree.command(guild=guild, description="Lock the current channel")
async def lockdown(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message("🔒 Channel locked")

@bot.tree.command(guild=guild, description="Unlock the current channel")
async def unlock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message("🔓 Channel unlocked")

@bot.tree.command(guild=guild, description="Set channel slowmode")
async def slowmode(interaction: discord.Interaction, seconds: int):
    await interaction.channel.edit(slowmode_delay=seconds)
    await interaction.response.send_message(f"🐢 Slowmode set to {seconds} seconds")

@bot.tree.command(guild=guild, description="Warn a member")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    async with aiosqlite.connect("guard.db") as db:
        await db.execute("INSERT INTO warns VALUES (?,?,?,?)",
                        (member.id, interaction.user.id, reason, datetime.utcnow().isoformat()))
        await db.commit()
    await log("WARN", interaction.user, member, reason)
    await interaction.response.send_message(f"⚠️ Warned {member}", ephemeral=True)

@bot.tree.command(guild=guild, description="View member warnings")
async def warnings(interaction: discord.Interaction, member: discord.Member):
    async with aiosqlite.connect("guard.db") as db:
        cur = await db.execute("SELECT reason, time FROM warns WHERE user_id=?", (member.id,))
        rows = await cur.fetchall()
    if not rows:
        return await interaction.response.send_message(f"{member} has no warnings", ephemeral=True)
    desc = "\n".join([f"• {r[0]} (<t:{int(datetime.fromisoformat(r[1]).timestamp())}:R>)" for r in rows[:10]])
    embed = discord.Embed(title=f"Warnings for {member}", description=desc, color=0xFAA61A)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(guild=guild, description="Clear all warnings")
async def clearwarns(interaction: discord.Interaction, member: discord.Member):
    async with aiosqlite.connect("guard.db") as db:
        await db.execute("DELETE FROM warns WHERE user_id=?", (member.id,))
        await db.commit()
    await interaction.response.send_message(f"✅ Cleared warnings for {member}", ephemeral=True)

@bot.tree.command(guild=guild, description="Change member nickname")
async def nick(interaction: discord.Interaction, member: discord.Member, nickname: str):
    await member.edit(nick=nickname)
    await interaction.response.send_message(f"✏️ Changed nickname for {member}", ephemeral=True)

@bot.tree.command(guild=guild, description="Add role to member")
async def roleadd(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await interaction.response.send_message(f"➕ Added {role.name} to {member}", ephemeral=True)

@bot.tree.command(guild=guild, description="Remove role from member")
async def roleremove(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await interaction.response.send_message(f"➖ Removed {role.name} from {member}", ephemeral=True)

@bot.tree.command(guild=guild, description="Show server information")
async def serverinfo(interaction: discord.Interaction):
    g = interaction.guild
    embed = discord.Embed(title=g.name, color=0x5865F2, timestamp=datetime.utcnow())
    embed.add_field(name="Owner", value=g.owner.mention)
    embed.add_field(name="Members", value=g.member_count)
    embed.add_field(name="Created", value=f"<t:{int(g.created_at.timestamp())}:D>")
    embed.set_thumbnail(url=g.icon.url if g.icon else None)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(guild=guild, description="Show user information")
async def userinfo(interaction: discord.Interaction, member: discord.Member):
    embed = discord.Embed(title=member.display_name, color=0x5865F2)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Joined Discord", value=f"<t:{int(member.created_at.timestamp())}:D>", inline=True)
    embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:D>", inline=True)
    embed.add_field(name="Roles", value=len(member.roles)-1, inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(guild=guild, description="Get user avatar")
async def avatar(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(member.display_avatar.url)

@bot.tree.command(guild=guild, description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! {round(bot.latency * 1000)}ms")

@bot.tree.command(guild=guild, description="Make the bot say something")
async def say(interaction: discord.Interaction, message: str):
    await interaction.response.send_message("Message sent!", ephemeral=True)
    await interaction.channel.send(message)

bot.run(TOKEN)
