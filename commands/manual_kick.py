from typing import Optional
import discord
from discord.interactions import Interaction
from database import *
from discord import app_commands
import humanize
import datetime as dt

class ManualKickTimeoutSet(discord.ui.Modal, title="When to kick?"):
    label = discord.ui.TextInput(label="What will happen", style=discord.TextStyle.paragraph)
    when_to_kick = discord.ui.TextInput(label="Seconds until kick")

    async def on_submit(self, interaction: Interaction):
        try:
            timeout = int(self.when_to_kick.value)
            if timeout < 0: raise Exception
        except:
            await interaction.response.send_message("The value of \"Seconds until kick\" must be a non-negative integer", ephemeral=True)
        
        k = ScheduledKick(
            guild_id=interaction.guild_id,
            user_id = self.member.id,
            kick_after = dt.datetime.now() + dt.timedelta(seconds=timeout),
            unless_has_role_id=self.config.immunity_role_id
        )

        k.save()
        
        # TODO: find way to send message to system channel?

        response = f"Successfully added a pending kick for member {self.member.mention}."
        td = dt.timedelta(seconds=timeout)
        response += f' It will happen in {timeout} seconds = {humanize.precisedelta(td)} from now, or after {(dt.datetime.now() + td).ctime()} (UTC time).'
        if k.unless_has_role_id:
            response += f' It will not happen if the member has role <@&{k.unless_has_role_id}>.'
        await interaction.response.send_message(response, ephemeral=True)



@app_commands.guild_only()
async def add_manual_kick(interaction: discord.Interaction, member: discord.Member):
    guild_id = interaction.guild_id
    try:
        config = GuildConfig.get(GuildConfig.guild_id == guild_id)
    except pw.DoesNotExist:
        await interaction.response.send_message("No config found for the current server. Run `/setup` to perform initial setup.")
        return

    modal = ManualKickTimeoutSet()
    # Use the shortest of the timeouts
    timeout = float('inf')
    if config.loss_of_immunity_role_timeout is not None and config.loss_of_immunity_role_timeout < timeout:
        timeout = config.loss_of_immunity_role_timeout
        with_what = 'the immunity loss timeout.'
    if config.new_member_kick_timeout is not None and config.new_member_kick_timeout < timeout:
        timeout = config.new_member_kick_timeout
        with_what = 'the new member kick timeout.'
    if timeout == float('inf'):
        timeout = 86400
        with_what = 'a duration of 1 day.'
    modal.label.default = f"You are about to schedule a kick for {member}. The time to kick has been prefilled with " + with_what
    modal.when_to_kick.default = timeout
    modal.member = member
    modal.config = config
    await interaction.response.send_modal(modal)



add_manual_kick = app_commands.ContextMenu(
    name="Add Manual Kick",
    callback=add_manual_kick
)
add_manual_kick.default_permissions = discord.Permissions()
add_manual_kick.default_permissions.kick_members = True
