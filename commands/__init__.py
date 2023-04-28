import discord
from . import show_rule
from . import setup

cmds = [show_rule.show_config, setup.setup]

def attach(tree: discord.app_commands.CommandTree):
    for cmd in cmds:
        tree.add_command(cmd)