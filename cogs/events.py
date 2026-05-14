import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import asyncio
import config

RSVP_EMOJI = "<:nc:1268768073523925013>"
DM_TIMEOUT = 120

RANK_PRIORITY = [
    "The Administrator",
    "Class - X",
    "Class - O",
    "Class - A",
]

DEPT_ICONS = {
    "Class-X Overwatch":       "https://i.imgur.com/P91p044.png",
    "Department of Operations": "https://i.imgur.com/SZBhEYW.png",
    "Security Corps":           "https://i.imgur.com/YmKQvyU.png",
    "The Red Wolves":           "https://i.imgur.com/ha1QsY8.png",
    "Regulations Department":   "https://i.imgur.com/NOYucyC.png",
    "Innovation Department":    "https://i.imgur.com/MHBqZYo.png",
    "Engineering Department":   "https://i.imgur.com/lhQVavk.png",
    "Board of Advisors":        "https://i.imgur.com/YHtkpf1.png",
}

DEPT_CHOICES = [
    "Class - X",
    "Department of Operations",
    "Security Corps",
    "The Red Wolves",
    "Regulations Department",
    "Innovation Department",
    "Engineering Department",
]


def get_rank(member: discord.Member) -> str:
    role_names = [r.name for r in member.roles]
    for rank in RANK_PRIORITY:
        if rank in role_names:
            return rank
    return "Staff"


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


def build_embed(dept: str, title: str, description: str, author_name: str, rank: str, parsed_links: list) -> discord.Embed:
    icon_url = DEPT_ICONS.get(dept, "")

    embed = discord.Embed(
        title=title,
        description=description,
        color=0x2C2F33,
        timestamp=datetime.utcnow()
    )
    if icon_url:
        embed.set_thumbnail(url=icon_url)
    embed.set_footer(text=f"{author_name} • {rank}")
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
        placeholder="Format: Label|URL, Label2|URL2\nExample: Join Game|https://roblox.com/...",
        required=False,
        max_length=500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()


class LinksView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=DM_TIMEOUT)
        self.links_str = None

    @discord.ui.button(label="Add Links", style=discord.ButtonStyle.primary)
    async def add_links(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AddLinksModal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        self.links_str = modal.links_input.value or ""
        self.stop()
        await interaction.edit_original_response(content="✅ Links saved!", view=None)

    @discord.ui.button(label="No Links", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.links_str = ""
        self.stop()
        await interaction.response.edit_message(content="No links added.", view=None)


class DeptView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=DM_TIMEOUT)
        self.chosen = None
        for dept in DEPT_CHOICES:
            btn = discord.ui.Button(label=dept, style=discord.ButtonStyle.primary)
            btn.callback = self._make_callback(dept)
            self.add_item(btn)

    def _make_callback(self, dept: str):
        async def callback(interaction: discord.Interaction):
            self.chosen = dept
            self.stop()
            await interaction.response.edit_message(content=f"Department: **{dept}**", view=None)
        return callback


class EventTypeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=DM_TIMEOUT)
        self.chosen = None

    @discord.ui.button(label="General Event", style=discord.ButtonStyle.primary)
    async def general_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.chosen = "General Event"
        self.stop()
        await interaction.response.edit_message(content="Type: **General Event**", view=None)


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


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _is_staff(self, interaction: discord.Interaction) -> bool:
        allowed = ["The Administrator", "Class - X", "Class - O", "Class - A"]
        return any(r.name in allowed for r in interaction.user.roles)

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
            await interaction.response.send_message("❌ Class A or above required.", ephemeral=True)
            return

        await interaction.response.send_message("📬 Check your DMs!", ephemeral=True)

        user = interaction.user
        member = interaction.guild.get_member(user.id)
        rank = get_rank(member) if member else "Staff"

        try:
            dm = await user.create_dm()
        except discord.Forbidden:
            await interaction.followup.send("❌ I couldn't DM you. Please enable DMs from server members.", ephemeral=True)
            return

        await dm.send("# 📣 New Event\nLet's build your event. Type `cancel` at any time to stop.")

        # Step 1: Event type
        await dm.send("# Step 1 — Event Type\nWhat kind of event is this?")
        type_view = EventTypeView()
        await dm.send("Choose an event type:", view=type_view)
        await type_view.wait()
        if not type_view.chosen:
            await dm.send("⏱️ Timed out. Use `/event` again to restart.")
            return

        # Step 2: Department
        await dm.send("# Step 2 — Department\nWhich department is hosting this event?")
        dept_view = DeptView()
        await dm.send("Choose a department:", view=dept_view)
        await dept_view.wait()
        if not dept_view.chosen:
            await dm.send("⏱️ Timed out. Use `/event` again to restart.")
            return
        dept = dept_view.chosen

        # Step 3: Title
        title = await self._ask(dm, user, "# Step 3 — Title\nWhat's the title of your event?\nExample: `Iron Fist Tryout`")
        if title is None or title.lower() == "cancel":
            await dm.send("❌ Event creation cancelled.")
            return

        # Step 4: Description
        description = await self._ask(dm, user, "# Step 4 — Description\nDescribe your event.")
        if description is None or description.lower() == "cancel":
            await dm.send("❌ Event creation cancelled.")
            return

        # Step 5: Links
        links_view = LinksView()
        await dm.send("# Step 5 — Links\nWould you like to add any link buttons?", view=links_view)
        await links_view.wait()
        parsed_links = parse_links(links_view.links_str) if links_view.links_str else []

        # Step 6: Ping
        ping_view = PingView()
        await dm.send("# Step 6 — Ping\nWho should be pinged when this posts?", view=ping_view)
        await ping_view.wait()
        ping_content = ping_view.chosen or ""

        # Build embed
        embed = build_embed(dept, title, description, user.display_name, rank, parsed_links)

        # Preview
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
        await dm.send(f"✅ Posted in {channel.mention}!")

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
        footer_text = new_embed.footer.text or ""
        await message.edit(embed=new_embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))
