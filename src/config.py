import os

class BasicConfig:
    PLATFORM = 'linux' # Running on Windows may produce issues due to command.

    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
    D4J_PATH = os.path.expanduser("~/defects4j")

    DEBUG_PATH = os.path.join(BASE_PATH, "..", "debug")
    LOG_PATH = os.path.join(BASE_PATH, "..", "log")
    OUTPUT_PATH = os.path.join(BASE_PATH, "..", "output")  # 实际生成文件的路径为output.mode.model.output_log.json  actual output path is output.mode.model.output_log.json
    TEMP_PATH = os.path.join(BASE_PATH, "..", "temp")  # 实际的临时路径为temp.mode.model.bugid  actual temp path is temp.mode.model.bugid

    LOC_PATH = os.path.join(BASE_PATH, "..", "data", "location")
    BUG_INFO_PATH = os.path.join(BASE_PATH, "..", "data", "bug_info")
    TEST_PATH = os.path.join(BASE_PATH, "..", "data", "test_functions")

    INDEX_MAP_JSON = os.path.join(BUG_INFO_PATH, "index_map.json")
    BUG_INFO_JSON = os.path.join(BUG_INFO_PATH, "bug_info.json")
    FAILING_TEST_JSON = os.path.join(BUG_INFO_PATH, "failing_test.json")
    FILE_HASH_JSON = os.path.join(BUG_INFO_PATH, "file_hash.json")

    MODE = "INFO_DEBUG"

    INSTRUMENTED_CODE_INPUT_PATH = os.path.join(BASE_PATH, ".." , "input", "instrumented_code.json") 
    # 仅用于COLLECT_OUTPUT模式  only used for COLLECT_OUTPUT mode

    OUTPUT_FILE_NAME = "output_log"
    DEBUG_MODE = True   # 导出补丁，输出llm日志  export patch, output llm log
    
    THREAD_COUNT = 1

class LLMConfig:
    LLM_MODEL = "replace_with_model_name_do_not_use_symbol_except_underline_or_dash"

    BASE_URL = "replace_with_base_url"
    MODEL = "replace_with_model"
    API_KEY = "replace_with_your_api_key"

    TEMPERATURE = 1.0
    MAX_RETRIES = 5
    TIMEOUT_LIMIT = 120

    TOKEN_ENCODING_NAME = 'cl100k_base'
    MAX_TOKEN = 4096

class HyperParamConfig:
    MAX_ITER = 4    # 每次 direct repair 后 debug repair 的数量  the count of debug repair after each direct repair
    MAX_EPOCH = 10
    AUGMENT_SIZE = 10

    INSERT_MAX_ATTEMPT = 10

class ValidatorConfig:
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