import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import asyncio
import config

# ── Role requirements ────────────────────────────────────────────────────────
ROLE_REQUIREMENTS = {
    "Class - D": "Test Subject",   # Test Subject can apply for Class D
    "Class - C": "Class - D",      # Class D can apply for Class C
    "Class - B": "Class - C",      # Class C can apply for Class B
}

# ── Questions per class ──────────────────────────────────────────────────────
QUESTIONS = {
    "Class - D": [
        "What is your Roblox username and profile link?",
        "What is the Nova Corporation?",
        "How did you find us?",
        "What are the 3 classes you can apply for?",
        "What is the name of the rulebook used by the Nova Corporation and its importance?",
        "Are you planning on joining any departments?",
        "Do you acknowledge that you are required to join the Roblox Group found in the information channel?",
    ],
    "Class - C": [
        "What is your Roblox username and profile link?",
        "What is the Nova Corporation security force named?",
        "Describe where you are and aren't allowed to go into in TS-Z.",
        "When was the Nova Corporation founded? [Lore]",
        "What is the Regulations Department?",
        "What is the Innovation Department and its importance?",
        "What guns are Nova Corporation Members allowed to use?",
    ],
    "Class - B": [
        "What is your Roblox username and profile link?",
        "When someone breaks a law, where do you report it?",
        "What is the proper raid protocol?",
        "Describe how you are required to act On-site.",
        "What is the Class-X Overwatch and its importance?",
        "What department maintains the logistics of the Nova Corporation?",
    ],
}

# ── Embed colors ─────────────────────────────────────────────────────────────
COLORS = {
    "Class - D": 0x5865F2,
    "Class - C": 0xFF8C00,
    "Class - B": 0x57F287,
}

CORP_ICON = "https://cdn.discordapp.com/attachments/1503851691567484938/1503922126573277301/06c691b96fe3c13569c640075f6330f4.png?ex=6a051c20&is=6a03caa0&hm=5b11744ce96ae6cb5d6e7d708e913b81f29fd80ba1dccd01cc2264a03cdd2d10&"

active_sessions = {}


def build_application_embed(class_type: str, applicant: discord.Member, answers: dict) -> discord.Embed:
    color = COLORS.get(class_type, 0x99AAB5)
    embed = discord.Embed(title=class_type, color=color)
    embed.set_author(name=f"{class_type} Application", icon_url=CORP_ICON)
    embed.set_thumbnail(url=CORP_ICON)

    for question, answer in answers.items():
        embed.add_field(name=question, value=answer, inline=False)

    embed.set_footer(text=f"{datetime.utcnow().strftime('%m/%d/%Y %I:%M %p')} UTC")
    return embed


async def ask(dm: discord.DMChannel, question: str, user_id: int, bot, step: int, total: int) -> str | None:
    await dm.send(f"**Question {step}/{total}**\n{question}")
    def check(m):
        return m.author.id == user_id and isinstance(m.channel, discord.DMChannel)
    try:
        msg = await bot.wait_for("message", check=check, timeout=300)
        if msg.content.strip().lower() == "cancel":
            return None
        return msg.content.strip()
    except asyncio.TimeoutError:
        await dm.send("⏰ Session timed out. Run `/apply` again to restart.")
        return None


class Applications(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_applicable_classes(self, member: discord.Member) -> list[str]:
        """Return which classes this member can apply for based on their roles."""
        role_names = [r.name for r in member.roles]
        available = []
        for class_type, required_role in ROLE_REQUIREMENTS.items():
            if required_role in role_names:
                available.append(class_type)
        return available

    @app_commands.guild_only()
    @app_commands.command(name="apply", description="Submit a class application via DM.")
    async def apply(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id in active_sessions:
            await interaction.followup.send("⚠️ You already have an active application session in your DMs!", ephemeral=True)
            return

        available = self._get_applicable_classes(interaction.user)
        if not available:
            await interaction.followup.send(
                "❌ You don't have the required role to apply for any class.\n"
                "You need **Test Subject** to apply for Class D.",
                ephemeral=True
            )
            return

        # Open DMs
        try:
            dm = await interaction.user.create_dm()
            await dm.send(
                "👋 Welcome to the Nova Corporation application system!\n"
                "Type `cancel` at any time to stop.\n\n"
                f"You can apply for: **{', '.join(available)}**"
            )
        except discord.Forbidden:
            await interaction.followup.send("❌ I couldn't DM you! Enable DMs from server members.", ephemeral=True)
            return

        await interaction.followup.send("📬 Check your DMs!", ephemeral=True)
        active_sessions[interaction.user.id] = True

        try:
            # Choose class if multiple available
            if len(available) == 1:
                chosen_class = available[0]
            else:
                options = "\n".join([f"**{i+1}.** {c}" for i, c in enumerate(available)])
                await dm.send(f"Which class are you applying for?\n\n{options}\n\nReply with the number.")
                def check(m):
                    return m.author.id == interaction.user.id and isinstance(m.channel, discord.DMChannel)
                while True:
                    try:
                        reply = await self.bot.wait_for("message", check=check, timeout=300)
                        if reply.content.strip().lower() == "cancel":
                            await dm.send("❌ Application cancelled.")
                            active_sessions.pop(interaction.user.id, None)
                            return
                        if reply.content.strip().isdigit():
                            idx = int(reply.content.strip()) - 1
                            if 0 <= idx < len(available):
                                chosen_class = available[idx]
                                break
                        await dm.send(f"❌ Reply with a number between 1 and {len(available)}.")
                    except asyncio.TimeoutError:
                        await dm.send("⏰ Session timed out.")
                        active_sessions.pop(interaction.user.id, None)
                        return

            questions = QUESTIONS[chosen_class]
            await dm.send(f"✅ Starting **{chosen_class}** application — {len(questions)} questions.\n\nTake your time and answer thoroughly!")

            answers = {}
            for i, question in enumerate(questions, start=1):
                answer = await ask(dm, question, interaction.user.id, self.bot, i, len(questions))
                if answer is None:
                    await dm.send("❌ Application cancelled.")
                    active_sessions.pop(interaction.user.id, None)
                    return
                answers[question] = answer

            # Preview
            preview_embed = build_application_embed(chosen_class, interaction.user, answers)
            await dm.send("✅ Here's a preview of your application:")
            await dm.send(embed=preview_embed)
            await dm.send("Reply `yes` to submit or `no` to cancel.")

            def confirm_check(m):
                return m.author.id == interaction.user.id and isinstance(m.channel, discord.DMChannel)
            try:
                confirm = await self.bot.wait_for("message", check=confirm_check, timeout=300)
            except asyncio.TimeoutError:
                await dm.send("⏰ Session timed out.")
                active_sessions.pop(interaction.user.id, None)
                return

            if confirm.content.strip().lower() != "yes":
                await dm.send("❌ Application cancelled. Run `/apply` again to start over.")
                active_sessions.pop(interaction.user.id, None)
                return

            # Post to applications channel
            channel_id = config.get("application_channel_id")
            if not channel_id:
                await dm.send("❌ Applications channel not configured. Contact an admin.")
                active_sessions.pop(interaction.user.id, None)
                return

            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                await dm.send("❌ Could not find the applications channel.")
                active_sessions.pop(interaction.user.id, None)
                return

            msg = await channel.send(embed=preview_embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            await dm.send(f"🎉 Your **{chosen_class}** application has been submitted! Good luck!")

        except Exception as e:
            print(f"[Applications] Error: {e}")
            try:
                await dm.send("❌ Something went wrong. Please try again.")
            except Exception:
                pass
        finally:
            active_sessions.pop(interaction.user.id, None)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not isinstance(message.channel, discord.DMChannel):
            return
        if message.author.id not in active_sessions:
            return
        if message.content.strip().lower() == "cancel":
            active_sessions.pop(message.author.id, None)
            await message.channel.send("❌ Application cancelled.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Applications(bot))
