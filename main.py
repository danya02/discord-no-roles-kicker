import discord
from discord import app_commands
from discord.ext import tasks
import os
import logging
import kicking
import peewee as pw
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
        self.check_for_pending_kicks.add_exception_type(pw.PeeweeException)
        self.run_reminders.add_exception_type(pw.PeeweeException)

    async def setup_hook(self):
        commands.attach(self.tree)
        if GUILD:
            self.tree.copy_global_to(guild=GUILD)
            await self.tree.sync(guild=GUILD)
        await self.tree.sync()
        self.check_for_pending_kicks.start()
        self.run_reminders.start()

    
    @tasks.loop(seconds=30)
    async def check_for_pending_kicks(self):
        await kicking.kick_check_loop.check_for_pending_kicks(self)

    @tasks.loop(seconds=29.5)  # slight offset to allow drift, so that database load isn't all at the same time
    async def run_reminders(self):
        await kicking.reminders.run_reminders(self)

client = MyClient()

@client.event
async def on_ready():
    log.info(f'Logged in as {client.user} (ID: {client.user.id})')


@client.event
async def on_member_join(member):
    await kicking.scheduling.on_member_join(client, member)

@client.event
async def on_raw_member_remove(payload):
    await kicking.scheduling.on_raw_member_remove(client, payload)

@client.event
async def on_member_update(before, after):
    await kicking.scheduling.on_member_update(client, before, after)


@client.tree.command()
async def hello(interaction: discord.Interaction):
    """Says hello!"""
    await interaction.response.send_message(f'Hi, {interaction.user.mention}')

def main():
    discord.utils.setup_logging(level=logging.DEBUG)
    client.run(os.getenv("DISCORD_TOKEN"), log_handler=None)

if __name__ == '__main__':
    main()