# Info Debug

## English Version

This project is a Java bug repair tool based on Defects4J and large language models (LLMs).

## Directory Structure

- `src/` - main source code directory
  - `config.py` - global configuration
  - `client.py` - execution entry point
  - `runner.py` - execution flow and multi-thread scheduling
  - `defs/bug_info.py` - loads bug metadata from JSON files
  - `llm/` - LLM client, prompt builder, and prompt templates
  - `pipeline/` - pipelines for different processing modes
  - `utils/` - utilities for bug list building, output collection, logging, validation, etc.
- `data/` - Defects4J preprocessed data
  - `location/` - location files
  - `bug_info/` - bug metadata JSON files
- `defects4j/` - Defects4J framework directory

## Environment Setup

### Python Environment

Recommended Python version: `3.10+`.

```bash
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If you use Conda:

```bash
conda create -n info_debug python=3.11 -y
conda activate info_debug
python -m pip install -r requirements.txt
```

If you do not use `requirements.txt`, install the minimum required packages manually:

```bash
python -m pip install openai tiktoken javalang
```

### Defects4J

This project depends on the Defects4J command-line tool.

1. Install Defects4J and make sure the `defects4j` command is available.
2. Clone or install it into a local directory, for example `~/defects4j`.
3. Set `BasicConfig.D4J_PATH` in `src/config.py` to the Defects4J root directory:

```python
class BasicConfig:
    D4J_PATH = os.path.expanduser("~/defects4j")
```

If your Defects4J installation path is different from `~/defects4j`, update it accordingly.

### Platform Note

The project is primarily developed for Linux. Running on Windows may produce issues due to command and path differences.

## `config.py` Parameter Guide

### BasicConfig

- `PLATFORM` - execution platform, currently set to `linux`.
- `BASE_PATH` - absolute path to the `src` directory.
- `D4J_PATH` - root path for Defects4J.
- `DEBUG_PATH` - directory for exported patches and debug data.
- `LOG_PATH` - LLM log output directory.
- `OUTPUT_PATH` - result output directory.
- `TEMP_PATH` - temporary working directory.
- `LOC_PATH` - path to `data/location`, containing `.buggy.lines` files.
- `BUG_INFO_PATH` - path to `data/bug_info`.
- `TEST_PATH` - path to `data/test_functions`.
- `INDEX_MAP_JSON` - bug index mapping file path.
- `BUG_INFO_JSON` - bug metadata JSON file path.
- `FAILING_TEST_JSON` - failing test metadata JSON file path.
- `FILE_HASH_JSON` - file hash metadata JSON file path.
- `OUTPUT_FILE_NAME` - base log filename.
- `DEBUG_MODE` - enable debug mode (export patches, write LLM logs).
- `THREAD_COUNT` - number of concurrent threads.

### LLMConfig

- `LLM_MODEL` - local model label for log directory naming.
- `BASE_URL` - base URL for the LLM API.
- `MODEL` - the model identifier used for requests.
- `API_KEY` - LLM API key.
- `TEMPERATURE` - sampling temperature.
- `MAX_RETRIES` - maximum retry count.
- `TIMEOUT_LIMIT` - timeout in seconds for each request.
- `TOKEN_ENCODING_NAME` - token encoding name.
- `MAX_TOKEN` - maximum token limit.

### HyperParamConfig

- `MAX_ITER` - number of debug repair attempts after direct repair.
- `MAX_EPOCH` - number of epochs.
- `AUGMENT_SIZE` - augmentation size.
- `INSERT_MAX_ATTEMPT` - maximum insert-print attempts.

### ValidatorConfig

- `TRIGGER_TEST_TIMEOUT_LIMIT` - timeout for trigger tests (seconds).
- `FULL_TEST_TIMEOUT_LIMIT` - timeout for full test suite (seconds).
- `COLLECT_OUTPUT_TIMEOUT_LIMIT` - timeout for `COLLECT_OUTPUT` mode (seconds).

### ClientConfig

- `DEFAULT` - run the default bug list if enabled.
- `RANGE` - run a continuous bug range if enabled.
- `CUSTOM` - run a custom bug list if enabled.
- `RANGE_START` / `RANGE_END` - start and end indices for range mode.
- `CUSTOM_LIST` - custom bug index list.

## Usage

### 1. Prepare Data

Ensure the JSON files in `data/bug_info` exist and are valid, and that `data/location` contains `.buggy.lines` files.

### 2. Adjust Configuration

- `BasicConfig.MODE`: set the run mode.
- `BasicConfig.DEBUG_MODE`: set to `True` to enable debug logs and patch exports.
- `BasicConfig.THREAD_COUNT`: control concurrency.
- `ClientConfig`: control which bugs are executed.

### 3. Run the Project

From the repository root:

```bash
python src/client.py
```

### 4. Output Locations

The project writes results to:

- `output/` - result logs
- `log/` - LLM call logs
- `debug/` - exported debug patches or files
- `temp/` - temporary run directories

### 5. Example Configuration

Run the default bug list:

```bash
python src/client.py
```

Use a specific bug range by modifying `ClientConfig` in `src/config.py`:

```python
class ClientConfig:
    DEFAULT = False
    RANGE = True
    CUSTOM = False
    RANGE_START = 1
    RANGE_END = 50
```

Use a custom list:

```python
class ClientConfig:
    DEFAULT = False
    RANGE = False
    CUSTOM = True
    CUSTOM_LIST = [1, 2, 5, 10]
```
