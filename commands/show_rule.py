import discord
from database import *
from discord import app_commands
import humanize
import datetime as dt

@app_commands.guild_only()
async def show_config(interaction: discord.Interaction):
    """Display the current configuration of this server."""
    guild_id = interaction.guild_id
    try:
        config = GuildConfig.get(GuildConfig.guild_id == guild_id)
    except pw.DoesNotExist:
        await interaction.response.send_message("No config found for the current server. Run `/setup` to perform initial setup.")
        return

    text = 'Current server config:\n'
    text += f"System message channel: <#{config.system_message_channel_id}> `/syschannel`\n"

    if config.pending_kick_notification_channel_id:
        text += f"Will send reminders about pending kicks in: <#{config.pending_kick_notification_channel_id}> `/pendingchannel`\n"
    else:
        text += f"Will send reminders about pending kicks in: unset `/pendingchannel`\n"

    text += f'When the time until kick passes these thresholds, send a reminder: "{config.pending_kick_notification_values}" `/pendingreminders`\n'

    if config.new_member_kick_timeout:
        h = humanize.precisedelta(dt.timedelta(seconds=config.new_member_kick_timeout))
        text += f'New members get kicked after: {h} = {config.new_member_kick_timeout} seconds `/newtimeout`\n'
    else:
        text += 'New members get kicked after: never `/newtimeout`\n'

    if config.immunity_role_id:
        text += f'Kick immunity role: <@&{config.immunity_role_id}> `/immunityrole`\n'
    else:
        text += 'Kick immunity role: unset `/immunityrole`\n'
    
    if config.loss_of_immunity_role_timeout:
        h = humanize.precisedelta(dt.timedelta(seconds=config.loss_of_immunity_role_timeout))
        text += f'Members losing immunity role get kicked after: {h} = {config.loss_of_immunity_role_timeout} seconds `/immunitytimeout`\n'
    else:
        text += 'Members losing immunity role get kicked after: never `/immunitytimeout`\n'

    h = humanize.precisedelta(dt.timedelta(seconds=config.kick_safety_timeout))
    text += f'When kicking a member, allow cancelling within: {h} = {config.kick_safety_timeout} seconds `/safetytimeout`\n'

    text += 'To reset these settings to safe defaults, perform `/setup` again.'
    interaction.response.send_message(text)


show_config.name = 'showconfig'
show_config.description = discord.utils.MISSING