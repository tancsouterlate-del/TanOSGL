import discord
from discord.ext import commands
from aiohttp import web
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Shared aiohttp app — cogs register routes onto this
bot.web_app = web.Application()

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

        # Start the single shared web server
        await bot.wait_until_ready()
        runner = web.AppRunner(bot.web_app)
        await runner.setup()
        port = int(os.environ.get("PORT", 5000))
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        print(f"[GlacierBot] Web server listening on port {port}")

        token = os.environ.get("DISCORD_TOKEN")
        if not token:
            raise ValueError("Set the DISCORD_TOKEN environment variable.")
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
