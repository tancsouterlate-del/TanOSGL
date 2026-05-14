import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import asyncio
import config

RSVP_EMOJI = "🎉"
DM_TIMEOUT = 120

RANK_PRIORITY = [
    "Developer",
    "The Administrator",
    "Class-X",
    "Class O",
    "Class A",
]

def get_rank(member: discord.Member) -> str:
    role_names = [r.name for r in member.roles]
    for rank in RANK_PRIORITY:
        if rank in role_names:
            return rank
    return "Staff"


def build_ansi_embed(header: str, title: str, description: str, author_name: str, rank: str) -> discord.Embed:
    timestamp = datetime.utcnow().strftime("%B %d, %Y • %I:%M %p UTC")

    # ANSI color codes: \u001b[33m = yellow/orange, \u001b[0m = reset
    ansi_block = (
        f"```ansi\n"
        f"\u001b[2;33m[{header}]\u001b[0m\n"
        f"\n"
        f"\u001b[2;33m[Description]\u001b[0m\n"
        f"{description}\n"
        f"```"
    )

    embed = discord.Embed(
        title=title,
        description=ansi_block,
        color=0x2C2F33,
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"{author_name} • {rank} • {timestamp}")
    return embed


class ConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=DM_TIMEOUT)
        self.confirmed = None

    @discord.ui.button(label="✅ Post", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        self.stop()
        await interaction.response.edit_message(content="✅ Posting...", view=None)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        self.stop()
        await interaction.response.edit_message(content="❌ Cancelled.", view=None)


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
        allowed = ["The Administrator", "Class-X Overwatch", "Class O", "Class A"]
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
    @app_commands.command(name="event", description="Create a new event post via DM.")
    async def event(self, interaction: discord.Interaction):
        if not self._is_staff(interaction):
            await interaction.response.send_message("❌ Staff role required.", ephemeral=True)
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

        await dm.send("# 📣 New Event\nI'll ask you a few questions. Type `cancel` at any time to stop.\n")

        # Step 1: Header
        header = await self._ask(dm, user, "# Step 1 of 3 — Header\nWhat's the header?\nExample: `The Armed Gentlemen Tryout`")
        if header is None or header.lower() == "cancel":
            await dm.send("❌ Cancelled.")
            return

        # Step 2: Title
        title = await self._ask(dm, user, "# Step 2 of 3 — Title\nWhat's the title?\nExample: `The Armed Gentlemen Tryout`")
        if title is None or title.lower() == "cancel":
            await dm.send("❌ Cancelled.")
            return

        # Step 3: Description
        description = await self._ask(dm, user, "# Step 3 of 3 — Description\nDescribe your event. You can use multiple lines.")
        if description is None or description.lower() == "cancel":
            await dm.send("❌ Cancelled.")
            return

        # Ping
        ping_view = PingView()
        await dm.send("# Who should be pinged?", view=ping_view)
        await ping_view.wait()
        ping_content = ping_view.chosen or ""

        # Build embed
        embed = build_ansi_embed(header, title, description, user.display_name, rank)

        # Preview
        await dm.send("# 👀 Preview\nHere's how your post will look:")
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

        msg = await channel.send(ping_content, embed=embed)
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

        # Update RSVP count in footer or description
        current_desc = new_embed.description or ""
        # Append or update RSVP line at the end of the ansi block
        rsvp_line = f"\n**{RSVP_EMOJI} {count} attending**"
        if f"{RSVP_EMOJI}" in current_desc:
            lines = current_desc.rsplit(f"{RSVP_EMOJI}", 1)
            new_embed.description = lines[0] + f"{RSVP_EMOJI} {count} attending**"
        else:
            # Insert before closing ```
            new_embed.description = current_desc.rstrip("`").rstrip() + f"\n\n{RSVP_EMOJI} **{count} attending**\n```"

        try:
            await message.edit(embed=new_embed)
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))
