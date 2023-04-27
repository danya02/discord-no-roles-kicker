import discord
from discord import app_commands
import os
import database
import logging
log = logging.getLogger(__name__)

import commands

GUILD = int(os.getenv("DEV_GUILD") or 0)
if GUILD:
    GUILD = discord.Object(GUILD)

class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        commands.attach(self.tree)
        if GUILD:
            self.tree.copy_global_to(guild=GUILD)
            await self.tree.sync(guild=GUILD)
        await self.tree.sync()



client = MyClient()

@client.event
async def on_ready():
    log.info(f'Logged in as {client.user} (ID: {client.user.id})')


@client.tree.command()
async def hello(interaction: discord.Interaction):
    """Says hello!"""
    await interaction.response.send_message(f'Hi, {interaction.user.mention}')

def main():
    discord.utils.setup_logging()
    client.run(os.getenv("DISCORD_TOKEN"), log_handler=None)

if __name__ == '__main__':
    main()