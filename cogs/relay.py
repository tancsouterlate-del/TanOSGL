"""
Relay endpoint — receives announcement data from TanOS and posts
it directly to the public server channel as a proper bot message.
This allows full embed rendering with author icons and footer icons.
"""
import discord
from discord.ext import commands
from aiohttp import web
import asyncio
import os
import config

RELAY_SECRET = os.environ.get("RELAY_SECRET", "")


class Relay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.runner = None
        self.site = None
        bot.loop.create_task(self.start_relay_server())

    async def start_relay_server(self):
        await self.bot.wait_until_ready()
        app = web.Application()
        app.router.add_post("/announce", self.handle_announce)
        app.router.add_get("/health", self.health_check)

        self.runner = web.AppRunner(app)
        await self.runner.setup()
        port = int(os.environ.get("PORT", 5000))
        self.site = web.TCPSite(self.runner, "0.0.0.0", port)
        await self.site.start()
        print(f"[Relay] Listening on port {port}")

    async def health_check(self, request: web.Request) -> web.Response:
        return web.Response(text="OK")

    async def handle_announce(self, request: web.Request) -> web.Response:
        # Verify secret
        secret = config.get("relay_secret") or RELAY_SECRET
        if secret:
            auth = request.headers.get("Authorization", "")
            if auth != f"Bearer {secret}":
                return web.Response(status=401, text="Unauthorized")

        try:
            data = await request.json()
        except Exception:
            return web.Response(status=400, text="Invalid JSON")

        channel_id = config.get("announcement_channel_id")
        if not channel_id:
            return web.Response(status=500, text="Announcement channel not configured")

        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            try:
                channel = await self.bot.fetch_channel(int(channel_id))
            except Exception:
                return web.Response(status=500, text="Channel not found")

        try:
            embed_data = data.get("embed", {})
            ping = data.get("ping", False)

            # Rebuild embed from dict
            embed = discord.Embed.from_dict(embed_data)

            content = "@here" if ping else ""
            await channel.send(content=content, embed=embed)
            print(f"[Relay] Announcement posted to {channel.name}")
            return web.Response(status=200, text="OK")
        except Exception as e:
            print(f"[Relay] Error posting announcement: {e}")
            return web.Response(status=500, text=str(e))

    def cog_unload(self):
        if self.runner:
            asyncio.create_task(self.runner.cleanup())


async def setup(bot: commands.Bot):
    await bot.add_cog(Relay(bot))
