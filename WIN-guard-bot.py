import os, discord, asyncio
from discord.ext import commands
from collections import defaultdict, deque
from datetime import datetime, timedelta

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
LOG_ID = int(os.getenv("MOD_LOG_CHANNEL_ID"))
WELCOME_ID = int(os.getenv("WELCOME_CHANNEL_ID"))
ROLE_ID = int(os.getenv("AUTO_ROLE_ID", 0))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

spam = defaultdict(lambda: deque(maxlen=5))
BAD = ["discord.gg/", "nigger", "faggot"] # add more

@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print("Windowra Guard PRO online")

@bot.event
async def on_member_join(m):
    if ROLE_ID: await m.add_roles(m.guild.get_role(ROLE_ID))
    ch = bot.get_channel(WELCOME_ID)
    e = discord.Embed(title=f"Welcome to Windowra, {m.name}!", description="Read #rules and enjoy!", color=0x5865F2)
    e.set_thumbnail(url=m.display_avatar.url)
    e.set_footer(text="Windowra • Official Community")
    await ch.send(content=m.mention, embed=e)

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    # anti-spam
    spam[msg.author.id].append(datetime.utcnow())
    if len(spam[msg.author.id])==5 and (spam[msg.author.id][-1]-spam[msg.author.id][0]).total_seconds()<5:
        await msg.delete(); await msg.author.timeout(timedelta(minutes=5)); await log(f"Auto-timeout {msg.author} for spam")
        return
    if any(b in msg.content.lower() for b in BAD):
        await msg.delete(); await log(f"Deleted bad word from {msg.author}")
    await bot.process_commands(msg)

async def log(text):
    ch = bot.get_channel(LOG_ID)
    e = discord.Embed(description=text, timestamp=datetime.utcnow(), color=0x2B2D31)
    await ch.send(embed=e)

@bot.tree.command(name="purge", description="Delete messages", guild=discord.Object(id=GUILD_ID))
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def purge(i: discord.Interaction, amount: int):
    await i.channel.purge(limit=amount); await i.response.send_message(f"Deleted {amount}", ephemeral=True); await log(f"{i.user} purged {amount} in {i.channel}")

@bot.tree.command(name="lockdown", description="Lock channel", guild=discord.Object(id=GUILD_ID))
async def lock(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("Locked"); await log("Lockdown")

@bot.tree.command(name="unlock", description="Unlock channel", guild=discord.Object(id=GUILD_ID))
async def unlock(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("Unlocked")

bot.run(TOKEN)
