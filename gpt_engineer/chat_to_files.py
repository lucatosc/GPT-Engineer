import os
import re

from typing import List, Tuple


def parse_chat(chat) -> List[Tuple[str, str]]:
    """
    Extracts all code blocks from a chat and returns them
    as a list of (filename, codeblock) tuples.

    Parameters
    ----------
    chat : str
        The chat to extract code blocks from.

    Returns
    -------
    List[Tuple[str, str]]
        A list of tuples, where each tuple contains a filename and a code block.
    """
    # Get all ``` blocks and preceding filenames
    regex = r"(\S+)\n\s*```[^\n]*\n(.+?)```"
    matches = re.finditer(regex, chat, re.DOTALL)

    files = []
    for match in matches:
        # Strip the filename of any non-allowed characters and convert / to \
        path = re.sub(r'[\:<>"|?*]', "", match.group(1))

        # Remove leading and trailing brackets
        path = re.sub(r"^\[(.*)\]$", r"\1", path)

        # Remove leading and trailing backticks
        path = re.sub(r"^`(.*)`$", r"\1", path)

        # Remove trailing ]
        path = re.sub(r"[\]\:]$", "", path)

        # Get the code
        code = match.group(2)

        # Add the file to the list
        files.append((path, code))

    # Get all the text before the first ``` block
    readme = chat.split("```")[0]
    files.append(("README.md", readme))

    # Return the files
    return files


def to_files(chat, workspace):
    """
    Parse the chat and add all extracted files to the workspace.

    Parameters
    ----------
    chat : str
        The chat to parse.
    workspace : dict
        The workspace to add the files to.
    """
    workspace["all_output.txt"] = chat

    files = parse_chat(chat)
    for file_name, file_content in files:
        workspace[file_name] = file_content


def overwrite_files(chat, dbs):
    """
    Replace the AI files with the older local files.

    Parameters
    ----------
    chat : str
        The chat containing the AI files.
    dbs : DBs
        The database containing the workspace.
    replace_files : dict
        A dictionary mapping file names to file paths of the local files.
    """
    dbs.workspace["all_output.txt"] = chat

    files = parse_chat(chat)
    for file_name, file_content in files:
        if file_name == "README.md":
            dbs.workspace["LAST_MODIFICATION_README.md"] = file_content
        else:
            dbs.workspace[file_name] = file_content


def get_code_strings(input) -> dict[str, str]:
    """
    Read file_list.txt and return file names and their content.

    Parameters
    ----------
    input : dict
        A dictionary containing the file_list.txt.

    Returns
    -------
    dict[str, str]
        A dictionary mapping file names to their content.
    """
    files_paths = input["file_list.txt"].strip().split("\n")
    files_dict = {}
    for full_file_path in files_paths:
        with open(full_file_path, "r") as file:
            file_data = file.read()
        if file_data:
            # TODO: Should below be the full path?
            file_name = os.path.relpath(full_file_path, input.path)
            files_dict[file_name] = file_data
    return files_dict


def format_file_to_input(file_name: str, file_content: str) -> str:
    """
    Format a file string to use as input to the AI agent.

    Parameters
    ----------
    file_name : str
        The name of the file.
    file_content : str
        The content of the file.

    Returns
    -------
    str
        The formatted file string.
    """
    file_str = f"""
    {file_name}
    ```
    {file_content}
    ```
    """
    return file_str
