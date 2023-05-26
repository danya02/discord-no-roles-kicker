from database import *
import discord
import datetime as dt
import logging
import humanize
log = logging.getLogger(__name__)

KICK_MSG_TEXT_DEFAULT = "{who} will be kicked in {when}. Please contact a server moderator for more information."
KICK_MSG_AVAILABLE_REPLACEMENTS = ['who', 'when']

def get_kick_msg_text(kick: ScheduledKick, gconf: GuildConfig) -> str:
    seconds_remaining = int((dt.datetime.now() - dt.datetime.fromtimestamp(kick.kick_after)).total_seconds())
    if not gconf.pending_kick_notification_msg:
        gconf.pending_kick_notification_msg = KICK_MSG_TEXT_DEFAULT
        # Deliberately do not save this.
    return gconf.pending_kick_notification_msg\
        .replace("{who}", f"<@{kick.user_id}>")\
        .replace("{when}", humanize.naturaldelta(seconds_remaining, minimum_unit='seconds'))


async def run_reminders(client: discord.Client):
    # Run only for guilds that have a reminder channel set.
    # In those, select kicks that are active.
    # It is expected that there will not be many such kicks,
    # and that selecting them would be quick.

    for kick in ScheduledKick.select(ScheduledKick, GuildConfig)\
        .where(ScheduledKick.is_active == True)\
        .join(GuildConfig, on=(ScheduledKick.guild_id == GuildConfig.guild_id), attr='gconf')\
        .where(GuildConfig.pending_kick_notification_channel_id.is_null(False)):
        gconf = kick.gconf
        # Get the channel (which might not exist), and the system notification channel (which must exist)
        syschan = gconf.system_message_channel_id
        syschan = client.get_channel(syschan)
        if syschan is None:
            log.error(f"Could not retrieve system channel for config {gconf}")
            continue

        notifychan = client.get_partial_messageable(gconf.pending_kick_notification_channel_id)


        # Now check whether we need to send the reminder.
        seconds_remaining = int((dt.datetime.now() - dt.datetime.fromtimestamp(kick.kick_after)).total_seconds())
        smallest_threshold_exceeded = float('inf')
        for threshold in map(int, gconf.pending_kick_notification_values.split()):
            if threshold > seconds_remaining:
                smallest_threshold_exceeded = threshold
        
        # If no thresholds have been hit, don't notify
        if smallest_threshold_exceeded == float('inf'): continue

        # If this threshold was already passed, don't notify
        if smallest_threshold_exceeded >= (kick.last_reminder_time or float('inf')): continue

        try:
            await notifychan.send(get_kick_msg_text(kick, gconf), allowed_mentions=discord.AllowedMentions(users=True, roles=False))
            kick.last_reminder_time = smallest_threshold_exceeded
            kick.save()
        except:
            try:
                await syschan.send(f"Failed to send a pending kick notification for kick ID: {kick.id}, concerning member <@{kick.user_id}> who will be kicked in {humanize.precisedelta(seconds_remaining)}. Please remind the member manually.")
                kick.last_reminder_time = smallest_threshold_exceeded
                kick.save()
            except:
                log.error(f"Could not send reminder into channel {notifychan.id}, and also the error message into channel {syschan.id}, about guild config {gconf.id}")
                continue