import discord
from . import show_rule
from . import setup
from . import channel

cmds = [show_rule.show_config, setup.setup, channel.syschannel, channel.pendingchannel]

def attach(tree: discord.app_commands.CommandTree):
    for cmd in cmds:
        tree.add_command(cmd)