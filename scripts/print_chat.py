"""
This module provides functionality to print a conversation with messages
colored according to the role of the speaker.
"""

import json

import typer

from termcolor import colored

app = typer.Typer()


def pretty_print_conversation(messages):
    """
    Prints a conversation with messages formatted and colored by role.

    Parameters
    ----------
    messages : list
        A list of message dictionaries, each containing 'role', 'name', and 'content' keys.

    """

    role_to_color = {
        "system": "red",
        "user": "green",
        "assistant": "blue",
        "function": "magenta",
    }
    formatted_messages = []
    


@app.command()
def main(
    messages_path: str,
):
    """
    Main function that loads messages from a JSON file and prints them using pretty formatting.

    Parameters
    ----------
    messages_path : str
        The file path to the JSON file containing the messages.

    """
    with open(messages_path) as f:
        messages = json.load(f)

    pretty_print_conversation(messages)


if __name__ == "__main__":
    app()
