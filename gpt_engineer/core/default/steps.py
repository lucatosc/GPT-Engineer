from gpt_engineer.core.code import Code
from gpt_engineer.core.ai import AI
from gpt_engineer.core.chat_to_files import (
    parse_chat,
    overwrite_code_with_edits,
    parse_edits,
)
from gpt_engineer.core.default.paths import (
    ENTRYPOINT_FILE,
    CODE_GEN_LOG_FILE,
    ENTRYPOINT_LOG_FILE,
    IMPROVE_LOG_FILE,
    PREPROMPTS_PATH,
)
from gpt_engineer.core.default.constants import MAX_EDIT_REFINEMENT_STEPS
from gpt_engineer.core.default.on_disk_memory import OnDiskMemory
from gpt_engineer.core.base_memory import BaseMemory
from gpt_engineer.core.base_execution_env import BaseExecutionEnv

from typing import Union, MutableMapping, List
from pathlib import Path
from langchain.schema import HumanMessage, SystemMessage
import inspect
import re
from termcolor import colored
from gpt_engineer.core.preprompts_holder import PrepromptsHolder


def curr_fn() -> str:
    return inspect.stack()[1].function


def setup_sys_prompt(preprompts: MutableMapping[Union[str, Path], str]) -> str:
    return (
        preprompts["roadmap"]
        + preprompts["generate"].replace("FILE_FORMAT", preprompts["file_format"])
        + "\nUseful to know:\n"
        + preprompts["philosophy"]
    )


def gen_code(
    ai: AI, prompt: str, memory: BaseMemory, preprompts_holder: PrepromptsHolder
) -> Code:
    preprompts = preprompts_holder.get_preprompts()
    messages = ai.start(setup_sys_prompt(preprompts), prompt, step_name=curr_fn())
    chat = messages[-1].content.strip()
    memory[CODE_GEN_LOG_FILE] = chat
    files = parse_chat(chat)
    code = Code({key: val for key, val in files})
    return code


def gen_entrypoint(
    ai: AI, code: Code, memory: BaseMemory, preprompts_holder: PrepromptsHolder
) -> Code:
    preprompts = preprompts_holder.get_preprompts()
    messages = ai.start(
        system=(preprompts["entrypoint"]),
        user="Information about the codebase:\n\n" + code.to_chat(),
        step_name=curr_fn(),
    )
    print()
    chat = messages[-1].content.strip()
    regex = r"```\S*\n(.+?)```"
    matches = re.finditer(regex, chat, re.DOTALL)
    entrypoint_code = Code(
        {ENTRYPOINT_FILE: "\n".join(match.group(1) for match in matches)}
    )
    memory[ENTRYPOINT_LOG_FILE] = chat
    return entrypoint_code


def execute_entrypoint(
    ai: AI,
    execution_env: BaseExecutionEnv,
    code: Code,
    preprompts_holder: PrepromptsHolder = None,
) -> Code:
    if not ENTRYPOINT_FILE in code:
        raise FileNotFoundError(
            "The required entrypoint " + ENTRYPOINT_FILE + " does not exist in the code."
        )

    command = code[ENTRYPOINT_FILE]

    print()
    print(
        colored(
            "Do you want to execute this code? (Y/n)",
            "red",
        )
    )
    print()
    print(command)
    print()
    if input().lower() not in ["", "y", "yes"]:
        print("Ok, not executing the code.")
        return []
    print("Executing the code...")
    print()
    print(
        colored(
            "Note: If it does not work as expected, consider running the code"
            + " in another way than above.",
            "green",
        )
    )
    print()
    print("You can press ctrl+c *once* to stop the execution.")
    print()

    execution_env.upload(code).run(f"bash {ENTRYPOINT_FILE}")
    return code


def setup_sys_prompt_existing_code(
    preprompts: MutableMapping[Union[str, Path], str]
) -> str:
    return (
        preprompts["improve"].replace("FILE_FORMAT", preprompts["file_format"])
        + "\nUseful to know:\n"
        + preprompts["philosophy"]
    )


def incorrect_edit(code: Code, chat: str) -> List[str,]:
    problems = []
    try:
        edits = parse_edits(chat)
    except ValueError as problem:
        print("Not possible to parse chat to edits")
        problems.append(str(problem))
        return problems

    for edit in edits:
        if not edit.filename in code:
            problems.append(
                f"A section tried to edit the file {edit.filename}, but this file does not exist in the code. Section:\n"
                + edit.filename
            )
        elif not edit.before in code[edit.filename]:
            problems.append(
                "This section, assigned to be exchanged for an edit block, does not have an exact match in the code: "
                + edit.before
                + "\nThis is often a result of placeholders, such as ... or references to 'existing code' or 'rest of function' etc, which cannot be used the HEAD part of the edit blocks. Also, to get a match, all comments, including long doc strings may have to be reproduced in the patch HEAD"
            )
    return problems


def improve(
    ai: AI,
    prompt: str,
    code: Code,
    memory: BaseMemory,
    preprompts_holder: PrepromptsHolder,
) -> Code:
    preprompts = preprompts_holder.get_preprompts()
    messages = [
        SystemMessage(content=setup_sys_prompt_existing_code(preprompts)),
    ]
    # Add files as input
    messages.append(HumanMessage(content=f"{code.to_chat()}"))
    messages.append(HumanMessage(content=f"Request: {prompt}"))
    problems = [""]
    # check edit correctness
    edit_refinements = 0
    while len(problems) > 0 and edit_refinements <= MAX_EDIT_REFINEMENT_STEPS:
        messages = ai.next(messages, step_name=curr_fn())
        chat = messages[-1].content.strip()
        problems = incorrect_edit(code, chat)
        if len(problems) > 0:
            messages.append(
                HumanMessage(
                    content=f"Some previously produced edits were not on the requested format, or the HEAD part was not found in the code. Details: "
                    + "\n".join(problems)
                    + "\n Please provide ALL the edits again, making sure that the failing ones are now on the correct format and can be found in the code. Make sure to not repeat past mistakes. \n"
                )
            )
        edit_refinements += 1
    overwrite_code_with_edits(chat, code)
    memory[IMPROVE_LOG_FILE] = chat
    return code
