import os

class BasicConfig:
    PLATFORM = 'linux' # Running on Windows may produce issues due to command.

    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
    D4J_PATH = os.path.expanduser("~/defects4j")

    DEBUG_PATH = os.getenv(
        "DEBUGREPAIR_DEBUG_PATH", os.path.join(BASE_PATH, "..", "debug")
    )
    LOG_PATH = os.path.join(BASE_PATH, "..", "log")
    OUTPUT_PATH = os.path.join(BASE_PATH, "..", "output")  # 实际生成文件的路径为output.mode.model.output_log.json  actual output path is output.mode.model.output_log.json
    TEMP_PATH = os.getenv(
        "DEBUGREPAIR_TEMP_PATH", os.path.join(BASE_PATH, "..", "temp")
    )  # 实际的临时路径为temp.mode.model.bugid  actual temp path is temp.mode.model.bugid

    DATA_ROOT = os.getenv(
        "DEBUGREPAIR_DATA_ROOT", os.path.join(BASE_PATH, "..", "data")
    )
    LOC_PATH = os.path.join(DATA_ROOT, "location")
    BUG_INFO_PATH = os.path.join(DATA_ROOT, "bug_info")
    TEST_PATH = os.path.join(DATA_ROOT, "test_functions")

    INDEX_MAP_JSON = os.path.join(BUG_INFO_PATH, "index_map.json")
    BUG_INFO_JSON = os.path.join(BUG_INFO_PATH, "bug_info.json")
    FAILING_TEST_JSON = os.path.join(BUG_INFO_PATH, "failing_test.json")
    FILE_HASH_JSON = os.path.join(BUG_INFO_PATH, "file_hash.json")

    MODE = "INFO_DEBUG"

    INSTRUMENTED_CODE_INPUT_PATH = os.path.join(BASE_PATH, ".." , "input", "instrumented_code.json") 
    # 仅用于COLLECT_OUTPUT模式  only used for COLLECT_OUTPUT mode

    OUTPUT_FILE_NAME = "output_log"
    DEBUG_MODE = True   # 导出补丁，输出llm日志  export patch, output llm log
    
    THREAD_COUNT = int(os.getenv("DEBUGREPAIR_BUG_WORKERS", "1"))

class LLMConfig:
    LLM_MODEL = "replace_with_model_name_do_not_use_symbol_except_underline_or_dash"

    BASE_URL = "replace_with_base_url"
    MODEL = "replace_with_model"
    API_KEY = "replace_with_your_api_key"
    REASONING_EFFORT = os.getenv("DEBUGREPAIR_LLM_REASONING_EFFORT", "medium")

    TEMPERATURE = 1.0
    MAX_RETRIES = 5
    TIMEOUT_LIMIT = int(os.getenv("DEBUGREPAIR_LLM_TIMEOUT", "120"))

    TOKEN_ENCODING_NAME = 'cl100k_base'
    MAX_TOKEN = 4096


class InstrumentationLLMConfig:
    BASE_URL = os.getenv("DEBUGREPAIR_INSTRUMENT_LLM_BASE_URL", "")
    MODEL = os.getenv("DEBUGREPAIR_INSTRUMENT_LLM_MODEL", "")
    API_KEY = os.getenv("DEBUGREPAIR_INSTRUMENT_LLM_API_KEY", "")
    REASONING_EFFORT = os.getenv(
        "DEBUGREPAIR_INSTRUMENT_LLM_REASONING_EFFORT", "high"
    )
    PROVIDER = os.getenv("DEBUGREPAIR_INSTRUMENT_LLM_PROVIDER", "openai")
    TEMPERATURE = None

class HyperParamConfig:
    MAX_ITER = 4    # total repair rounds per session, including direct repair
    MAX_EPOCH = 6   # debugging sessions
    AUGMENT_SIZE = 8

    MAX_REPAIR_ROUNDS = MAX_ITER
    MAX_SESSIONS = MAX_EPOCH

    INSERT_MAX_ATTEMPT = 10

class ValidatorConfig:
    DEFECTS4J_EXECUTABLE = os.getenv("DEBUGREPAIR_DEFECTS4J", "defects4j")
    TRIGGER_TEST_TIMEOUT_LIMIT = 180
    FULL_TEST_TIMEOUT_LIMIT = 1200
    COLLECT_OUTPUT_TIMEOUT_LIMIT = 180

class ClientConfig:
    DEFAULT = True
    RANGE = False
    CUSTOM = False

    RANGE_START = 1
    RANGE_END = 100

    CUSTOM_LIST = [1, 2, 3]
