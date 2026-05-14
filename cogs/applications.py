import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from aiohttp import web
import config

APP_COLORS = {
    "staff":      0x5865F2,
    "moderator":  0xFF8C00,
    "builder":    0x57F287,
    "default":    0x99AAB5,
}


def build_application_embed(data: dict) -> discord.Embed:
    app_type  = data.get("type", "Application").title()
    username  = data.get("username", "Unknown")
    user_id   = data.get("userId", "")
    answers   = data.get("answers", {})
    submitted = data.get("timestamp", datetime.utcnow().strftime("%m/%d/%Y %I:%M %p UTC"))

    color = APP_COLORS.get(data.get("type", "").lower(), APP_COLORS["default"])

    embed = discord.Embed(
        title=f"{app_type} Application",
        color=color,
        timestamp=datetime.utcnow()
    )
    embed.set_author(name=f"{username} applied for {app_type}")

    if user_id:
        embed.add_field(
            name="Roblox Profile",
            value=f"[{username}](https://www.roblox.com/users/{user_id}/profile)",
            inline=True
        )

    embed.add_field(name="Username", value=username, inline=True)
    embed.add_field(name="Submitted", value=submitted, inline=True)

    for question, answer in answers.items():
        embed.add_field(name=question, value=answer or "No answer", inline=False)

    embed.set_footer(text="GlacierBot • Application System")
    return embed


class Applications(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Register routes on the shared web app
        bot.web_app.router.add_post("/application", self.handle_application)
        bot.web_app.router.add_get("/health", self.health_check)

    async def health_check(self, request: web.Request) -> web.Response:
        return web.Response(text="OK")

    async def handle_application(self, request: web.Request) -> web.Response:
        secret = config.get("application_webhook_secret")
        if secret:
            auth = request.headers.get("Authorization", "")
            if auth != f"Bearer {secret}":
                return web.Response(status=401, text="Unauthorized")

        try:
            data = await request.json()
        except Exception:
            return web.Response(status=400, text="Invalid JSON")

        channel_id = config.get("application_channel_id")
        if not channel_id:
            return web.Response(status=500, text="Application channel not configured")

        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            return web.Response(status=500, text="Channel not found")

        embed = build_application_embed(data)
        msg = await channel.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        print(f"[Applications] New application from {data.get('username', 'Unknown')}")
        return web.Response(status=200, text="OK")


async def setup(bot: commands.Bot):
    await bot.add_cog(Applications(bot))
