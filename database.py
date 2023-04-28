import peewee as pw
import logging
log = logging.getLogger(__name__)


db = pw.SqliteDatabase("/database.db")

def create_table(cls):
    log.debug("Creating table for", cls)
    db.create_tables([cls])
    return cls

class MyModel(pw.Model):
    class Meta:
        database = db

@create_table
class GuildConfig(MyModel):
    guild_id = pw.BigIntegerField(unique=True)
    new_member_kick_timeout = pw.IntegerField(null=True)
    immunity_role_id = pw.BigIntegerField(null=True)
    loss_of_immunity_role_timeout = pw.IntegerField(null=True)
    system_message_channel_id = pw.BigIntegerField()
    pending_kick_notification_channel_id = pw.BigIntegerField(null=True)
    pending_kick_notification_values = pw.TextField(default='3600 7200 21600 43200 86400 259200 604800 1209600')
    kick_safety_timeout = pw.IntegerField(default=15*60)


@create_table
class ScheduledKick(MyModel):
    is_active = pw.BooleanField(default=True, index=True)
    was_executed = pw.BooleanField(index=True, default=False)

    user_id = pw.BigIntegerField()
    guild_id = pw.BigIntegerField()
    kick_after = pw.DateTimeField(index=True)
    unless_has_role_id = pw.BigIntegerField(null=True, index=True)