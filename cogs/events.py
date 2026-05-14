import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import asyncio
import config

EVENT_COLORS = {
    "Tryout":          0xFF8C00,
    "Event":           0x5865F2,
    "Server Start Up": 0x57F287,
}

EVENT_TYPES = ["Tryout", "Event", "Server Start Up"]
RSVP_EMOJI = "🎉"
DM_TIMEOUT = 120


def parse_links(links_str: str) -> list[tuple[str, str]]:
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
    return results[:5]


def build_embed(data: dict) -> discord.Embed:
    color = EVENT_COLORS.get(data["event_type"], 0x99AAB5)
    embed = discord.Embed(
        title=f"📣 {data['event_type']} — {data['title']}",
        description=data["description"],
        color=color,
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="📅 Date & Time", value=data["date"],     inline=True)
    embed.add_field(name="👤 Host",         value=data["host"],     inline=True)
    embed.add_field(name="📍 Location",     value=data["location"], inline=True)
    embed.add_field(
        name=f"{RSVP_EMOJI} RSVP",
        value=f"React with {RSVP_EMOJI} to attend!\n**0 attending**",
        inline=False
    )
    embed.set_footer(text=f"Posted by {data['author']} • GlacierBot")
    return embed


class EventLinkView(discord.ui.View):
    def __init__(self, links: list[tuple[str, str]]):
        super().__init__(timeout=None)
        for label, url in links:
            self.add_item(discord.ui.Button(label=label, url=url, style=discord.ButtonStyle.link))


class AddLinksModal(discord.ui.Modal, title="Add Event Links"):
    links_input = discord.ui.TextInput(
        label="Links",
        style=discord.TextStyle.paragraph,
        placeholder='Format: Label|URL, Label2|URL2\nExample: Join Game|https://roblox.com/...',
        required=False,
        max_length=500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()


class LinksView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=DM_TIMEOUT)
        self.links_str = None

    @discord.ui.button(label="➕ Add Links", style=discord.ButtonStyle.primary)
    async def add_links(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AddLinksModal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        self.links_str = modal.links_input.value or ""
        self.stop()
        await interaction.edit_original_response(content="✅ Links saved!", view=None)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.links_str = ""
        self.stop()
        await interaction.response.edit_message(content="Skipped links.", view=None)


class PingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=DM_TIMEOUT)
        self.chosen = ""

    @discord.ui.button(label="No one", style=discord.ButtonStyle.secondary)
    async def no_ping(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.chosen = ""
        self.stop()
        await interaction.response.edit_message(content="Ping: **No one**", view=None)

    @discord.ui.button(label="@here", style=discord.ButtonStyle.primary)
    async def here_ping(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.chosen = "@here"
        self.stop()
        await interaction.response.edit_message(content="Ping: **@here**", view=None)

    @discord.ui.button(label="@everyone", style=discord.ButtonStyle.danger)
    async def everyone_ping(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.chosen = "@everyone"
        self.stop()
        await interaction.response.edit_message(content="Ping: **@everyone**", view=None)


class ConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=DM_TIMEOUT)
        self.confirmed = None

    @discord.ui.button(label="✅ Post Event", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        self.stop()
        await interaction.response.edit_message(content="✅ Posting event...", view=None)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        self.stop()
        await interaction.response.edit_message(content="❌ Event cancelled.", view=None)


class EventTypeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=DM_TIMEOUT)
        self.chosen = None
        for et in EVENT_TYPES:
            btn = discord.ui.Button(label=et, style=discord.ButtonStyle.primary)
            btn.callback = self._make_callback(et)
            self.add_item(btn)

    def _make_callback(self, event_type: str):
        async def callback(interaction: discord.Interaction):
            self.chosen = event_type
            self.stop()
            await interaction.response.edit_message(content=f"Event type: **{event_type}**", view=None)
        return callback


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

    async def _ask(self, dm: discord.DMChannel, user: discord.User, prompt: str) -> str | None:
        await dm.send(prompt)
        def check(m):
            return m.author.id == user.id and isinstance(m.channel, discord.DMChannel)
        try:
            msg = await self.bot.wait_for("message", check=check, timeout=DM_TIMEOUT)
            return msg.content.strip()
        except asyncio.TimeoutError:
            await dm.send("⏱️ Timed out. Use `/event` again to restart.")
            return None

    @app_commands.guild_only()
    @app_commands.command(name="event", description="Create a new event announcement via DM.")
    async def event(self, interaction: discord.Interaction):
        if not self._is_staff(interaction):
            await interaction.response.send_message("❌ Staff role required.", ephemeral=True)
            return

        await interaction.response.send_message("📬 Check your DMs! I'll walk you through creating the event.", ephemeral=True)

        user = interaction.user
        try:
            dm = await user.create_dm()
        except discord.Forbidden:
            await interaction.followup.send("❌ I couldn't DM you. Please enable DMs from server members.", ephemeral=True)
            return

        await dm.send("# 📣 New Event Setup\nLet's build your event. You can type `cancel` at any time to stop.")

        # Step 1: Event type
        await dm.send("# Step 1 of 6 — Event Type\nWhat type of event is this?")
        type_view = EventTypeView()
        await dm.send("Choose an event type:", view=type_view)
        await type_view.wait()
        if not type_view.chosen:
            await dm.send("⏱️ Timed out. Use `/event` again to restart.")
            return
        event_type = type_view.chosen

        # Step 2: Title
        val = await self._ask(dm, user, "# Step 2 of 6 — Event Title\nExample: `Iron Fist Tryout`")
        if val is None or val.lower() == "cancel":
            await dm.send("❌ Event creation cancelled.")
            return
        title = val

        # Step 3: Description
        val = await self._ask(dm, user, "# Step 3 of 6 — Description\nDescribe your event.")
        if val is None or val.lower() == "cancel":
            await dm.send("❌ Event creation cancelled.")
            return
        description = val

        # Step 4: Date & Time
        val = await self._ask(dm, user, "# Step 4 of 6 — Date & Time\nExample: `May 20 at 5PM EST`")
        if val is None or val.lower() == "cancel":
            await dm.send("❌ Event creation cancelled.")
            return
        date = val

        # Step 5: Host
        val = await self._ask(dm, user, "# Step 5 of 6 — Host\nWho is hosting this event?")
        if val is None or val.lower() == "cancel":
            await dm.send("❌ Event creation cancelled.")
            return
        host = val

        # Step 6: Location
        val = await self._ask(dm, user, "# Step 6 of 6 — Location\nWhere does this take place? (e.g. game link, server name, or TBA)")
        if val is None or val.lower() == "cancel":
            await dm.send("❌ Event creation cancelled.")
            return
        location = val

        # Links
        links_view = LinksView()
        await dm.send("# Optional — Links\nWant to add any link buttons to the event?", view=links_view)
        await links_view.wait()
        parsed_links = parse_links(links_view.links_str) if links_view.links_str else []

        # Ping
        ping_view = PingView()
        await dm.send("# Who should be pinged when this posts?", view=ping_view)
        await ping_view.wait()
        ping_content = ping_view.chosen or ""

        data = {
            "event_type": event_type,
            "title": title,
            "description": description,
            "date": date,
            "host": host,
            "location": location,
            "author": user.display_name,
        }

        # Preview
        embed = build_embed(data)
        await dm.send("# 👀 Preview\nHere's how your event will look:")
        if parsed_links:
            await dm.send(embed=embed, view=EventLinkView(parsed_links))
        else:
            await dm.send(embed=embed)

        confirm_view = ConfirmView()
        await dm.send("Ready to post?", view=confirm_view)
        await confirm_view.wait()

        if not confirm_view.confirmed:
            return

        # Post to events channel
        channel_id = config.get("events_channel_id")
        channel = self.bot.get_channel(int(channel_id)) if channel_id else None
        if not channel:
            await dm.send("❌ Events channel not configured. Ask an admin to run `/setup`.")
            return

        final_view = EventLinkView(parsed_links) if parsed_links else None
        msg = await channel.send(ping_content, embed=embed, view=final_view)
        await msg.add_reaction(RSVP_EMOJI)
        await dm.send(f"✅ Event posted in {channel.mention}!")

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
