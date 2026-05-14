import discord
from discord.ext import commands
from datetime import datetime
import config

BUGREPORT_CHANNEL_ID = 1084917359426412664
FORWARD_CHANNEL_ID = 1408840563679039548
FIXED_CHANNEL_ID = 1084917360642773153
REACT_EMOJI = "<:Yes:1214749336865349632>"


def build_report_embed(message: discord.Message) -> discord.Embed:
    guild = message.guild
    channel = message.channel

    embed = discord.Embed(
        title="BUG REPORT",
        description=message.content,
        color=0xED4245,
        timestamp=message.created_at
    )
    embed.set_author(
        name=f"{guild.name} - {channel.name}",
        icon_url=guild.icon.url if guild.icon else None
    )
    embed.add_field(
        name="",
        value=f"[↗ Jump to report]({message.jump_url})",
        inline=False
    )
    embed.add_field(
        name="REPORTED BY",
        value=message.author.mention,
        inline=False
    )
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.set_footer(
        text=f"{guild.name}",
        icon_url=guild.icon.url if guild.icon else None
    )
    return embed


def build_fixed_embed(report_embed: discord.Embed, fixed_by: discord.Member) -> discord.Embed:
    embed = discord.Embed(
        title="✅ BUG FIXED",
        description=report_embed.description,
        color=0x57F287,
        timestamp=datetime.utcnow()
    )
    embed.set_author(
        name=report_embed.author.name if report_embed.author else "Bug Report",
        icon_url=report_embed.author.icon_url if report_embed.author else None
    )
    for field in report_embed.fields:
        embed.add_field(name=field.name, value=field.value, inline=field.inline)
    embed.add_field(name="FIXED BY", value=fixed_by.mention, inline=False)
    embed.set_thumbnail(url=report_embed.thumbnail.url if report_embed.thumbnail else None)
    embed.set_footer(
        text=report_embed.footer.text if report_embed.footer else "",
        icon_url=report_embed.footer.icon_url if report_embed.footer else None
    )
    return embed


class MarkFixedView(discord.ui.View):
    def __init__(self, original_message_id: int):
        super().__init__(timeout=None)
        self.original_message_id = original_message_id

    @discord.ui.button(label="Mark as Fixed", style=discord.ButtonStyle.success, custom_id="mark_fixed")
    async def mark_fixed(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        # Build fixed embed from current embed
        if not interaction.message.embeds:
            await interaction.followup.send("❌ Could not find the report embed.", ephemeral=True)
            return

        report_embed = interaction.message.embeds[0]
        fixed_embed = build_fixed_embed(report_embed, interaction.user)

        # Edit the forwarded message to show fixed
        await interaction.message.edit(embed=fixed_embed, view=None)

        # Post to fixed bugs channel in main server
        fixed_channel = interaction.client.get_channel(FIXED_CHANNEL_ID)
        if fixed_channel:
            await fixed_channel.send(embed=fixed_embed)

        # Try to add a checkmark reaction to the original report
        try:
            report_channel = interaction.client.get_channel(BUGREPORT_CHANNEL_ID)
            if report_channel:
                original_msg = await report_channel.fetch_message(self.original_message_id)
                await original_msg.add_reaction("✅")
        except Exception as e:
            print(f"[BugReports] Could not react to original: {e}")


class BugReports(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.add_view(MarkFixedView(0))  # Re-register persistent view on startup

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id != BUGREPORT_CHANNEL_ID:
            return

        # React to the report
        try:
            await message.add_reaction(REACT_EMOJI)
        except Exception as e:
            print(f"[BugReports] React error: {e}")

        # Forward to dev server
        forward_channel = self.bot.get_channel(FORWARD_CHANNEL_ID)
        if not forward_channel:
            print("[BugReports] Forward channel not found.")
            return

        embed = build_report_embed(message)
        view = MarkFixedView(message.id)
        await forward_channel.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(BugReports(bot))
