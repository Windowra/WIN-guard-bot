import os, discord, aiosqlite
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
GUILD = discord.Object(id=GUILD_ID)

# --- DB for warns ---
async def init_db():
    async with aiosqlite.connect("guard.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS warns (user_id INTEGER, mod_id INTEGER, reason TEXT, time TEXT)")
        await db.commit()

@bot.event
async def on_ready():
    await init_db()
    bot.tree.clear_commands(guild=GUILD)
    await bot.tree.sync(guild=GUILD)
    print(f"Windowra Guard Pro online | 19 commands loaded")
    status.start()

@tasks.loop(minutes=10)
async def status():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Windowra"))

def embed(title, desc, color=0x5865F2):
    e = discord.Embed(title=title, description=desc, color=color, timestamp=datetime.utcnow())
    e.set_footer(text="Windowra • Official Community")
    return e

# 1 BAN
@bot.tree.command(name="ban", description="Ban a member", guild=GUILD)
@app_commands.checks.has_permissions(ban_members=True)
async def ban(i: discord.Interaction, member: discord.Member, reason: str = "No reason", delete_days: int = 0):
    await member.ban(reason=reason, delete_message_days=delete_days)
    await i.response.send_message(embed=embed("🔨 Ban", f"{member.mention} banned\nReason: {reason}"))

# 2 KICK
@bot.tree.command(name="kick", description="Kick a member", guild=GUILD)
@app_commands.checks.has_permissions(kick_members=True)
async def kick(i: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.kick(reason=reason)
    await i.response.send_message(embed=embed("👢 Kick", f"{member.mention} kicked"), ephemeral=True)

# 3 TIMEOUT
@bot.tree.command(name="timeout", description="Timeout user", guild=GUILD)
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(i: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason"):
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await i.response.send_message(embed=embed("⏱️ Timeout", f"{member.mention} for {minutes}m"))

# 4 UNTIMEOUT
@bot.tree.command(name="untimeout", description="Remove timeout", guild=GUILD)
@app_commands.checks.has_permissions(moderate_members=True)
async def untimeout(i: discord.Interaction, member: discord.Member):
    await member.timeout(None)
    await i.response.send_message(embed=embed("✅ Untimeout", f"{member.mention} released"))

# 5 WARN
@bot.tree.command(name="warn", description="Warn a user", guild=GUILD)
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(i: discord.Interaction, member: discord.Member, reason: str):
    async with aiosqlite.connect("guard.db") as db:
        await db.execute("INSERT INTO warns VALUES (?,?,?,?)", (member.id, i.user.id, reason, datetime.utcnow().isoformat()))
        await db.commit()
    await i.response.send_message(embed=embed("⚠️ Warn", f"{member.mention} warned\n{reason}"))

# 6 WARNINGS
@bot.tree.command(name="warnings", description="Check warns", guild=GUILD)
async def warnings(i: discord.Interaction, member: discord.Member):
    async with aiosqlite.connect("guard.db") as db:
        cur = await db.execute("SELECT reason,time FROM warns WHERE user_id=?", (member.id,))
        rows = await cur.fetchall()
    desc = "\n".join([f"• {r[0]} ({r[1][:10]})" for r in rows]) or "No warns"
    await i.response.send_message(embed=embed(f"Warnings for {member}", desc), ephemeral=True)

# 7 CLEARWARNS
@bot.tree.command(name="clearwarns", description="Clear warns", guild=GUILD)
@app_commands.checks.has_permissions(administrator=True)
async def clearwarns(i: discord.Interaction, member: discord.Member):
    async with aiosqlite.connect("guard.db") as db:
        await db.execute("DELETE FROM warns WHERE user_id=?", (member.id,)); await db.commit()
    await i.response.send_message(embed=embed("Cleared", f"Warns cleared for {member.mention}"))

# 8 PURGE
@bot.tree.command(name="purge", description="Delete messages", guild=GUILD)
@app_commands.checks.has_permissions(manage_messages=True)
async def purge(i: discord.Interaction, amount: int):
    await i.response.defer(ephemeral=True)
    deleted = await i.channel.purge(limit=amount)
    await i.followup.send(embed=embed("🧹 Purge", f"Deleted {len(deleted)} messages"), ephemeral=True)

# 9 SLOWMODE
@bot.tree.command(name="slowmode", description="Set slowmode", guild=GUILD)
@app_commands.checks.has_permissions(manage_channels=True)
async def slowmode(i: discord.Interaction, seconds: int):
    await i.channel.edit(slowmode_delay=seconds)
    await i.response.send_message(embed=embed("Slowmode", f"Set to {seconds}s"))

# 10 LOCK
@bot.tree.command(name="lock", description="Lock channel", guild=GUILD)
@app_commands.checks.has_permissions(manage_channels=True)
async def lock(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=False)
    await i.response.send_message(embed=embed("🔒 Locked", "Channel locked"))

# 11 UNLOCK
@bot.tree.command(name="unlock", description="Unlock channel", guild=GUILD)
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=True)
    await i.response.send_message(embed=embed("🔓 Unlocked", "Channel unlocked"))

# 12 NICK
@bot.tree.command(name="nick", description="Change nickname", guild=GUILD)
@app_commands.checks.has_permissions(manage_nicknames=True)
async def nick(i: discord.Interaction, member: discord.Member, nickname: str):
    await member.edit(nick=nickname)
    await i.response.send_message(embed=embed("Nickname", f"{member.mention} → {nickname}"))

# 13 ROLE ADD
@bot.tree.command(name="roleadd", description="Add role", guild=GUILD)
@app_commands.checks.has_permissions(manage_roles=True)
async def roleadd(i: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await i.response.send_message(embed=embed("Role Added", f"{role.mention} to {member.mention}"))

# 14 ROLE REMOVE
@bot.tree.command(name="roleremove", description="Remove role", guild=GUILD)
@app_commands.checks.has_permissions(manage_roles=True)
async def roleremove(i: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await i.response.send_message(embed=embed("Role Removed", f"{role.mention} from {member.mention}"))

# 15 LOCKDOWN
@bot.tree.command(name="lockdown", description="Server lockdown", guild=GUILD)
@app_commands.checks.has_permissions(administrator=True)
async def lockdown(i: discord.Interaction):
    for c in i.guild.text_channels:
        await c.set_permissions(i.guild.default_role, send_messages=False)
    await i.response.send_message(embed=embed("🚨 Lockdown", "Server locked"))

# 16 UNLOCKDOWN
@bot.tree.command(name="unlockdown", description="End lockdown", guild=GUILD)
@app_commands.checks.has_permissions(administrator=True)
async def unlockdown(i: discord.Interaction):
    for c in i.guild.text_channels:
        await c.set_permissions(i.guild.default_role, send_messages=True)
    await i.response.send_message(embed=embed("✅ Lockdown Ended", "Server unlocked"))

# 17 USERINFO
@bot.tree.command(name="userinfo", description="User info", guild=GUILD)
async def userinfo(i: discord.Interaction, member: discord.Member):
    e = embed(f"{member}", f"Joined: {member.joined_at.date()}\nCreated: {member.created_at.date()}")
    e.set_thumbnail(url=member.display_avatar.url)
    await i.response.send_message(embed=e)

# 18 SERVERINFO
@bot.tree.command(name="serverinfo", description="Server info", guild=GUILD)
async def serverinfo(i: discord.Interaction):
    g = i.guild
    e = embed(g.name, f"Members: {g.member_count}\nCreated: {g.created_at.date()}")
    e.set_thumbnail(url=g.icon.url if g.icon else None)
    await i.response.send_message(embed=e)

# 19 AVATAR
@bot.tree.command(name="avatar", description="Get avatar", guild=GUILD)
async def avatar(i: discord.Interaction, member: discord.Member):
    e = embed(f"{member}'s Avatar", ""); e.set_image(url=member.display_avatar.url)
    await i.response.send_message(embed=e)

bot.run(TOKEN)
