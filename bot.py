import discord
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

EXTENSIONS = [
    "cogs.applications",
    "cogs.suggestions",
    "cogs.events",
    "cogs.admin",
    "cogs.relay",
]

@bot.event
async def on_ready():
    print(f"[GlacierBot] Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"[GlacierBot] Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"[GlacierBot] Sync error: {e}")

async def main():
    async with bot:
        for ext in EXTENSIONS:
            await bot.load_extension(ext)
            print(f"[GlacierBot] Loaded: {ext}")
        token = os.environ.get("DISCORD_TOKEN")
        if not token:
            raise ValueError("Set the DISCORD_TOKEN environment variable.")
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
