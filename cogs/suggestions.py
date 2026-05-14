import discord
from discord.ext import commands
from datetime import datetime

SUGGESTIONS_CHANNEL_ID = 1084917356419096647
FORWARD_CHANNEL_ID = 1089548190577086577
FEATURED_CHANNEL_ID = 1370158487312662529

UPVOTE_EMOJI = "<:reaction_approved:1280928878369439807>"
DOWNVOTE_EMOJI = "<:reaction_denied:1280946099284213822>"
NC_EMOJI = "<:nc:1268768073523925013>"
UPVOTE_THRESHOLD = 15


def build_suggestion_embed(message: discord.Message) -> discord.Embed:
    guild = message.guild
    embed = discord.Embed(
        title="SUGGESTION",
        description=message.content,
        color=0x5865F2,
        timestamp=message.created_at
    )
    embed.set_author(
        name=f"{guild.name}",
        icon_url=guild.icon.url if guild.icon else None
    )
    embed.add_field(
        name="",
        value=f"[↗ Jump to suggestion]({message.jump_url})",
        inline=False
    )
    embed.add_field(name="SUGGESTED BY", value=message.author.mention, inline=False)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.set_footer(
        text=f"{guild.name}",
        icon_url=guild.icon.url if guild.icon else None
    )
    # Attach image if any
    if message.attachments:
        embed.set_image(url=message.attachments[0].url)
    return embed


def build_result_embed(suggestion_embed: discord.Embed, feedback: str, approved: bool, dev: discord.Member) -> discord.Embed:
    color = 0x57F287 if approved else 0xED4245
    result_text = "<:reaction_approved:1280928878369439807> Approved" if approved else "<:reaction_denied:1280946099284213822> Denied"

    embed = discord.Embed(
        title="SUGGESTION",
        description=suggestion_embed.description,
        color=color,
        timestamp=datetime.utcnow()
    )
    embed.set_author(
        name=suggestion_embed.author.name if suggestion_embed.author else "Suggestion",
        icon_url=suggestion_embed.author.icon_url if suggestion_embed.author else None
    )
    for field in suggestion_embed.fields:
        embed.add_field(name=field.name, value=field.value, inline=field.inline)
    embed.add_field(
        name="DEVELOPER RESPONSE",
        value=f"{dev.mention} ({dev.top_role.name}): {feedback}",
        inline=False
    )
    embed.add_field(name="RESULT", value=result_text, inline=False)
    embed.set_thumbnail(url=suggestion_embed.thumbnail.url if suggestion_embed.thumbnail else None)
    embed.set_footer(
        text=suggestion_embed.footer.text if suggestion_embed.footer else "",
        icon_url=suggestion_embed.footer.icon_url if suggestion_embed.footer else None
    )
    if suggestion_embed.image:
        embed.set_image(url=suggestion_embed.image.url)
    return embed


class FeedbackModal(discord.ui.Modal, title="Developer Feedback"):
    feedback = discord.ui.TextInput(
        label="Your feedback",
        style=discord.TextStyle.paragraph,
        placeholder="Write your response to this suggestion...",
        required=True,
        max_length=1000,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()


class ApproveView(discord.ui.View):
    def __init__(self, suggestion_embed: discord.Embed, feedback: str, dev: discord.Member, original_message_id: int, forwarded_message_id: int, forward_channel_id: int):
        super().__init__(timeout=120)
        self.suggestion_embed = suggestion_embed
        self.feedback = feedback
        self.dev = dev
        self.original_message_id = original_message_id
        self.forwarded_message_id = forwarded_message_id
        self.forward_channel_id = forward_channel_id

    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._submit(interaction, approved=True)

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._submit(interaction, approved=False)

    async def _submit(self, interaction: discord.Interaction, approved: bool):
        await interaction.response.defer(ephemeral=True)
        result_embed = build_result_embed(self.suggestion_embed, self.feedback, approved, self.dev)

        # Edit the forwarded message in dev server
        try:
            forward_channel = interaction.client.get_channel(self.forward_channel_id)
            if forward_channel:
                forwarded_msg = await forward_channel.fetch_message(self.forwarded_message_id)
                await forwarded_msg.edit(embed=result_embed, view=None)
        except Exception as e:
            print(f"[Suggestions] Could not edit forwarded message: {e}")

        # Post to featured channel in main server
        featured_channel = interaction.client.get_channel(FEATURED_CHANNEL_ID)
        if featured_channel:
            await featured_channel.send(embed=result_embed)

        # React to original suggestion
        try:
            suggestions_channel = interaction.client.get_channel(SUGGESTIONS_CHANNEL_ID)
            if suggestions_channel:
                original = await suggestions_channel.fetch_message(self.original_message_id)
                await original.add_reaction("<:reaction_approved:1280928878369439807>" if approved else "<:reaction_denied:1280946099284213822>")
        except Exception as e:
            print(f"[Suggestions] Could not react to original: {e}")

        await interaction.followup.send(
            f"{'✅ Approved' if approved else '❌ Denied'} and posted to featured channel!",
            ephemeral=True
        )


class DevFeedbackView(discord.ui.View):
    def __init__(self, suggestion_embed: discord.Embed, original_message_id: int, forwarded_message_id: int):
        super().__init__(timeout=None)
        self.suggestion_embed = suggestion_embed
        self.original_message_id = original_message_id
        self.forwarded_message_id = forwarded_message_id

    @discord.ui.button(label="Developer Feedback", style=discord.ButtonStyle.primary, custom_id="dev_feedback")
    async def dev_feedback(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = FeedbackModal()
        await interaction.response.send_modal(modal)
        await modal.wait()

        feedback_text = modal.feedback.value
        approve_view = ApproveView(self.suggestion_embed, feedback_text, interaction.user, self.original_message_id, self.forwarded_message_id, FORWARD_CHANNEL_ID)
        await interaction.followup.send(
            "Feedback recorded! Now choose a result:",
            view=approve_view,
            ephemeral=True
        )


class Suggestions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id != SUGGESTIONS_CHANNEL_ID:
            return

        # Auto react with upvote and downvote
        try:
            await message.add_reaction(UPVOTE_EMOJI)
            await message.add_reaction(DOWNVOTE_EMOJI)
        except Exception as e:
            print(f"[Suggestions] React error: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.channel_id != SUGGESTIONS_CHANNEL_ID:
            return
        if payload.user_id == self.bot.user.id:
            return
        if str(payload.emoji) != UPVOTE_EMOJI:
            return

        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        # Count upvotes (subtract 1 for the bot's own reaction)
        upvote_count = 0
        already_forwarded = False
        for reaction in message.reactions:
            if str(reaction.emoji) == UPVOTE_EMOJI:
                upvote_count = reaction.count - 1
            if str(reaction.emoji) == NC_EMOJI:
                already_forwarded = True

        if upvote_count >= UPVOTE_THRESHOLD and not already_forwarded:
            # React with NC emoji to mark as forwarded
            try:
                await message.add_reaction(NC_EMOJI)
            except Exception as e:
                print(f"[Suggestions] NC react error: {e}")

            # Forward to dev server
            forward_channel = self.bot.get_channel(FORWARD_CHANNEL_ID)
            if not forward_channel:
                print("[Suggestions] Forward channel not found.")
                return

            embed = build_suggestion_embed(message)
            forwarded_msg = await forward_channel.send(embed=embed, view=discord.ui.View())
            view = DevFeedbackView(embed, message.id, forwarded_msg.id)
            await forwarded_msg.edit(view=view)
            print(f"[Suggestions] Forwarded suggestion {message.id} to dev server.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Suggestions(bot))
