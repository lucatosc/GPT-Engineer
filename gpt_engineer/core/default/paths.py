import os

META_DATA_REL_PATH = ".gpteng"
MEMORY_REL_PATH = os.path.join(META_DATA_REL_PATH, "memory")
CODE_GEN_LOG_FILE = "all_output.txt"
ENTRYPOINT_FILE = "run.sh"
ENTRYPOINT_LOG_FILE = "gen_entrypoint_chat.txt"


def memory_path(path):
    return os.path.join(path, MEMORY_REL_PATH)
