import os, discord, aiosqlite, re
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

async def log(action, mod, target, reason="-"):
    ch = bot.get_channel(MOD_LOG)
    e = discord.Embed(title=action, color=0x5865F2, timestamp=datetime.utcnow())
    e.add_field(name="Mod", value=mod.mention)
    e.add_field(name="Target", value=str(target))
    e.add_field(name="Reason", value=reason, inline=False)
    await ch.send(embed=e)

async def init_db():
    async with aiosqlite.connect("guard.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS warns (user_id INTEGER, mod_id INTEGER, reason TEXT, time TEXT)")
        await db.commit()

@bot.event
async def on_ready():
    await init_db()
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Windowra Guard PRO online")

@bot.event
async def on_member_join(m):
    if AUTO_ROLE_ID and AUTO_ROLE_ID.isdigit():
        await m.add_roles(m.guild.get_role(int(AUTO_ROLE_ID)), reason="Auto-role")
    ch = bot.get_channel(WELCOME_ID)
    e = discord.Embed(title=f"Welcome to Windowra, {m.name}!", description="Check #rules and enjoy!", color=0x57F287)
    e.set_thumbnail(url=m.display_avatar.url)
    e.set_footer(text=f"Member #{m.guild.member_count}")
    await ch.send(content=m.mention, embed=e)

@bot.event
async def on_member_remove(m):
    ch = bot.get_channel(LEAVE_ID)
    e = discord.Embed(description=f"**{m.name}** has left the server", color=0xED4245, timestamp=datetime.utcnow())
    e.set_footer(text=f"We now have {m.guild.member_count} members")
    await ch.send(embed=e)

# Auto-mod
SPAM = {}
@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    now = datetime.utcnow()
    SPAM.setdefault(msg.author.id, [])
    SPAM[msg.author.id].append(now)
    SPAM[msg.author.id] = [t for t in SPAM[msg.author.id] if (now - t).seconds < 5]
    if len(SPAM[msg.author.id]) > 5:
        await msg.delete()
        try: await msg.author.timeout(timedelta(minutes=5), reason="Spam")
        except: pass
    if re.search(r"discord\.gg/\w+|https?://", msg.content) and not msg.author.guild_permissions.manage_messages:
        await msg.delete()
    await bot.process_commands(msg)

# Commands
@bot.tree.command(guild=discord.Object(id=GUILD_ID), description="Ban a member")
async def ban(i: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.ban(reason=reason); await log("BAN", i.user, member, reason)
    await i.response.send_message(f"🔨 Banned {member}", ephemeral=True)

@bot.tree.command(guild=discord.Object(id=GUILD_ID), description="Kick a member")
async def kick(i: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.kick(reason=reason); await log("KICK", i.user, member, reason)
    await i.response.send_message(f"👢 Kicked {member}", ephemeral=True)

@bot.tree.command(guild=discord.Object(id=GUILD_ID), description="Timeout a member")
async def timeout(i: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason"):
    await member.timeout(timedelta(minutes=minutes), reason=reason); await log("TIMEOUT", i.user, member, f"{minutes}m | {reason}")
    await i.response.send_message(f"⏱️ {member} timed out for {minutes}m", ephemeral=True)

@bot.tree.command(guild=discord.Object(id=GUILD_ID), description="Remove timeout")
async def untimeout(i: discord.Interaction, member: discord.Member):
    await member.timeout(None); await log("UNTIMEOUT", i.user, member)
    await i.response.send_message(f"✅ {member} released", ephemeral=True)

@bot.tree.command(guild=discord.Object(id=GUILD_ID), description="Delete messages")
async def purge(i: discord.Interaction, amount: int):
    await i.response.defer(ephemeral=True)
    deleted = await i.channel.purge(limit=amount)
    await i.followup.send(f"🧹 Deleted {len(deleted)} messages", ephemeral=True)

@bot.tree.command(guild=discord.Object(id=GUILD_ID), description="Lock channel")
async def lockdown(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=False)
    await i.response.send_message("🔒 Channel locked")

@bot.tree.command(guild=discord.Object(id=GUILD_ID), description="Unlock channel")
async def unlock(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=True)
    await i.response.send_message("🔓 Channel unlocked")

@bot.tree.command(guild=discord.Object(id=GUILD_ID), description="Set slowmode")
async def slowmode(i: discord.Interaction, seconds: int):
    await i.channel.edit(slowmode_delay=seconds)
    await i.response.send_message(f"🐢 Slowmode set to {seconds}s")

@bot.tree.command(guild=discord.Object(id=GUILD_ID), description="Warn a member")
async def warn(i: discord.Interaction, member: discord.Member, reason: str):
    async with aiosqlite.connect("guard.db") as db:
        await db.execute("INSERT INTO warns VALUES (?,?,?,?)", (member.id, i.user.id, reason, datetime.utcnow().isoformat()))
        await db.commit()
    await log("WARN", i.user, member, reason)
    await i.response.send_message(f"⚠️ Warned {member}", ephemeral=True)

@bot.tree.command(guild=discord.Object(id=GUILD_ID), description="View warnings")
async def warnings(i: discord.Interaction, member: discord.Member):
    async with aiosqlite.connect("guard.db") as db:
        cur = await db.execute("SELECT reason,time FROM warns WHERE user_id=?", (member.id,))
        rows = await cur.fetchall()
    if not rows: return await i.response.send_message("No warnings", ephemeral=True)
    desc = "\n".join([f"• {r[0]} - {r[1][:10]}" for r in rows[:10]])
    await i.response.send_message(embed=discord.Embed(title=f"Warnings for {member}", description=desc, color=0xFAA61A), ephemeral=True)

@bot.tree.command(guild=discord.Object(id=GUILD_ID), description="Clear warnings")
async def clearwarns(i: discord.Interaction, member: discord.Member):
    async with aiosqlite.connect("guard.db") as db:
        await db.execute("DELETE FROM warns WHERE user_id=?", (member.id,))
        await db.commit()
    await i.response.send_message(f"✅ Cleared warnings for {member}", ephemeral=True)

@bot.tree.command(guild=discord.Object(id=GUILD_ID), description="Change nickname")
async def nick(i: discord.Interaction, member: discord.Member, nickname: str):
    await member.edit(nick=nickname); await i.response.send_message(f"✏️ Nickname set", ephemeral=True)

@bot.tree.command(guild=discord.Object(id=GUILD_ID), description="Add role")
async def roleadd(i: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.add_roles(role); await i.response.send_message(f"➕ Added {role.name}", ephemeral=True)

@bot.tree.command(guild=discord.Object(id=GUILD_ID), description="Remove role")
async def roleremove(i: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.remove_roles(role); await i.response.send_message(f"➖ Removed {role.name}", ephemeral=True)

@bot.tree.command(guild=discord.Object(id=GUILD_ID), description="Server info")
async def serverinfo(i: discord.Interaction):
    g = i.guild
    e = discord.Embed(title=g.name, color=0x5865F2)
    e.add_field(name="Members", value=g.member_count); e.add_field(name="Owner", value=g.owner.mention)
    e.set_thumbnail(url=g.icon.url if g.icon else None)
    await i.response.send_message(embed=e)

@bot.tree.command(guild=discord.Object(id=GUILD_ID), description="User info")
async def userinfo(i: discord.Interaction, member: discord.Member):
    e = discord.Embed(title=member.display_name, color=0x5865F2)
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name="Joined Discord", value=member.created_at.date())
    e.add_field(name="Joined Server", value=member.joined_at.date())
    await i.response.send_message(embed=e)

@bot.tree.command(guild=discord.Object(id=GUILD_ID), description="Show avatar")
async def avatar(i: discord.Interaction, member: discord.Member):
    await i.response.send_message(member.display_avatar.url)

@bot.tree.command(guild=discord.Object(id=GUILD_ID), description="Bot latency")
async def ping(i: discord.Interaction):
    await i.response.send_message(f"Pong! {round(bot.latency*1000)}ms")

@bot.tree.command(guild=discord.Object(id=GUILD_ID), description="Make bot say something")
async def say(i: discord.Interaction, message: str):
    await i.response.send_message("Sent!", ephemeral=True)
    await i.channel.send(message)

bot.run(TOKEN)
