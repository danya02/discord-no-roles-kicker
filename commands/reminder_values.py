from typing import Optional
import discord
from discord.interactions import Interaction
from database import *
from discord import app_commands
import humanize
import datetime as dt

@app_commands.guild_only()
async def pendingreminders(interaction: discord.Interaction, intervals: str):
    """Set the thresholds for kick reminders."""
    guild_id = interaction.guild_id
    try:
        config = GuildConfig.get(GuildConfig.guild_id == guild_id)
    except pw.DoesNotExist:
        await interaction.response.send_message("No config found for the current server. Run `/setup` to perform initial setup.")
        return

    try:
        intervals = list(map(int, intervals.split()))
        for i in intervals:
            if i < 0:
                raise Exception
    except:
        await interaction.response.send_message("The argument must be a sequence of positive numbers of seconds", ephemeral=True)
        return

    intervals_str = ' '.join(map(str, intervals))
    msg = f'Old intervals (for reference): "{config.pending_kick_notification_values}"\n'
    msg += f'New intervals: "{intervals_str}"\n'
    humanized = []
    for i in intervals:
        humanized.append(humanize.precisedelta(dt.timedelta(seconds=i)))
    msg += f'Parsed: {"; ".join(humanized)}'
    config.pending_kick_notification_values = intervals_str
    config.save()
    await interaction.response.send_message(msg)


pendingreminders = app_commands.Command(
    name="pendingreminders",
    description="Set the thresholds for kick reminders",
    callback=pendingreminders
)
pendingreminders.default_permissions = discord.Permissions()
pendingreminders.default_permissions.kick_members = True
