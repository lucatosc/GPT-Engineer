from gpt_engineer.core.code import Code
from gpt_engineer.core.base_version_manager import BaseVersionManager
from gpt_engineer.core.ai import AI
from gpt_engineer.core.default.steps import (
    gen_code,
    gen_entrypoint,
    execute_entrypoint,
    improve,
)
from gpt_engineer.core.base_repository import BaseRepository
from gpt_engineer.core.default.on_disk_repository import OnDiskRepository
from gpt_engineer.core.base_execution_env import BaseExecutionEnv
from gpt_engineer.core.default.on_disk_execution_env import OnDiskExecutionEnv
from gpt_engineer.core.default.paths import memory_path, ENTRYPOINT_FILE
from gpt_engineer.core.base_agent import BaseAgent
from gpt_engineer.applications.cli.learning import human_review
from typing import TypeVar, Callable

CodeGenType = TypeVar(
    "CodeGenType", bound=Callable[[AI, str, BaseRepository], Code]
)
ExecuteEntrypointType = TypeVar(
    "ExecuteEntrypointType", bound=Callable[[AI, BaseExecutionEnv, Code], None]
)
ImproveType = TypeVar(
    "ImproveType", bound=Callable[[AI, str, Code, BaseRepository], Code]
)

class CliAgent(BaseAgent):
    """
    The `Agent` class is responsible for managing the lifecycle of code generation and improvement.

    Attributes:
        path (str): The file path where the `Agent` will operate, used for version management and
                    file operations.
        version_manager (BaseVersionManager): An object that adheres to the VersionManagerInterface,
                        responsible for version control of the generated code. Defaults to `VersionManager`
                        if not provided. PROBABLY GIT SHOULD BE USED IN THE DEFAULT
        step_bundle (StepBundleInterface): Workflows of code generation steps that define the behavior of gen_code and
        improve.
        ai (AI): Manages calls to the LLM.

    Methods:
        __init__(self, path: str, version_manager: VersionManagerInterface = None,
                 step_bundle: StepBundleInterface = None, ai: AI = None):
            Initializes a new instance of the Agent class with the provided path, version manager,
            step bundle, and AI. It falls back to default instances if specific components are not provided.

        init(self, prompt: str) -> Code:
            Generates a new piece of code using the AI and step bundle based on the provided prompt.
            It also snapshots the generated code using the version manager.

            Parameters:
                prompt (str): A string prompt that guides the code generation process.

            Returns:
                Code: An instance of the `Code` class containing the generated code.

        improve(self, prompt: str) -> Code:
            Improves an existing piece of code using the AI and step bundle based on the provided prompt.
            It also snapshots the improved code using the version manager.

            Parameters:
                prompt (str): A string prompt that guides the code improvement process.

            Returns:
                Code: An instance of the `Code` class containing the improved code.
    """

    def __init__(
        self,
        memory: BaseRepository,
        execution_env: BaseExecutionEnv,
        ai: AI = None,
        code_gen_fn: CodeGenType = gen_code,
        execute_entrypoint_fn: ExecuteEntrypointType = execute_entrypoint,
        improve_fn: ImproveType = improve
    ):
        self.memory = memory
        self.execution_env = execution_env
        self.ai = ai or AI()
        self.code_gen_fn = code_gen_fn
        self.execute_entrypoint_fn = execute_entrypoint_fn
        self.improve_fn = improve_fn

    @classmethod
    def with_default_config(cls, path: str, ai: AI = None, code_gen_fn: CodeGenType = gen_code, execute_entrypoint_fn: ExecuteEntrypointType = execute_entrypoint, improve_fn: ImproveType = improve):
        return cls(
            memory=OnDiskRepository(memory_path(path)),
            execution_env=OnDiskExecutionEnv(path),
            ai=ai,
            code_gen_fn=code_gen_fn,
            execute_entrypoint_fn=execute_entrypoint_fn,
            improve_fn=improve_fn
        )

    def init(self, prompt: str) -> Code:
        code = self.code_gen_fn(self.ai, prompt, self.memory)
        entrypoint = gen_entrypoint(self.ai, code, self.memory)
        code = Code(code | entrypoint)
        self.execute_entrypoint_fn(self.ai, self.execution_env, code)
        human_review(self.memory)
        return code

    def improve(self, prompt: str, code: Code) -> Code:
        code = self.improve_fn(self.ai, prompt, code, self.memory)
        if not ENTRYPOINT_FILE in code:
            entrypoint = gen_entrypoint(self.ai, code, self.memory)
            code = Code(code | entrypoint)
        self.execute_entrypoint_fn(self.ai, self.execution_env, code)
        human_review(self.memory)
        return code
