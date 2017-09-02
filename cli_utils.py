import re
import ast
from collections import OrderedDict

import config


# NOTE: This only works because we know this is a simulation running
# on mininet and are aware of each hosts' socket.

# BUG: This has no idea of how many nodes are actually running
def get_sock_from_name(name):
    num = re.findall(r'\d+', name)
    num = int(num[0])

    # TODO: Use some python ip module to get ip based on config.IP
    return (("10.0.0.%d" % (num + 1)), config.PORT)


# NOTE: Ideally, we should be using a better REPL module (like cmd.Cmd)

def generate_help_dict():
    # Get an Abstract Syntax Tree of the cli.py source file
    # I shall rot in seven hells for this sorcery
    with open('cli.py') as src_file:
        tree = ast.parse(src_file.read())

    # Our goal is to build a dictionary of commands and their help strings
    # In the order they are defined in the source
    commands = OrderedDict()

    # Let's have a walk down the tree
    for node in ast.walk(tree):

        # if comparisons that have 'cmd' on the left side of comparison
        if (isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == 'cmd'
            ):

            cmd_aliases = [Str.s for Str in node.test.comparators[0].elts]

            # The longest command is main - others are its aliases
            cmd = sorted(cmd_aliases, key=len)[-1]
            docstring = ""

            # Extract the docstring (if there is one)
            if_child = node.body[0]
            if hasattr(if_child, 'value') and isinstance(if_child.value, ast.Str):
                docstring = if_child.value.s

            # Add it to our dict
            commands[cmd] = docstring

    return commands
