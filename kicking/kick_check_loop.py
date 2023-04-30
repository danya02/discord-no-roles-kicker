from database import *
from . import execute_kick
import datetime as dt

async def check_for_pending_kicks(client):
    for kick in ScheduledKick.select()\
            .where(ScheduledKick.is_active == True)\
                .where(dt.datetime.now().timestamp() > ScheduledKick.kick_after):
        await execute_kick.start_kick(client, kick)  # safe to call many times with same kick