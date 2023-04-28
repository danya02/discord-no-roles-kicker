import discord
from database import *
from discord import app_commands

class AreYouSureSetup(discord.ui.Modal, title="Are you sure?"):
    label = discord.ui.TextInput(label="Warning", default="If you submit this, this server's current config will be lost!")

    async def on_submit(self, interaction: discord.Interaction):
        with db.atomic():
            # Delete the guild's config, if any
            maybe_config = GuildConfig.get_or_none(GuildConfig.guild_id == interaction.guild_id)
            if maybe_config:
                maybe_config.delete_instance()
            # create new empty config
            GuildConfig(
                guild_id=interaction.guild_id,
                system_message_channel_id=interaction.channel_id
            ).save()
        
        await interaction.response.send_message("Created new empty config for this server!")


@app_commands.guild_only()
async def setup(interaction: discord.Interaction):
    modal = AreYouSureSetup()
    # If there is no config, just run the setup
    if GuildConfig.get_or_none(guild_id = GuildConfig.guild_id) is None:
        await modal.on_submit(interaction)
    else:
        await interaction.response.send_modal(modal)


setup = app_commands.Command(
    name='setup',
    description='Create a new empty config for this server',
    callback=setup,
)
setup.default_permissions = discord.Permissions()
setup.default_permissions.administrator = True
