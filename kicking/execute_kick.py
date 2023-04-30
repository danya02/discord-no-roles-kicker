from database import *
import asyncio
import discord
import logging
import datetime as dt
import humanize
log = logging.getLogger(__name__)

RUNNING_KICKS_LOCK = asyncio.Lock()
RUNNING_KICKS = []

async def start_kick(client: discord.Client, kick: ScheduledKick):
    log.debug(f"Trying to start kick {kick}")
    async with RUNNING_KICKS_LOCK:
        # Remove all tasks that have finished.
        to_delete = []
        for kick_task in RUNNING_KICKS:
            if kick_task.done():
                to_delete.append(kick_task)
        
        for d in to_delete:
            RUNNING_KICKS.remove(d)

        # Check if there is a running kick already
        # If there is, return immediately
        for kick_task in RUNNING_KICKS:
            if kick_task.get_name().endswith('-' + str(kick.id)):
                return


        # Now that we know that there is no currently running kick,
        # start one.
        log.info(f"Starting task for kick {kick}")
        task = asyncio.create_task(run_kick(client, kick))
        task.set_name(f"RunningKick-{kick.id}")
        RUNNING_KICKS.append(task)


async def run_kick(client: discord.Client, kick: ScheduledKick):
    # Retreive the guild's configuration, error out if none.
    guild_id = kick.guild_id
    try:
        config = GuildConfig.get(GuildConfig.guild_id == guild_id)
    except pw.DoesNotExist:
        log.error(f"Tried to execute kick {kick} but didn't have config for guild {kick.guild_id}?!")
        kick.is_active = False
        kick.save()
    
    guild = client.get_guild(config.guild_id)
    syschan = guild.get_channel(config.system_message_channel_id)
    
    try:
        member = await guild.fetch_member(kick.user_id)  # fetch for newest info
    except discord.NotFound:
        await syschan.send(f"Tried to initiate kick of <@{kick.user_id}> (ID: {kick.user_id}) but there appears to be no such member in this server.")
        kick.is_active = False
        kick.save()
        return


    time_started = dt.datetime.now()
    safety_timeout = dt.timedelta(seconds=config.kick_safety_timeout)
    final_time = time_started + safety_timeout

    def make_message():
        time_remaining = final_time - dt.datetime.now()
        time_remaining = dt.timedelta(seconds=int(time_remaining.total_seconds()))
        fraction_remaining = time_remaining.total_seconds() / safety_timeout.total_seconds()
        fraction_done = 1 - fraction_remaining

        progress_bar = ''
        STEPS = 20
        for i in range(STEPS):
            frac = i / STEPS
            if frac < fraction_done:
                progress_bar += '⚠️' # WARNING SIGN
            else:
                progress_bar += '⬜' # WHITE LARGE SQUARE
        
        msg = f"Currently kicking: {member} {member.mention}\n"
        msg += f"Kick will happen in: {int(time_remaining.total_seconds())} seconds = {humanize.precisedelta(time_remaining)}\n"
        if kick.unless_has_role_id:
            msg += f"Cancel this kick by giving the member the role <@&{kick.unless_has_role_id}>, or clicking the reaction button on this message.\n"
        else:
            msg += "Cancel this kick by clicking the reaction button on this message.\n"
        
        msg += progress_bar

        return msg


    # Initial message
    msg = await syschan.send(make_message())

    # Add a reaction to the message
    await msg.add_reaction('🚫') # NO ENTRY SIGN

    while dt.datetime.now() < final_time:
        # Loop until the final time has passed
        try:
            reaction, user = await client.wait_for('reaction_add', timeout=30, check=lambda reaction, user: reaction.message == msg)
            if user.guild_permissions.kick_members:
                # Cancel the kick
                kick.is_active = False
                kick.save()
                await msg.edit(content=f"Pending kick for {member} {member.mention} was cancelled by {user} via reaction")
                return
            else:
                await syschan.send(f"Sorry {user.mention}, you cannot cancel the pending kick because you do not have permission to \"Kick Members\" in this server.", delete_after=10)
        except asyncio.TimeoutError:
            pass
        
        await msg.edit(content=make_message())

        # If there is an immunity role provided for the kick, check if the member has gained it.
        if kick.unless_has_role_id:
            try:
                member = await guild.fetch_member(kick.user_id)  # fetch for newest info
            except discord.NotFound:
                await msg.edit(content=f"While kicking {member} <@{kick.user_id}> (ID: {kick.user_id}), they seem to have disappeared.")
                kick.is_active = False
                kick.save()
                return
            
            for role in member.roles:
                if role.id == kick.unless_has_role_id:
                    kick.is_active = False
                    kick.save()
                    await msg.edit(content=f"Pending kick for {member} {member.mention} was cancelled because they gained role <@&{role.id}>")
                    return

    # Timeout expired: time for final check and kick
    try:
        member = await guild.fetch_member(kick.user_id)  # fetch for newest info
    except discord.NotFound:
        await msg.edit(content=f"While kicking {member} <@{kick.user_id}> (ID: {kick.user_id}), they seem to have disappeared.")
        kick.is_active = False
        kick.save()
        return
    
    for role in member.roles:
        if role.id == kick.unless_has_role_id:
            kick.is_active = False
            kick.save()
            await msg.edit(content=f"Pending kick for {member} {member.mention} was cancelled because they gained role <@&{role.id}>")
            return

    # Clear to kick
    await member.kick(reason=f"Pending kick ID={kick.id} expired")
    await msg.edit(content=f"Kick for {member} {member.mention} (ID: {kick.user_id}) executed successfully.")
    kick.is_active = False
    kick.was_executed = True
    kick.save()