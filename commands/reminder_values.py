from typing import Optional
import discord
from discord.interactions import Interaction
from database import *
from discord import app_commands
import humanize
import datetime as dt

from kicking.reminders import KICK_MSG_AVAILABLE_REPLACEMENTS, KICK_MSG_TEXT_DEFAULT, get_kick_msg_text

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


class PendingKickMsgSet(discord.ui.Modal, title="Kick reminder message"):
    label = discord.ui.TextInput(label="What will happen", style=discord.TextStyle.paragraph)
    label2 = discord.ui.TextInput(label="Available placeholders")
    msg = discord.ui.TextInput(label="Reminder message", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: Interaction):
        guild_id = interaction.guild_id
        try:
            config = GuildConfig.get(GuildConfig.guild_id == guild_id)
        except pw.DoesNotExist:
            await interaction.response.send_message("No config found for the current server. Run `/setup` to perform initial setup.")
            return

        config.pending_kick_notification_msg = self.msg.value.strip() or None
        config.save()

        test_kick = ScheduledKick()
        test_kick.user_id = interaction.user.id
        test_kick.kick_after = dt.datetime.now() + dt.timedelta(days=1337, seconds=420)

        test_msg = get_kick_msg_text(test_kick, config)

        response = f"Your new message was set. Here is what a kick reminder would look like:\n\n{test_msg}"
        await interaction.response.send_message(response)


@app_commands.guild_only()
async def pendingmsg(interaction: discord.Interaction):
    """Set the kick reminder custom message."""
    guild_id = interaction.guild_id
    try:
        config = GuildConfig.get(GuildConfig.guild_id == guild_id)
    except pw.DoesNotExist:
        await interaction.response.send_message("No config found for the current server. Run `/setup` to perform initial setup.")
        return

    modal = PendingKickMsgSet()
    modal.label.default = "You are about to change the message that gets sent to remind members of pending kicks. Use the provided placeholders to show where to put information. Empty to reset to default message. Afterwards, an example reminder will be shown."
    modal.label2.default = "; ".join(['{'+i+'}' for i in  KICK_MSG_AVAILABLE_REPLACEMENTS])
    modal.msg.default = config.pending_kick_notification_msg or KICK_MSG_TEXT_DEFAULT
    await interaction.response.send_modal(modal)

pendingmsg = app_commands.Command(
    name="pendingmsg",
    description="Set the kick reminder custom message",
    callback=pendingmsg
)
pendingmsg.default_permissions = discord.Permissions()
pendingmsg.default_permissions.kick_members = True
