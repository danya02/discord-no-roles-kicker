from typing import List, Optional
import discord
from database import *
from discord import app_commands
from discord.app_commands import Choice
import humanize
import datetime as dt

async def autocomplete_long_or_zero(interaction: discord.Interaction,
                            current: str) -> List[Choice[int]]:
    options = [
    Choice(name='unset', value=0),
    Choice(name='1 day', value=24*60*60),
    Choice(name='7 days', value=7*24*60*60),
    Choice(name='14 days', value=14*24*60*60),
    Choice(name='31 days', value=31*24*60*60),
    ]
    return [i for i in options if i.name.startswith(current)]

@app_commands.autocomplete(timeout=autocomplete_long_or_zero)
@app_commands.guild_only()
async def newtimeout(interaction: discord.Interaction, timeout: Optional[int]):
    """Set the kick timeout for new members, in seconds, or empty to unset."""
    guild_id = interaction.guild_id
    try:
        config = GuildConfig.get(GuildConfig.guild_id == guild_id)
    except pw.DoesNotExist:
        await interaction.response.send_message("No config found for the current server. Run `/setup` to perform initial setup.")
        return

    timeout = max(timeout or 0, 0)

    if not timeout:
        config.new_member_kick_timeout = None
        config.save()
        await interaction.response.send_message("New members will no longer be kicked")
    else:
        config.new_member_kick_timeout = timeout
        config.save()
        d = dt.timedelta(seconds=timeout)
        await interaction.response.send_message(f"New members will be kicked after {timeout} seconds = {humanize.precisedelta(d)} after joining.")

newtimeout = app_commands.Command(
    name="newtimeout",
    description="Set the kick timeout for new members, in seconds, or empty to unset",
    callback=newtimeout
)
newtimeout.default_permissions = discord.Permissions()
newtimeout.default_permissions.kick_members = True


@app_commands.autocomplete(timeout=autocomplete_long_or_zero)
@app_commands.guild_only()
async def immunitytimeout(interaction: discord.Interaction, timeout: Optional[int]):
    """Set the kick timeout for members losing immunity role, in seconds, or empty to unset."""
    guild_id = interaction.guild_id
    try:
        config = GuildConfig.get(GuildConfig.guild_id == guild_id)
    except pw.DoesNotExist:
        await interaction.response.send_message("No config found for the current server. Run `/setup` to perform initial setup.")
        return

    timeout = max(timeout or 0, 0)

    if not timeout:
        config.loss_of_immunity_role_timeout = None
        config.save()
        await interaction.response.send_message("Members losing immunity role will no longer be kicked")
    else:
        config.loss_of_immunity_role_timeout = timeout
        config.save()
        d = dt.timedelta(seconds=timeout)
        await interaction.response.send_message(f"Members will be kicked after {timeout} seconds = {humanize.precisedelta(d)} after losing the immunity role (which is <@&{config.immunity_role_id}>).")

immunitytimeout = app_commands.Command(
    name="immunitytimeout",
    description="Set the kick timeout for members losing immunity role, in seconds, or empty to unset",
    callback=immunitytimeout
)
immunitytimeout.default_permissions = discord.Permissions()
immunitytimeout.default_permissions.kick_members = True


async def autocomplete_short(interaction: discord.Interaction,
                            current: str) -> List[Choice[int]]:
    options = [
    Choice(name='10 minutes', value=10*60),
    Choice(name='30 minutes', value=30*60),
    Choice(name='1 hour', value=60*60),
    Choice(name='2 hours', value=2*60*60),
    ]
    return [i for i in options if i.name.startswith(current)]


@app_commands.autocomplete(timeout=autocomplete_short)
@app_commands.guild_only()
async def safetytimeout(interaction: discord.Interaction, timeout: Optional[int]):
    """Set the kick safety timeout, in seconds."""
    guild_id = interaction.guild_id
    try:
        config = GuildConfig.get(GuildConfig.guild_id == guild_id)
    except pw.DoesNotExist:
        await interaction.response.send_message("No config found for the current server. Run `/setup` to perform initial setup.")
        return

    timeout = max(timeout or 0, 0)

    if timeout < 10*60:
        await interaction.response.send_message("Cannot set safety timeout below 10 minutes!", ephemeral=True)
        return

    config.kick_safety_timeout = timeout
    config.save()
    d = dt.timedelta(seconds=timeout)
    await interaction.response.send_message(f"You will have {timeout} seconds = {humanize.precisedelta(d)} to cancel a kick in progress.")

safetytimeout = app_commands.Command(
    name="safetytimeout",
    description="Set the kick safety timeout, in seconds",
    callback=safetytimeout
)
safetytimeout.default_permissions = discord.Permissions()
safetytimeout.default_permissions.kick_members = True
