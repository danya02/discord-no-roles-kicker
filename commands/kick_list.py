from typing import Optional
import discord
from discord.interactions import Interaction
from database import *
from discord import app_commands
import humanize
import datetime as dt

kicks = app_commands.Group(
    name="kicks",
    description="View this server's kicks",
    guild_only=True,
)
kicks.default_permissions = discord.Permissions()
kicks.default_permissions.kick_members = True

def pretty_print_kick(kick: ScheduledKick) -> str:
    msg = ''
    # First, an emoji representing its state
    if kick.is_active:
        msg += '⏳'  # HOURGLASS WITH FLOWING SAND
    elif kick.was_executed:
        msg += '✅'  # WHITE HEAVY CHECK MARK
    else: # not active, but also not executed
        msg += '🚫'  # NO ENTRY SIGN
    
    msg += f' ID: {kick.id} '
    delta = dt.datetime.now() - dt.datetime.fromtimestamp(kick.kick_after)
    humandelta = humanize.precisedelta(delta)
    msg += f'Kick member <@{kick.user_id}> after {dt.datetime.fromtimestamp(kick.kick_after).ctime()} (UTC time), which is {humandelta} from now'
    if kick.unless_has_role_id:
        msg += f', unless member had role <@&{kick.unless_has_role_id}>'

    if kick.is_active:
        msg += ' (pending)'
    elif kick.was_executed:
        msg += ' (completed)'
    else: # not active, but also not executed
        msg += ' (cancelled)'

    return msg

PER_PAGE=5

class KickPaginatorView(discord.ui.View):
    def __init__(self, *, timeout = 180, currently_shown, selector):
        super().__init__(timeout=timeout)
        self.currently_shown = currently_shown
        self.selector = selector


    @discord.ui.button(label="Earlier", emoji='⬅️')
    async def show_earlier(self, interaction: discord.Interaction, btn: discord.Button):
        # Find a new set of items that are earlier than the currently shown one
        earliest = self.currently_shown[0].id
        new_entries = list(self.selector.where(ScheduledKick.id < earliest).order_by(-ScheduledKick.id).limit(PER_PAGE))
        new_entries.sort(key=lambda x: x.id)
        text = '\n'.join(map(pretty_print_kick, new_entries))

        # Check whether the two buttons need to be active
        exists_earlier = self.selector.where(ScheduledKick.id < new_entries[0]).get_or_none() is not None
        exists_later = self.selector.where(ScheduledKick.id > new_entries[-1]).get_or_none() is not None
        self.show_earlier.disabled = not exists_earlier
        self.show_later.disabled = not exists_later
        self.currently_shown = new_entries

        await interaction.response.edit_message(content=text, view=self)

    @discord.ui.button(label="Later", emoji='➡️')
    async def show_later(self, interaction: discord.Interaction, btn: discord.Button):
        # Find a new set of items that are later than the currently shown one
        latest = self.currently_shown[-1].id
        new_entries = list(self.selector.where(ScheduledKick.id > latest).order_by(ScheduledKick.id).limit(PER_PAGE))
        new_entries.sort(key=lambda x: x.id)
        text = '\n'.join(map(pretty_print_kick, new_entries))

        # Check whether the two buttons need to be active
        exists_earlier = self.selector.where(ScheduledKick.id < new_entries[0]).get_or_none() is not None
        exists_later = self.selector.where(ScheduledKick.id > new_entries[-1]).get_or_none() is not None
        self.show_earlier.disabled = not exists_earlier
        self.show_later.disabled = not exists_later
        self.currently_shown = new_entries

        await interaction.response.edit_message(content=text, view=self)

def show_kicks(name, description, selector):
    async def perform_show(interaction: discord.Interaction):
        guild_id = interaction.guild_id
        try:
            config = GuildConfig.get(GuildConfig.guild_id == guild_id)
        except pw.DoesNotExist:
            await interaction.response.send_message("No config found for the current server. Run `/setup` to perform initial setup.")
            return

        # Get initial contents of message, which should be the latest entries
        my_selector = selector.where(ScheduledKick.guild_id == guild_id)
        latest_entries = list(my_selector.order_by(-ScheduledKick.id).limit(PER_PAGE))
        latest_entries.sort(key=lambda x: x.id)
        text = '\n'.join(map(pretty_print_kick, latest_entries))

        if not latest_entries:
            await interaction.response.send_message("No kicks in this server yet...", ephemeral=True)
            return
        
        # Construct view, set button's active state
        view = KickPaginatorView(currently_shown=latest_entries, selector=my_selector)
        view.show_later.disabled = True  # because at end
        exists_earlier = my_selector.where(ScheduledKick.id < latest_entries[0].id).get_or_none() is not None
        view.show_earlier.disabled = not exists_earlier

        await interaction.response.send_message(text, view=view)

    # Make command out of coro
    cmd = app_commands.Command(
        name=name,
        description=description,
        callback=perform_show
    )
    cmd.default_permissions = discord.Permissions()
    cmd.default_permissions.kick_members = True
    
    return cmd

pending_kicks = show_kicks("kickspending", "Show kicks that are pending", ScheduledKick.select().where(ScheduledKick.is_active == True))
all_kicks = show_kicks("kicksall", "Show all kicks, including ones that were cancelled", ScheduledKick.select())
