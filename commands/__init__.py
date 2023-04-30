import discord
from . import show_rule
from . import setup
from . import channel
from . import timeout
from . import manual_kick

cmds = [
    show_rule.show_config,
    setup.setup,
    channel.syschannel, channel.pendingchannel,
    timeout.newtimeout, timeout.immunitytimeout, timeout.safetytimeout,
    manual_kick.add_manual_kick,
    ]

def attach(tree: discord.app_commands.CommandTree):
    for cmd in cmds:
        tree.add_command(cmd)