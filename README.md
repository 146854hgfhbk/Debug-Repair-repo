# DebugRepair

DebugRepair is an LLM-based automated program repair system for Java bugs. This
repository contains the paper-aligned Defects4J functional core: test semantic
purification data, hybrid instrumentation, runtime trace collection,
conversation-based repair, validation, and patch augmentation.

The included corpus contains 483 single-function bugs from Defects4J 1.2 and
2.0. QuixBugs and HumanEval-Java experiments described in the paper are not
included in this repository.

## Repository Layout

- `src/`: repair workflow, prompts, model clients, instrumentation, trace
  collection, and validation.
- `data/`: the 483-bug corpus, perfect fault locations, and purified tests.
- `tools/java-instrumenter/`: the JavaParser helper used for normalization,
  method replacement, and rule-based instrumentation.
- `tests/`: unit and regression tests.
- `validator-server.py` and `validator-worker.py`: optional remote Defects4J
  validation service.
- `run.sh`: Linux launcher that loads a private `.env` file.

## Requirements

Use Linux for the full experiment. Windows is suitable for unit tests, but
Defects4J projects and historical build systems are substantially more reliable
on Linux.

Required software:

- Python 3.10 or newer; Python 3.11 is recommended.
- A JDK providing both `java` and `javac`. JDK 8 is the safest default for
  the Defects4J 2.0 projects.
- Defects4J 2.0 and its Perl dependencies.
- Access to an OpenAI-compatible chat-completions API for the repair model.
- Git and network access during setup. The JavaParser builder downloads one
  pinned Maven dependency and verifies its SHA-256 checksum.

## 1. Install Defects4J 2.0

Follow the upstream Defects4J prerequisites, then install the version used by
this corpus:

```bash
git clone https://github.com/rjust/defects4j.git "$HOME/defects4j"
cd "$HOME/defects4j"
git checkout v2.0.0
cpanm --installdeps .
./init.sh
export PATH="$HOME/defects4j/framework/bin:$PATH"
defects4j query -p Chart -q 'bug.id,tests.trigger' >/dev/null
```

The final command must exit successfully. A different installation location is
fine; configure its executable explicitly in step 3.

## 2. Install Python and JavaParser Dependencies

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python tools/java-instrumenter/build.py --force --print-classpath
python -m pytest -q
```

The JavaParser build command downloads JavaParser Core 3.26.3, verifies its
pinned checksum, and compiles the helper locally. Generated classes and the JAR
are cached under `tools/java-instrumenter/build/` and are ignored by Git.

The full 483-method JavaParser round-trip test is optional:

```bash
DEBUGREPAIR_FULL_CORPUS=1 python -m pytest \
  tests/test_repository_java_instrumentation.py::test_every_repository_method_round_trips_through_javaparser -q
```

## 3. Configure the Model and Defects4J

Create a private configuration file:

```bash
cp .env.example .env
```

Edit `.env` and set these required values:

```bash
DEBUGREPAIR_LLM_LABEL=paper-backbone
DEBUGREPAIR_LLM_BASE_URL=https://provider.example/v1
DEBUGREPAIR_LLM_MODEL=replace-with-model-id
DEBUGREPAIR_LLM_API_KEY=replace-with-api-key
DEBUGREPAIR_DEFECTS4J=/home/USER/defects4j/framework/bin/defects4j
```

`DEBUGREPAIR_LLM_LABEL` is a filesystem-safe experiment label used for output
directories. It is not sent to the API. The default repair temperature is
`1.0`, matching the paper.

By default, repair and instrumentation use the same endpoint, model, and API
key. To use a separate instrumentation model, set the optional
`DEBUGREPAIR_INSTRUMENT_LLM_*` variables shown in `.env.example`. Set
`DEBUGREPAIR_INSTRUMENT_LLM_PROVIDER=anthropic` only for an Anthropic-native
instrumentation endpoint; otherwise keep the default `openai`.

Never commit `.env`; it is ignored by Git.

## 4. Validate the Installation Without Calling an LLM

```bash
bash run.sh --check-config
```

This command does not send an API request. It checks:

- required model settings;
- Java and `javac`;
- the Defects4J executable, unless remote validation is enabled;
- the 483-entry data index; and
- the JavaParser helper build.

Resolve every reported error before starting an experiment.

## 5. Run One Smoke Bug

Start with index 1, which maps to `Chart-1`:

```bash
bash run.sh --bugs 1
```

This command does call the configured model API and executes Defects4J
compilation and tests. Results are written under:

```text
output/INFO_DEBUG/<label>/output_log.json
log/<label>/llm_log.jsonl
debug/
temp/
```

Run several selected indices with:

```bash
bash run.sh --bugs 1 2 3
```

Completed bugs with terminal status `success` or `fail` are skipped when the
same command is resumed.

## 6. Run the Full 483-Bug Experiment

Only start the full run after the single-bug smoke test succeeds:

```bash
bash run.sh
```

With no `--bugs` argument, `ClientConfig.DEFAULT` runs all 483 bugs. This is
an expensive experiment: a bug may use multiple repair, instrumentation, and
augmentation requests, plus repeated Defects4J test executions. Control
parallelism conservatively with:

```bash
DEBUGREPAIR_BUG_WORKERS=4
```

Put that setting in `.env` rather than editing source.

## Runtime Workflow

The default `INFO_DEBUG` mode performs:

1. direct repair using the buggy method, purified failing test, and error data;
2. LLM instrumentation with AST normalization and Defects4J compilation gates;
3. deterministic JavaParser instrumentation after failed LLM attempts;
4. execution of exactly one purified failing test to collect a runtime trace;
5. validator-guided conversational repair;
6. trigger-test and full-suite validation; and
7. eight alternative patch-generation attempts after finding a plausible patch.

The paper budget is configured in `src/config.py`: six debugging sessions,
four repair rounds per session including direct repair, ten instrumentation
attempts, and eight augmentation requests. Perfect fault locations are marked
with `// Buggy Line`.

## Optional Remote Validation

To keep model calls on one host and run Defects4J on another, start
`validator-server.py` on the validation host with
`DEBUGREPAIR_VALIDATOR_TOKEN`, `DEBUGREPAIR_VALIDATOR_WORK_ROOT`, and the
local Defects4J environment configured. On the model host set:

```bash
DEBUGREPAIR_VALIDATOR_URL=http://validator-host:9001
DEBUGREPAIR_VALIDATOR_TOKEN=replace-with-a-shared-secret
```

When `DEBUGREPAIR_VALIDATOR_URL` is set, compilation, runtime trace collection,
and patch validation are delegated to that service. Put TLS and access control
in front of the service when it is reachable beyond a trusted private network.
