import discord
from discord.ext import commands
from aiohttp import web
import os
import config

RELAY_SECRET = os.environ.get("RELAY_SECRET", "")


class Relay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Register routes on the shared web app
        bot.web_app.router.add_post("/announce", self.handle_announce)

    async def handle_announce(self, request: web.Request) -> web.Response:
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

            embed = discord.Embed.from_dict(embed_data)

            # Ping @everyone for Rank proposals, @here for all others
            proposal_type = embed_data.get("author", {}).get("name", "")
            if ping:
                content = "@everyone" if proposal_type == "Rank" else "@here"
            else:
                content = ""

            await channel.send(content=content, embed=embed)
            print(f"[Relay] Announcement posted to {channel.name} (type={proposal_type}, ping={content or 'none'})")
            return web.Response(status=200, text="OK")
        except Exception as e:
            print(f"[Relay] Error posting announcement: {e}")
            return web.Response(status=500, text=str(e))


async def setup(bot: commands.Bot):
    await bot.add_cog(Relay(bot))
