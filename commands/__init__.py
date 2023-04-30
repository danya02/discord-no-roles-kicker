import discord
from . import show_rule
from . import setup
from . import channel
from . import timeout
from . import manual_kick
from . import reminder_values
from . import cancel
from . import kick_list

cmds = [
    show_rule.show_config,
    setup.setup,
    channel.syschannel, channel.pendingchannel,
    timeout.newtimeout, timeout.immunitytimeout, timeout.safetytimeout,
    manual_kick.add_manual_kick,
    reminder_values.pendingreminders,
    cancel.cancel,
    kick_list.all_kicks, kick_list.pending_kicks,
    ]

def attach(tree: discord.app_commands.CommandTree):
    for cmd in cmds:
        tree.add_command(cmd)