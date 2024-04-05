import os
import tempfile

import pytest

from langchain.schema import AIMessage

from gpt_engineer.applications.cli.cli_agent import CliAgent
from gpt_engineer.core.default.disk_execution_env import DiskExecutionEnv
from gpt_engineer.core.default.disk_memory import DiskMemory

# from gpt_engineer.core.default.git_version_manager import GitVersionManager
from gpt_engineer.core.default.paths import ENTRYPOINT_FILE, memory_path
from gpt_engineer.core.files_dict import FilesDict
from gpt_engineer.core.prompt import Prompt
from gpt_engineer.tools.custom_steps import clarified_gen, lite_gen
from tests.mock_ai import MockAI


def test_init_standard_config(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")
    temp_dir = tempfile.mkdtemp()
    memory = DiskMemory(memory_path(temp_dir))
    execution_env = DiskExecutionEnv()
    mock_ai = MockAI(
        [
            AIMessage(
                "hello_world.py\n```\nwith open('output.txt', 'w') as file:\n    file.write('Hello World!')\n```"
            ),
            AIMessage("```run.sh\npython3 hello_world.py\n```"),
        ],
    )
    cli_agent = CliAgent.with_default_config(memory, execution_env, ai=mock_ai)
    outfile = "output.txt"
    os.path.join(temp_dir, outfile)
    code = cli_agent.init(
        Prompt(
            f"Make a program that prints 'Hello World!' to a file called '{outfile}'"
        )
    )

    env = DiskExecutionEnv()
    env.upload(code).run(f"bash {ENTRYPOINT_FILE}")
    code = env.download()

    assert outfile in code
    assert code[outfile] == "Hello World!"


def test_init_lite_config(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")
    temp_dir = tempfile.mkdtemp()
    memory = DiskMemory(memory_path(temp_dir))
    # version_manager = GitVersionManager(temp_dir)
    execution_env = DiskExecutionEnv()
    mock_ai = MockAI(
        [
            AIMessage(
                "hello_world.py\n```\nwith open('output.txt', 'w') as file:\n    file.write('Hello World!')\n```"
            ),
            AIMessage("```run.sh\npython3 hello_world.py\n```"),
        ],
    )
    cli_agent = CliAgent.with_default_config(
        memory, execution_env, ai=mock_ai, code_gen_fn=lite_gen
    )
    outfile = "output.txt"
    os.path.join(temp_dir, outfile)
    code = cli_agent.init(
        Prompt(
            f"Make a program that prints 'Hello World!' to a file called '{outfile}'"
        )
    )

    env = DiskExecutionEnv()
    env.upload(code).run(f"bash {ENTRYPOINT_FILE}")
    code = env.download()

    assert outfile in code
    assert code[outfile].strip() == "Hello World!"


def test_init_clarified_gen_config(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")
    temp_dir = tempfile.mkdtemp()
    memory = DiskMemory(memory_path(temp_dir))
    execution_env = DiskExecutionEnv()
    mock_ai = MockAI(
        [
            AIMessage("nothing to clarify"),
            AIMessage(
                "hello_world.py\n```\nwith open('output.txt', 'w') as file:\n    file.write('Hello World!')\n```"
            ),
            AIMessage("```run.sh\npython3 hello_world.py\n```"),
        ],
    )
    cli_agent = CliAgent.with_default_config(
        memory, execution_env, ai=mock_ai, code_gen_fn=clarified_gen
    )
    outfile = "output.txt"
    code = cli_agent.init(
        Prompt(
            f"Make a program that prints 'Hello World!' to a file called '{outfile} either using python or javascript'"
        )
    )

    env = DiskExecutionEnv()
    env.upload(code).run(f"bash {ENTRYPOINT_FILE}")
    code = env.download()

    assert outfile in code
    assert code[outfile].strip() == "Hello World!"


def test_improve_standard_config(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")
    temp_dir = tempfile.mkdtemp()
    code = FilesDict(
        {
            "main.py": "def write_hello_world_to_file(filename):\n    \"\"\"\n    Writes 'Hello World!' to the specified file.\n    \n    :param filename: The name of the file to write to.\n    \"\"\"\n    with open(filename, 'w') as file:\n        file.write('Hello World!')\n\nif __name__ == \"__main__\":\n    output_filename = 'output.txt'\n    write_hello_world_to_file(output_filename)",
            "requirements.txt": "# No dependencies required",
            "run.sh": "python3 main.py\n",
        }
    )
    memory = DiskMemory(memory_path(temp_dir))
    # version_manager = GitVersionManager(temp_dir)
    execution_env = DiskExecutionEnv()
    mock_ai = MockAI(
        [
            AIMessage(
                "```diff\n--- main.py\n+++ main.py\n@@ -7,3 +7,3 @@\n     with open(filename, 'w') as file:\n-        file.write('Hello World!')\n+        file.write('!dlroW olleH')\n```"
            )
        ]
    )
    cli_agent = CliAgent.with_default_config(memory, execution_env, ai=mock_ai)

    code = cli_agent.improve(
        code,
        Prompt(
            "Change the program so that it prints '!dlroW olleH' instead of 'Hello World!'"
        ),
    )

    env = DiskExecutionEnv()
    env.upload(code).run(f"bash {ENTRYPOINT_FILE}")
    code = env.download()

    outfile = "output.txt"
    assert outfile in code
    assert code[outfile] == "!dlroW olleH"


if __name__ == "__main__":
    pytest.main()
