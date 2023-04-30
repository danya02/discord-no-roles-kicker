from typing import Optional
import discord
from discord.interactions import Interaction
from database import *
from discord import app_commands
import humanize
import datetime as dt

@app_commands.guild_only()
async def cancel(interaction: discord.Interaction, kick_id: int):
    guild_id = interaction.guild_id
    try:
        config = GuildConfig.get(GuildConfig.guild_id == guild_id)
    except pw.DoesNotExist:
        await interaction.response.send_message("No config found for the current server. Run `/setup` to perform initial setup.")
        return
    
    kick = ScheduledKick.select().where(ScheduledKick.id == kick_id)\
        .where(ScheduledKick.guild_id == guild_id)\
        .get_or_none()
    if not kick:
        await interaction.response.send_message(f"Could not find pending kick with ID: {kick_id}. It might not exist or belong to a different server.", ephemeral=True)
        return

    if kick.is_active == False:
        await interaction.response.send_message(f"Kick ID: {kick_id} is not scheduled. It might be already executed or cancelled.", ephemeral=True)
        return
    kick.is_active = False
    kick.save()
    await interaction.response.send_message(f"Kick ID: {kick_id} successfully cancelled. Review pending kicks with `/kicks`.")




cancel = app_commands.Command(
    name="cancel",
    description="Cancel a pending kick by its ID",
    callback=cancel
)
cancel.default_permissions = discord.Permissions()
cancel.default_permissions.kick_members = True
