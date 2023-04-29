from typing import Optional
import discord
from database import *
from discord import app_commands
import humanize
import datetime as dt

@app_commands.guild_only()
async def syschannel(interaction: discord.Interaction, channel: discord.TextChannel):
    """Set the system message channel."""
    guild_id = interaction.guild_id
    try:
        config = GuildConfig.get(GuildConfig.guild_id == guild_id)
    except pw.DoesNotExist:
        await interaction.response.send_message("No config found for the current server. Run `/setup` to perform initial setup.")
        return

    if channel.type != discord.ChannelType.text:
        await interaction.response.send_message(f"Channel <#{channel.id}> is not a text channel", ephemeral=True)
        return
    
    try:
        await channel.send("This will be the new system message channel.")
        config.system_message_channel_id = channel.id
        config.save()
        await interaction.response.send_message("System message channel updated")
    except Exception as e:
        await interaction.response.send_message(f"Error setting system message channel: {str(e)}", ephemeral=True)


syschannel = app_commands.Command(
    name="syschannel",
    description="Set the system message channel",
    callback=syschannel
)
syschannel.default_permissions = discord.Permissions()
syschannel.default_permissions.kick_members = True


@app_commands.guild_only()
async def pendingchannel(interaction: discord.Interaction, channel: Optional[discord.TextChannel]):
    """Set the channel for pending kicks, or empty to unset."""
    guild_id = interaction.guild_id
    try:
        config = GuildConfig.get(GuildConfig.guild_id == guild_id)
    except pw.DoesNotExist:
        await interaction.response.send_message("No config found for the current server. Run `/setup` to perform initial setup.")
        return

    
    try:
        if channel:
            if channel.type != discord.ChannelType.text:
                await interaction.response.send_message(f"Channel <#{channel.id}> is not a text channel", ephemeral=True)
                return
            await channel.send("This will be the new pending channel.")
            config.pending_kick_notification_channel_id = channel.id
            config.save()

            await interaction.response.send_message("Pending channel set")
        else:
            config.pending_kick_notification_channel_id = None
            config.save()
            await interaction.response.send_message("Pending channel unset")

            
    except Exception as e:
        await interaction.response.send_message(f"Error setting pending channel: {str(e)}", ephemeral=True)

pendingchannel = app_commands.Command(
    name="pendingchannel",
    description="Set the channel for pending kicks, or empty to unset",
    callback=pendingchannel
)
pendingchannel.default_permissions = discord.Permissions()
pendingchannel.default_permissions.kick_members = True
