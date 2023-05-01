from typing import Optional
import discord
from database import *
from discord import app_commands
import humanize
import datetime as dt

@app_commands.guild_only()
async def immunityrole(interaction: discord.Interaction, role: Optional[discord.Role]):
    """Set the kick immunity role, or empty to unset."""
    guild_id = interaction.guild_id
    try:
        config = GuildConfig.get(GuildConfig.guild_id == guild_id)
    except pw.DoesNotExist:
        await interaction.response.send_message("No config found for the current server. Run `/setup` to perform initial setup.")
        return

    if role:
        config.immunity_role_id = role.id
        config.save()
        await interaction.response.send_message(f"Kick immunity role is now set to {role.mention}")
        return
    else:
        config.immunity_role_id = None
        config.save()
        await interaction.response.send_message(f"Kick immunity role is now removed")
        return




immunityrole = app_commands.Command(
    name="immunityrole",
    description="Set the kick immunity role, or empty to unset",
    callback=immunityrole
)
immunityrole.default_permissions = discord.Permissions()
immunityrole.default_permissions.kick_members = True
