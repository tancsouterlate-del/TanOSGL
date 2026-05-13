import discord
from discord.ext import commands
import config


class Suggestions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        suggestions_id = config.get("suggestions_channel_id")
        if not suggestions_id:
            return
        if message.channel.id != int(suggestions_id):
            return

        for emoji in ["✅", "❌", "🟡"]:
            try:
                await message.add_reaction(emoji)
            except discord.HTTPException:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Suggestions(bot))
