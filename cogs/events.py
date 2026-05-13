import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import config

EVENT_COLORS = {
    "Training":    0x5865F2,
    "Raid":        0xED4245,
    "Meeting":     0xFEE75C,
    "Tryout":      0xFF8C00,
    "Social":      0x57F287,
    "Other":       0x99AAB5,
}

RSVP_EMOJI = "🎉"


def parse_links(links_str: str) -> list[tuple[str, str]]:
    """Parse 'Label|URL, Label2|URL2' into list of (label, url) tuples."""
    results = []
    if not links_str:
        return results
    for item in links_str.split(","):
        item = item.strip()
        if "|" in item:
            label, url = item.split("|", 1)
            results.append((label.strip(), url.strip()))
        elif item.startswith("http"):
            results.append(("Link", item))
    return results[:5]  # Max 5 links


class EventLinkView(discord.ui.View):
    """Persistent view with up to 5 link buttons."""
    def __init__(self, links: list[tuple[str, str]]):
        super().__init__(timeout=None)
        for label, url in links:
            self.add_item(discord.ui.Button(
                label=label,
                url=url,
                style=discord.ButtonStyle.link
            ))


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _is_staff(self, interaction: discord.Interaction) -> bool:
        staff_role_id = config.get("staff_role_id")
        admin_role_id = config.get("admin_role_id")
        allowed = []
        if staff_role_id:
            allowed.append(int(staff_role_id))
        if admin_role_id:
            allowed.append(int(admin_role_id))
        if not allowed:
            return interaction.user.guild_permissions.manage_guild
        return any(r.id in allowed for r in interaction.user.roles)

    @app_commands.guild_only()
    @app_commands.command(name="event", description="Post a new event announcement with RSVP.")
    @app_commands.describe(
        event_type="Type of event",
        title="Event title",
        description="Event details",
        date="Date and time (e.g. May 15 at 5PM EST)",
        host="Who is hosting",
        location="Where it takes place (e.g. game link or server)",
        links='Optional buttons: format as "Label|URL, Label2|URL2" (up to 5)',
    )
    @app_commands.choices(event_type=[
        app_commands.Choice(name="Training",  value="Training"),
        app_commands.Choice(name="Raid",      value="Raid"),
        app_commands.Choice(name="Meeting",   value="Meeting"),
        app_commands.Choice(name="Tryout",    value="Tryout"),
        app_commands.Choice(name="Social",    value="Social"),
        app_commands.Choice(name="Other",     value="Other"),
    ])
    async def event(
        self,
        interaction: discord.Interaction,
        event_type: app_commands.Choice[str],
        title: str,
        description: str,
        date: str,
        host: str,
        location: str = "TBA",
        links: str = None,
    ):
        if not self._is_staff(interaction):
            await interaction.response.send_message("❌ Staff role required.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        channel_id = config.get("events_channel_id")
        channel = self.bot.get_channel(int(channel_id)) if channel_id else interaction.channel

        color = EVENT_COLORS.get(event_type.value, 0x99AAB5)

        embed = discord.Embed(
            title=f"📣 {event_type.value} — {title}",
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="📅 Date & Time", value=date,     inline=True)
        embed.add_field(name="👤 Host",         value=host,     inline=True)
        embed.add_field(name="📍 Location",     value=location, inline=True)
        embed.add_field(
            name=f"{RSVP_EMOJI} RSVP",
            value=f"React with {RSVP_EMOJI} to attend!\n**0 attending**",
            inline=False
        )
        embed.set_footer(text=f"Posted by {interaction.user.display_name} • GlacierBot")

        # Build link buttons if provided
        parsed_links = parse_links(links) if links else []
        view = EventLinkView(parsed_links) if parsed_links else None

        msg = await channel.send("@everyone", embed=embed, view=view)
        await msg.add_reaction(RSVP_EMOJI)

        await interaction.followup.send(f"✅ Event posted in {channel.mention}!", ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        if str(payload.emoji) != RSVP_EMOJI:
            return
        await self._update_rsvp(payload.channel_id, payload.message_id)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        if str(payload.emoji) != RSVP_EMOJI:
            return
        await self._update_rsvp(payload.channel_id, payload.message_id)

    async def _update_rsvp(self, channel_id: int, message_id: int):
        events_channel_id = config.get("events_channel_id")
        if not events_channel_id or channel_id != int(events_channel_id):
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return
        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            return
        if not message.embeds:
            return

        count = 0
        for reaction in message.reactions:
            if str(reaction.emoji) == RSVP_EMOJI:
                count = max(0, reaction.count - 1)
                break

        embed = message.embeds[0]
        new_embed = embed.copy()
        for i, field in enumerate(new_embed.fields):
            if "RSVP" in field.name:
                new_embed.set_field_at(
                    i,
                    name=f"{RSVP_EMOJI} RSVP",
                    value=f"React with {RSVP_EMOJI} to attend!\n**{count} attending**",
                    inline=False
                )
                break

        try:
            await message.edit(embed=new_embed)
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))
