import os
import discord
import sqlite3
import datetime
from discord.ext import commands
from discord import app_commands
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
GUILD = discord.Object(id=GUILD_ID)
def init_db():
    con = sqlite3.connect("warns.db")
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS warns (user_id INTEGER, guild_id INTEGER, reason TEXT, ts TEXT)")
    con.commit()
    con.close()
init_db()
@bot.event
async def on_ready():
    print(f"DEBUG GUILD_ID={os.getenv('GUILD_ID')}")
    print(f"DEBUG commands in tree BEFORE sync={len(bot.tree.get_commands())}")
    bot.tree.clear_commands(guild=GUILD)
    await bot.tree.sync(guild=GUILD)
    synced = await bot.tree.sync(guild=GUILD)
    print(f"Windowra Guard PRO online - {len(synced)} commands synced")
@bot.event
async def on_member_join(member):
    role_id = int(os.getenv("AUTO_ROLE_ID","0"))
    if role_id:
        r = member.guild.get_role(role_id)
        if r:
            try: await member.add_roles(r)
            except: pass
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
    await interaction.response.send_message(f"Removed timeout", ephemeral=True)
@bot.tree.command(name="warn", description="Warn a member", guild=GUILD)
@app_commands.default_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    con = sqlite3.connect("warns.db"); cur = con.cursor()
    cur.execute("INSERT INTO warns VALUES (?,?,?,?)", (member.id, interaction.guild_id, reason, datetime.datetime.utcnow().isoformat()))
    con.commit(); con.close()
    await interaction.response.send_message(f"Warned {member}", ephemeral=True)
@bot.tree.command(name="warnings", description="Check warnings", guild=GUILD)
async def warnings(interaction: discord.Interaction, member: discord.Member):
    con = sqlite3.connect("warns.db"); cur = con.cursor()
    cur.execute("SELECT reason, ts FROM warns WHERE user_id=? AND guild_id=?", (member.id, interaction.guild_id))
    rows = cur.fetchall(); con.close()
    if not rows: return await interaction.response.send_message("No warnings", ephemeral=True)
    msg = "\n".join([f"{i+1}. {r}" for i,(r,t) in enumerate(rows)])
    await interaction.response.send_message(msg, ephemeral=True)
@bot.tree.command(name="clearwarns", description="Clear warnings", guild=GUILD)
@app_commands.default_permissions(moderate_members=True)
async def clearwarns(interaction: discord.Interaction, member: discord.Member):
    con = sqlite3.connect("warns.db"); cur = con.cursor()
    cur.execute("DELETE FROM warns WHERE user_id=? AND guild_id=?", (member.id, interaction.guild_id))
    con.commit(); con.close()
    await interaction.response.send_message("Cleared", ephemeral=True)
@bot.tree.command(name="purge", description="Delete messages", guild=GUILD)
@app_commands.default_permissions(manage_messages=True)
async def purge(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"Deleted {amount}", ephemeral=True)
@bot.tree.command(name="slowmode", description="Set slowmode", guild=GUILD)
@app_commands.default_permissions(manage_channels=True)
async def slowmode(interaction: discord.Interaction, seconds: int):
    await interaction.channel.edit(slowmode_delay=seconds)
    await interaction.response.send_message(f"Set to {seconds}s", ephemeral=True)
@bot.tree.command(name="lock", description="Lock channel", guild=GUILD)
@app_commands.default_permissions(manage_channels=True)
async def lock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message("Locked", ephemeral=True)
@bot.tree.command(name="unlock", description="Unlock channel", guild=GUILD)
@app_commands.default_permissions(manage_channels=True)
async def unlock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message("Unlocked", ephemeral=True)
@bot.tree.command(name="userinfo", description="Get user info", guild=GUILD)
async def userinfo(interaction: discord.Interaction, member: discord.Member):
    e = discord.Embed(title=member.display_name, color=0x5865F2)
    e.add_field(name="ID", value=member.id)
    e.set_thumbnail(url=member.display_avatar.url)
    await interaction.response.send_message(embed=e)
@bot.tree.command(name="serverinfo", description="Server info", guild=GUILD)
async def serverinfo(interaction: discord.Interaction):
    g = interaction.guild
    await interaction.response.send_message(f"{g.name} - {g.member_count} members", ephemeral=True)
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
async def embed_cmd(interaction: discord.Interaction, title: str, description: str):
    await interaction.channel.send(embed=discord.Embed(title=title, description=description, color=0xFFD700))
    await interaction.response.send_message("Sent", ephemeral=True)
@bot.tree.command(name="poll", description="Create poll", guild=GUILD)
async def poll(interaction: discord.Interaction, question: str):
    m = await interaction.response.send_message(embed=discord.Embed(title="Poll", description=question))
@bot.tree.command(name="help", description="List commands", guild=GUILD)
async def help_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("19 commands loaded", ephemeral=True)
bot.run(os.getenv("DISCORD_TOKEN"))
