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
GUILD = discord.Object(id=GUILD_ID)

# ---------- DB ----------
async def init_db():
    async with aiosqlite.connect("guard.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS warns(user_id INTEGER, mod_id INTEGER, reason TEXT, time TEXT)")
        await db.commit()

# ---------- READY ----------
@bot.event
async def on_ready():
    await init_db()
    bot.tree.clear_commands(guild=GUILD)
    synced = await bot.tree.sync(guild=GUILD)
    print(f"Windowra Guard PRO ONLINE - {len(synced)} commands synced")

# ---------- WELCOME/LEAVE ----------
@bot.event
async def on_member_join(m):
    if AUTO_ROLE_ID and AUTO_ROLE_ID.isdigit():
        r = m.guild.get_role(int(AUTO_ROLE_ID))
        if r:
            try: await m.add_roles(r, reason="Auto-role")
            except: pass
    ch = bot.get_channel(WELCOME_ID)
    if ch:
        e = discord.Embed(title=f"Welcome {m.name}!", description="Read #rules and enjoy!", color=0x57F287)
        e.set_thumbnail(url=m.display_avatar.url)
        await ch.send(m.mention, embed=e)

@bot.event
async def on_member_remove(m):
    ch = bot.get_channel(LEAVE_ID)
    if ch:
        e = discord.Embed(description=f"**{m.name}** left the server", color=0xED4245, timestamp=datetime.utcnow())
        await ch.send(embed=e)

# ---------- AUTO-MOD ----------
spam = {}
@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    now = datetime.utcnow()
    spam.setdefault(msg.author.id, [])
    spam[msg.author.id].append(now)
    spam[msg.author.id] = [t for t in spam[msg.author.id] if (now-t).total_seconds() < 5]
    if len(spam[msg.author.id]) > 5:
        try:
            await msg.delete()
            await msg.author.timeout(timedelta(minutes=5), reason="Spam")
        except: pass
    if re.search(r"discord\.gg/|discord\.com/invite", msg.content):
        if not msg.author.guild_permissions.manage_messages:
            try: await msg.delete()
            except: pass
    await bot.process_commands(msg)

# ---------- COMMANDS ----------
@bot.tree.command(guild=GUILD, description="Ban a member")
async def ban(i:discord.Interaction, member:discord.Member, reason:str="No reason"):
    await member.ban(reason=reason)
    await i.response.send_message(f"🔨 Banned {member}", ephemeral=True)

@bot.tree.command(guild=GUILD, description="Kick a member")
async def kick(i:discord.Interaction, member:discord.Member, reason:str="No reason"):
    await member.kick(reason=reason)
    await i.response.send_message(f"👢 Kicked {member}", ephemeral=True)

@bot.tree.command(guild=GUILD, description="Timeout a member")
async def timeout(i:discord.Interaction, member:discord.Member, minutes:int, reason:str="No reason"):
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await i.response.send_message(f"⏱️ {member} for {minutes}m", ephemeral=True)

@bot.tree.command(guild=GUILD, description="Remove timeout")
async def untimeout(i:discord.Interaction, member:discord.Member):
    await member.timeout(None)
    await i.response.send_message("✅ Untimed", ephemeral=True)

@bot.tree.command(guild=GUILD, description="Purge messages")
async def purge(i:discord.Interaction, amount:int):
    await i.response.defer(ephemeral=True)
    deleted = await i.channel.purge(limit=amount)
    await i.followup.send(f"🧹 Deleted {len(deleted)}")

@bot.tree.command(guild=GUILD, description="Lock channel")
async def lockdown(i:discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=False)
    await i.response.send_message("🔒 Locked")

@bot.tree.command(guild=GUILD, description="Unlock channel")
async def unlock(i:discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=True)
    await i.response.send_message("🔓 Unlocked")

@bot.tree.command(guild=GUILD, description="Set slowmode")
async def slowmode(i:discord.Interaction, seconds:int):
    await i.channel.edit(slowmode_delay=seconds)
    await i.response.send_message(f"🐢 {seconds}s")

@bot.tree.command(guild=GUILD, description="Warn member")
async def warn(i:discord.Interaction, member:discord.Member, reason:str):
    async with aiosqlite.connect("guard.db") as db:
        await db.execute("INSERT INTO warns VALUES (?,?,?,?)", (member.id, i.user.id, reason, datetime.utcnow().isoformat()))
        await db.commit()
    await i.response.send_message("⚠️ Warned", ephemeral=True)

@bot.tree.command(guild=GUILD, description="View warnings")
async def warnings(i:discord.Interaction, member:discord.Member):
    async with aiosqlite.connect("guard.db") as db:
        cur = await db.execute("SELECT reason,time FROM warns WHERE user_id=?", (member.id,))
        rows = await cur.fetchall()
    if not rows: return await i.response.send_message("No warns", ephemeral=True)
    txt = "\n".join([f"• {r[0]}" for r in rows[:10]])
    await i.response.send_message(txt, ephemeral=True)

@bot.tree.command(guild=GUILD, description="Clear warnings")
async def clearwarns(i:discord.Interaction, member:discord.Member):
    async with aiosqlite.connect("guard.db") as db:
        await db.execute("DELETE FROM warns WHERE user_id=?", (member.id,))
        await db.commit()
    await i.response.send_message("✅ Cleared", ephemeral=True)

@bot.tree.command(guild=GUILD, description="Change nickname")
async def nick(i:discord.Interaction, member:discord.Member, nickname:str):
    await member.edit(nick=nickname)
    await i.response.send_message("✏️ Changed", ephemeral=True)

@bot.tree.command(guild=GUILD, description="Add role")
async def roleadd(i:discord.Interaction, member:discord.Member, role:discord.Role):
    await member.add_roles(role)
    await i.response.send_message(f"➕ {role.name}", ephemeral=True)

@bot.tree.command(guild=GUILD, description="Remove role")
async def roleremove(i:discord.Interaction, member:discord.Member, role:discord.Role):
    await member.remove_roles(role)
    await i.response.send_message(f"➖ {role.name}", ephemeral=True)

@bot.tree.command(guild=GUILD, description="Server info")
async def serverinfo(i:discord.Interaction):
    g = i.guild
    e = discord.Embed(title=g.name, color=0x5865F2)
    e.add_field(name="Members", value=g.member_count)
    e.add_field(name="Owner", value=str(g.owner))
    await i.response.send_message(embed=e)

@bot.tree.command(guild=GUILD, description="User info")
async def userinfo(i:discord.Interaction, member:discord.Member):
    e = discord.Embed(title=member.display_name, color=0x5865F2)
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d"))
    await i.response.send_message(embed=e)

@bot.tree.command(guild=GUILD, description="Avatar")
async def avatar(i:discord.Interaction, member:discord.Member):
    await i.response.send_message(member.display_avatar.url)

@bot.tree.command(guild=GUILD, description="Ping")
async def ping(i:discord.Interaction):
    await i.response.send_message(f"Pong {round(bot.latency*1000)}ms")

@bot.tree.command(guild=GUILD, description="Say something")
async def say(i:discord.Interaction, message:str):
    await i.response.send_message("Sent", ephemeral=True)
    await i.channel.send(message)

bot.run(TOKEN)
