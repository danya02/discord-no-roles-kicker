import discord
from . import show_rule

cmds = [show_rule.show_config]

def attach(tree: discord.app_commands.CommandTree):
    for cmd in cmds:
        name = discord.utils.MISSING
        description = discord.utils.MISSING
        try:
            name = cmd.name
        except AttributeError: pass
        try:
            description = cmd.description
        except AttributeError: pass
        tree.command(name=name, description=description)(cmd)