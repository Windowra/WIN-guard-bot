import os
import discord
import sqlite3
import datetime
from discord.ext import commands
from discord import app_commands

# ----- SETUP -----
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

GUILD_ID = int(os.getenv("GUILD_ID", "0"))
GUILD = discord.Object(id=GUILD_ID)

MOD_LOG = int(os.getenv("MOD_LOG_CHANNEL_ID", "0"))
WELCOME = int(os.getenv("WELCOME_CHANNEL_ID", "0"))
LEAVE = int(os.getenv("LEAVE_CHANNEL_ID", "0"))
AUTO_ROLE = int(os.getenv("AUTO_ROLE_ID", "0"))

def init_db():
    con = sqlite3.connect("warns.db")
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS warns (user_id INTEGER, guild_id INTEGER, reason TEXT, ts TEXT)")
    con.commit()
    con.close()

init_db()

# ----- EVENTS -----
@bot.event
async def on_ready():
    print(f"DEBUG GUILD_ID={os.getenv('GUILD_ID')}")
    print(f"DEBUG commands in tree BEFORE sync={len(bot.tree.get_commands())}")
    try:
        bot.tree.clear_commands(guild=GUILD)
        await bot.tree.sync(guild=GUILD)
        synced = await bot.tree.sync(guild=GUILD)
        print(f"Windowra Guard PRO online - {len(synced)} commands synced")
    except Exception as e:
        print(f"Sync error: {e}")

@bot.event
async def on_member_join(member):
    if AUTO_ROLE:
        role = member.guild.get_role(AUTO_ROLE)
        if role: 
            try: await member.add_roles(role)
            except: pass
    if WELCOME:
        ch = bot.get_channel(WELCOME)
        if ch: await ch.send(f"Welcome {member.mention} to **{member.guild.name}**!")

@bot.event
async def on_member_remove(member):
    if LEAVE:
        ch = bot.get_channel(LEAVE)
        if ch: await ch.send(f"{member.name} has left the server.")

# ----- COMMANDS (19 total) -----
@bot.tree.command(name="ping", description="Check bot latency", guild=GUILD)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! {round(bot.latency*1000)}ms", ephemeral=True)

@bot.tree.command(name="ban", description="Ban a member", guild=GUILD)
@app_commands.default_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"Banned {member}", ephemeral=True)

@bot.tree.command(name="kick", description="Kick a member", guild=GUILD)
@app_commands.default_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"Kicked {member}", ephemeral=True)

@bot.tree.command(name="timeout", description="Timeout a member", guild=GUILD)
@app_commands.default_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason"):
    await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
    await interaction.response.send_message(f"Timed out {member} for {minutes}m", ephemeral=True)

@bot.tree.command(name="untimeout", description="Remove timeout", guild=GUILD)
@app_commands.default_permissions(moderate_members=True)
async def untimeout(interaction: discord.Interaction, member: discord.Member):
    await member.timeout(None)
    await interaction.response.send_message(f"Removed timeout from {member}", ephemeral=True)

@bot.tree.command(name="warn", description="Warn a member", guild=GUILD)
@app_commands.default_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    con = sqlite3.connect("warns.db")
    cur = con.cursor()
    cur.execute("INSERT INTO warns VALUES (?,?,?,?)", (member.id, interaction.guild_id, reason, datetime.datetime.utcnow().isoformat()))
    con.commit(); con.close()
    await interaction.response.send_message(f"Warned {member}: {reason}", ephemeral=True)

@bot.tree.command(name="warnings", description="Check warnings", guild=GUILD)
async def warnings(interaction: discord.Interaction, member: discord.Member):
    con = sqlite3.connect("warns.db"); cur = con.cursor()
    cur.execute("SELECT reason, ts FROM warns WHERE user_id=? AND guild_id=?", (member.id, interaction.guild_id))
    rows = cur.fetchall(); con.close()
    if not rows: return await interaction.response.send_message("No warnings", ephemeral=True)
    msg = "\n".join([f"{i+1}. {r} ({t[:10]})" for i,(r,t) in enumerate(rows)])
    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="clearwarns", description="Clear warnings", guild=GUILD)
@app_commands.default_permissions(moderate_members=True)
async def clearwarns(interaction: discord.Interaction, member: discord.Member):
    con = sqlite3.connect("warns.db"); cur = con.cursor()
    cur.execute("DELETE FROM warns WHERE user_id=? AND guild_id=?", (member.id, interaction.guild_id))
    con.commit(); con.close()
    await interaction.response.send_message(f"Cleared warns for {member}", ephemeral=True)

@bot.tree.command(name="purge", description="Delete messages", guild=GUILD)
@app_commands.default_permissions(manage_messages=True)
async def purge(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"Deleted {amount} messages", ephemeral=True)

@bot.tree.command(name="slowmode", description="Set slowmode", guild=GUILD)
@app_commands.default_permissions(manage_channels=True)
async def slowmode(interaction: discord.Interaction, seconds: int):
    await interaction.channel.edit(slowmode_delay=seconds)
    await interaction.response.send_message(f"Slowmode set to {seconds}s", ephemeral=True)

@bot.tree.command(name="lock", description="Lock channel", guild=GUILD)
@app_commands.default_permissions(manage_channels=True)
async def lock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message("Channel locked", ephemeral=True)

@bot.tree.command(name="unlock", description="Unlock channel", guild=GUILD)
@app_commands.default_permissions(manage_channels=True)
async def unlock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message("Channel unlocked", ephemeral=True)

@bot.tree.command(name="userinfo", description="Get user info", guild=GUILD)
async def userinfo(interaction: discord.Interaction, member: discord.Member):
    embed = discord.Embed(title=member.display_name, color=discord.Color.blurple())
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d"))
    embed.set_thumbnail(url=member.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="serverinfo", description="Server info", guild=GUILD)
async def serverinfo(interaction: discord.Interaction):
    g = interaction.guild
    await interaction.response.send_message(f"**{g.name}** - {g.member_count} members", ephemeral=True)

@bot.tree.command(name="avatar", description="Get avatar", guild=GUILD)
async def avatar(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(member.display_avatar.url)

@bot.tree.command(name="say", description="Make bot say something", guild=GUILD)
@app_commands.default_permissions(manage_messages=True)
async def say(interaction: discord.Interaction, message: str):
    await interaction.response.send_message("Sent", ephemeral=True)
    await interaction.channel.send(message)

@bot.tree.command(name="embed", description="Send embed", guild=GUILD)
@app_commands.default_permissions(manage_messages=True)
async def embed(interaction: discord.Interaction, title: str, description: str):
    em = discord.Embed(title=title, description=description, color=discord.Color.gold())
    await interaction.response.send_message("Sent", ephemeral=True)
    await interaction.channel.send(embed=em)

@bot.tree.command(name="poll", description="Create poll", guild=GUILD)
async def poll(interaction: discord.Interaction, question: str):
    em = discord.Embed(title="Poll", description=question, color=discord.Color.green())
    await interaction.response.send_message(embed=em)
    msg = await interaction.original_response()
    await msg.add_reaction("👍"); await msg.add_reaction("👎")

@bot.tree.command(name="help", description="List commands", guild=GUILD)
async def help_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("19 moderation & utility slash commands loaded!", ephemeral=True)

# ----- RUN -----
bot.run(os.getenv("DISCORD_TOKEN"))
