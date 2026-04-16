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

---

## 中文版本

# Info Debug

本项目是一个基于 Defects4J 和 LLM 的 Java bug 修复工具。

## 目录结构

- `src/` - 主要代码目录
  - `config.py` - 全局配置项
  - `client.py` - 运行入口
  - `runner.py` - 执行流程和多线程调度
  - `defs/bug_info.py` - 从 JSON 元数据加载 bug 信息
  - `llm/` - LLM 客户端、Prompt 构建器与 prompt 模板
  - `pipeline/` - 各种处理模式的 pipeline
  - `utils/` - bug 列表构建、输出采集、日志、验证等工具
- `data/` - Defects4J 数据预处理结果
  - `location/` - 位置文件
  - `bug_info/` - bug 元数据 JSON 文件
- `defects4j/` - Defects4J 框架目录

## 环境配置

### Python 环境

建议使用 Python 3.10+。

```bash
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

如果你使用 Conda：

```bash
conda create -n info_debug python=3.11 -y
conda activate info_debug
python -m pip install -r requirements.txt
```

如果你不使用 `requirements.txt`，必须至少安装：

```bash
python -m pip install openai tiktoken javalang
```

### Defects4J

本项目依赖 Defects4J 命令行工具。

1. 安装 Defects4J 并确保 `defects4j` 命令可用。
2. 克隆或安装到本地目录，例如 `~/defects4j`。
3. 在 `src/config.py` 中设置 `BasicConfig.D4J_PATH` 为 Defects4J 根目录：

```python
class BasicConfig:
    D4J_PATH = os.path.expanduser("~/defects4j")
```

如果你的 Defects4J 安装路径不是 `~/defects4j`，请改成真实路径。

### 平台说明

项目主要基于 Linux 平台开发。Windows 上运行可能出现一些错误。

## `config.py` 参数说明

### BasicConfig

- `PLATFORM` - 运行平台，目前默认 `linux`。
- `BASE_PATH` - `src` 目录绝对路径。
- `D4J_PATH` - Defects4J 安装根目录。
- `DEBUG_PATH` - 调试时导出补丁/日志的目录。
- `LOG_PATH` - LLM 日志输出目录。
- `OUTPUT_PATH` - 结果输出目录。
- `TEMP_PATH` - 临时文件保存目录。
- `LOC_PATH` - `data/location` 目录，包含 `.buggy.lines` 等定位文件。
- `BUG_INFO_PATH` - `data/bug_info` 目录。
- `TEST_PATH` - `data/test_functions`。
- `INDEX_MAP_JSON` - bug 索引映射文件路径。
- `BUG_INFO_JSON` - bug 信息 JSON。
- `FAILING_TEST_JSON` - 失败测试数据 JSON。
- `FILE_HASH_JSON` - 文件哈希数据 JSON。
- `OUTPUT_FILE_NAME` - 输出日志文件名基准。
- `DEBUG_MODE` - 是否启用调试模式（导出补丁、输出 LLM 日志）。
- `THREAD_COUNT` - 并发线程数。

### LLMConfig

- `LLM_MODEL` - 本地模型标识，用于日志目录命名。
- `BASE_URL` - LLM API 基础地址。
- `MODEL` - 调用的具体模型名称。
- `API_KEY` - LLM API Key。
- `TEMPERATURE` - 生成温度。
- `MAX_RETRIES` - 最大重试次数。
- `TIMEOUT_LIMIT` - 单次请求超时时间（秒）。
- `TOKEN_ENCODING_NAME` - Token 编码名称。
- `MAX_TOKEN` - 最大 token 限制。

### HyperParamConfig

- `MAX_ITER` - direct repair 后的 debug repair 次数。
- `MAX_EPOCH` - 迭代 epoch 数量。
- `AUGMENT_SIZE` - 增强大小。
- `INSERT_MAX_ATTEMPT` - 插入打印时的最大尝试次数。

### ValidatorConfig

- `TRIGGER_TEST_TIMEOUT_LIMIT` - 触发测试超时时间（秒）。
- `FULL_TEST_TIMEOUT_LIMIT` - 全量测试超时时间（秒）。
- `COLLECT_OUTPUT_TIMEOUT_LIMIT` - `COLLECT_OUTPUT` 模式超时时间（秒）。

### ClientConfig

- `DEFAULT` - 开启后将运行默认的 bug 列表。
- `RANGE` - 开启后将运行指定范围的 bug 列表。
- `CUSTOM` - 开启后将运行自定义的 bug 列表。
- `RANGE_START` / `RANGE_END` - 范围开始/结束索引。
- `CUSTOM_LIST` - 自定义 bug 索引列表。

## 运行方法

### 1. 准备数据

确保 `data/bug_info` 目录下的 JSON 文件存在且格式正确；`data/location` 下包含 `.buggy.lines` 文件。

### 2. 调整配置

- `BasicConfig.MODE`：设置运行模式。
- `BasicConfig.DEBUG_MODE`：若希望输出调试日志和导出补丁，请设置为 `True`。
- `BasicConfig.THREAD_COUNT`：控制并发 bug 数量。
- `ClientConfig`：控制要运行的 bug 列表。

### 3. 运行入口

从仓库根目录执行：

```bash
python src/client.py
```

### 4. 结果输出

输出文件和日志会按照以下目录生成：

- `output/` - 结果日志输出
- `log/` - LLM 调用日志
- `debug/` - 调试导出的补丁或临时文件
- `temp/` - 运行期间的临时目录

## 5. 运行示例

```bash
python src/client.py
```

若仅希望运行特定 bug 范围，可修改 `src/config.py` 中 `ClientConfig`：

```python
class ClientConfig:
    DEFAULT = False
    RANGE = True
    CUSTOM = False
    RANGE_START = 1
    RANGE_END = 50
```

或使用自定义列表：

```python
class ClientConfig:
    DEFAULT = False
    RANGE = False
    CUSTOM = True
    CUSTOM_LIST = [1, 2, 5, 10]
```
