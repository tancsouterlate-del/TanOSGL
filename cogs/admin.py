import discord
from discord import app_commands
from discord.ext import commands
import config


def is_admin(interaction: discord.Interaction) -> bool:
    allowed = ["The Administrator", "Class-X Overwatch"]
    return any(r.name in allowed for r in interaction.user.roles)


def is_staff(interaction: discord.Interaction) -> bool:
    allowed = ["The Administrator", "Class-X Overwatch", "Class O", "Class A"]
    return any(r.name in allowed for r in interaction.user.roles)


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.guild_only()
    @app_commands.command(name="setup", description="Configure GlacierBot channels and roles.")
    @app_commands.describe(
        applications_channel="Channel where Roblox applications are posted",
        suggestions_channel="Channel where suggestions get reactions",
        events_channel="Channel where events are posted",
        staff_role="Role that can post events",
        admin_role="Role that can use admin commands",
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        applications_channel: discord.TextChannel = None,
        suggestions_channel: discord.TextChannel = None,
        events_channel: discord.TextChannel = None,
        staff_role: discord.Role = None,
        admin_role: discord.Role = None,
    ):
        await interaction.response.defer(ephemeral=True)
        if not is_admin(interaction):
            await interaction.followup.send("❌ Class-X Overwatch or The Administrator role required.", ephemeral=True)
            return

        if applications_channel:
            config.set_value("application_channel_id", applications_channel.id)
        if suggestions_channel:
            config.set_value("suggestions_channel_id", suggestions_channel.id)
        if events_channel:
            config.set_value("events_channel_id", events_channel.id)
        if staff_role:
            config.set_value("staff_role_id", staff_role.id)
        if admin_role:
            config.set_value("admin_role_id", admin_role.id)

        cfg = config.load()
        app_ch = f"<#{cfg['application_channel_id']}>" if cfg.get("application_channel_id") else "⚠️ Not set"
        sug_ch = f"<#{cfg['suggestions_channel_id']}>" if cfg.get("suggestions_channel_id") else "⚠️ Not set"
        evt_ch = f"<#{cfg['events_channel_id']}>"      if cfg.get("events_channel_id")      else "⚠️ Not set"
        s_role = f"<@&{cfg['staff_role_id']}>"         if cfg.get("staff_role_id")          else "⚠️ Not set"
        a_role = f"<@&{cfg['admin_role_id']}>"         if cfg.get("admin_role_id")          else "⚠️ Not set"

        embed = discord.Embed(title="⚙️ GlacierBot — Configuration", color=0x5865F2)
        embed.add_field(name="Applications Channel", value=app_ch, inline=False)
        embed.add_field(name="Suggestions Channel",  value=sug_ch, inline=False)
        embed.add_field(name="Events Channel",       value=evt_ch, inline=False)
        embed.add_field(name="Staff Role",           value=s_role, inline=True)
        embed.add_field(name="Admin Role",           value=a_role, inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="set_webhook_secret", description="Set the secret key for Roblox application webhooks.")
    @app_commands.describe(secret="Secret string that Roblox will send in the Authorization header")
    async def set_webhook_secret(self, interaction: discord.Interaction, secret: str):
        await interaction.response.defer(ephemeral=True)
        if not is_admin(interaction):
            await interaction.followup.send("❌ Class-X Overwatch or The Administrator role required.", ephemeral=True)
            return
        config.set_value("application_webhook_secret", secret)
        await interaction.followup.send("✅ Webhook secret saved!", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="set_announcement_channel", description="Set the channel for TanOS community announcements.")
    @app_commands.describe(channel="Channel where announcements will be posted")
    async def set_announcement_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        if not is_admin(interaction):
            await interaction.followup.send("❌ Class-X Overwatch or The Administrator role required.", ephemeral=True)
            return
        config.set_value("announcement_channel_id", channel.id)
        await interaction.followup.send(f"✅ Announcement channel set to {channel.mention}!", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="set_relay_secret", description="Set the shared secret key for TanOS relay security.")
    @app_commands.describe(secret="Secret key — must match what TanOS has configured")
    async def set_relay_secret(self, interaction: discord.Interaction, secret: str):
        await interaction.response.defer(ephemeral=True)
        if not is_admin(interaction):
            await interaction.followup.send("❌ Class-X Overwatch or The Administrator role required.", ephemeral=True)
            return
        config.set_value("relay_secret", secret)
        await interaction.followup.send("✅ Relay secret saved!", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="status", description="Show current GlacierBot configuration.")
    async def status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not is_admin(interaction):
            await interaction.followup.send("❌ Class-X Overwatch or The Administrator role required.", ephemeral=True)
            return

        cfg = config.load()
        app_ch = f"<#{cfg['application_channel_id']}>" if cfg.get("application_channel_id") else "⚠️ Not set"
        sug_ch = f"<#{cfg['suggestions_channel_id']}>" if cfg.get("suggestions_channel_id") else "⚠️ Not set"
        evt_ch = f"<#{cfg['events_channel_id']}>"      if cfg.get("events_channel_id")      else "⚠️ Not set"
        s_role = f"<@&{cfg['staff_role_id']}>"         if cfg.get("staff_role_id")          else "⚠️ Not set"
        secret = "✅ Set" if cfg.get("application_webhook_secret") else "⚠️ Not set"

        embed = discord.Embed(title="🖥️ GlacierBot — Status", color=0x5865F2)
        embed.add_field(name="Applications Channel", value=app_ch, inline=False)
        embed.add_field(name="Suggestions Channel",  value=sug_ch, inline=False)
        embed.add_field(name="Events Channel",       value=evt_ch, inline=False)
        embed.add_field(name="Staff Role",           value=s_role, inline=True)
        embed.add_field(name="Webhook Secret",       value=secret, inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)


    @app_commands.guild_only()
    @app_commands.command(name="restart", description="Restart GlacierBot.")
    async def restart(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not is_admin(interaction):
            await interaction.followup.send("❌ Class-X Overwatch or The Administrator role required.", ephemeral=True)
            return
        await interaction.followup.send("♻️ Restarting GlacierBot...", ephemeral=True)
        import os, sys
        os.execv(sys.executable, [sys.executable] + sys.argv)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
