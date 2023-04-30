import discord
from database import *
import datetime as dt
import time

async def on_member_join(client: discord.Client, member: discord.Member):
    # Get the guild config. If none, ignore
    guild_id = member.guild.id
    try:
        config = GuildConfig.get(GuildConfig.guild_id == guild_id)
    except pw.DoesNotExist:
        return

    # If there is no new member kick timeout configured, ignore
    if config.new_member_kick_timeout is None:
        return

    guild = client.get_guild(config.guild_id)
    syschan = guild.get_channel(config.system_message_channel_id)

    k = ScheduledKick(
        user_id=member.id,
        guild_id=guild.id,
        kick_after=time.time() + config.new_member_kick_timeout,
        unless_has_role_id=config.immunity_role_id,
    )
    k.save()
    msg = f"Created new pending kick ID: {k.id} for {member} {member.mention} (ID: {member.id}).\n"
    msg += f"Member will be kicked after {dt.datetime.fromtimestamp(k.kick_after).ctime()} (UTC time)\n"
    if k.unless_has_role_id:
        msg += f"Member will not be kicked if they have role <@&{k.unless_has_role_id}>\n"
    msg += "Review pending kicks with `/kicks...`, or cancel kicks with `/cancel`."
    await syschan.send(msg, allowed_mentions=discord.AllowedMentions.none())


async def on_raw_member_remove(client: discord.Client, payload: discord.RawMemberRemoveEvent):
    # Check whether the leaving member had any pending kicks. If so, say that.

    guild_id = payload.guild_id
    try:
        config = GuildConfig.get(GuildConfig.guild_id == guild_id)
    except pw.DoesNotExist:
        return

    guild = client.get_guild(config.guild_id)
    syschan = guild.get_channel(config.system_message_channel_id)

    for k in ScheduledKick.select()\
        .where(ScheduledKick.guild_id == guild_id)\
        .where(ScheduledKick.user_id == payload.user.id)\
        .where(ScheduledKick.is_active == True):
        k.is_active = False
        k.save()
        await syschan.send(f"Pending kick ID: {k.id} cancelled because the member it concerned, {payload.user} {payload.user.mention} (ID: {payload.user.id}), was removed.", allowed_mentions=discord.AllowedMentions.none())


async def on_member_update(client: discord.Client, before: discord.Member, after: discord.Member):
    # If member gained role, remove all pending kicks that would depend on that role.
    # If member lost immunity role, add a scheduled kick
    
    guild_id = before.guild.id
    try:
        config = GuildConfig.get(GuildConfig.guild_id == guild_id)
    except pw.DoesNotExist:
        return

    guild = client.get_guild(config.guild_id)
    syschan = guild.get_channel(config.system_message_channel_id)

    added_roles = []
    removed_roles = []
    for old_role in before.roles:
        if old_role not in after.roles:
            removed_roles.append(old_role)
    
    for new_role in after.roles:
        if new_role not in before.roles:
            added_roles.append(new_role)
    
    # If gained a role, check for kicks that depend on it
    for role in added_roles:
        for k in ScheduledKick.select()\
            .where(ScheduledKick.guild_id == before.guild.id)\
            .where(ScheduledKick.user_id == before.id)\
            .where(ScheduledKick.unless_has_role_id == role.id):
            k.is_active = False
            k.save()
        await syschan.send(f"Pending kick ID: {k.id} cancelled because the member it concerned, {before.user} {before.user.mention} (ID: {before.user.id}), gained role <@&{role.id}>.", allowed_mentions=discord.AllowedMentions.none())

    # If removed a role, check if it is the immunity role
    # (but only if loss_of_immunity_role_timeout is set)
    if config.loss_of_immunity_role_timeout:
        for role in removed_roles:
            if role.id == config.immunity_role_id:
                k = ScheduledKick(
                    guild_id=after.guild.id,
                    user_id=after.id,
                    kick_after=time.time() + config.loss_of_immunity_role_timeout,
                    unless_has_role_id=config.immunity_role_id
                )
                k.save()
                msg = f"Created new pending kick ID: {k.id} for {after} {after.mention} (ID: {after.id}).\n"
                msg += f"Member will be kicked after {dt.datetime.fromtimestamp(k.kick_after).ctime()} (UTC time)\n"
                if k.unless_has_role_id:
                    msg += f"Member will not be kicked if they have role <@&{k.unless_has_role_id}>\n"
                msg += "Review pending kicks with `/kicks...`, or cancel kicks with `/cancel`."
                await syschan.send(msg, allowed_mentions=discord.AllowedMentions.none())