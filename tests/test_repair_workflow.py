from types import SimpleNamespace

from pipeline import info_debug


def _configure_small_budget(monkeypatch, sessions=2, rounds=3):
    monkeypatch.setattr(info_debug.HyperParamConfig, "MAX_EPOCH", sessions)
    monkeypatch.setattr(info_debug.HyperParamConfig, "MAX_ITER", rounds)
    monkeypatch.setattr(info_debug.HyperParamConfig, "AUGMENT_SIZE", 0)
    monkeypatch.setattr(info_debug, "update_status_and_final_msg", lambda *a, **k: None)
    monkeypatch.setattr(info_debug, "update_plausible_patches", lambda *a, **k: None)


def test_direct_success_skips_instrumentation(monkeypatch):
    events = []
    _configure_small_budget(monkeypatch, sessions=1, rounds=3)
    monkeypatch.setattr(
        info_debug,
        "direct_repair_pipeline",
        lambda **kwargs: events.append("direct") or (True, "", "patch", {}),
    )
    monkeypatch.setattr(
        info_debug,
        "insert_print_pipeline",
        lambda **kwargs: events.append("instrument") or ("instrumented", "trace"),
    )
    monkeypatch.setattr(
        info_debug,
        "debug_repair_pipeline",
        lambda **kwargs: events.append("debug") or (False, "failed", "bad", {}),
    )
    monkeypatch.setattr(
        info_debug,
        "patch_augment_pipeline",
        lambda **kwargs: (False, "", "", {}),
    )

    info_debug.pipeline(
        "Chart-1",
        SimpleNamespace(),
        object(),
        SimpleNamespace(build_feedback=lambda message, patch: f"{patch}:{message}"),
    )

    assert events == ["direct"]


def test_sessions_refresh_trace_and_manage_feedback_history(monkeypatch):
    events = []
    debug_calls = []
    direct_count = 0
    instrumentation_count = 0
    debug_count = 0
    _configure_small_budget(monkeypatch, sessions=2, rounds=3)

    def direct_repair(**kwargs):
        nonlocal direct_count
        direct_count += 1
        events.append(f"direct-{direct_count}")
        return False, f"direct-error-{direct_count}", f"direct-patch-{direct_count}", {}

    def instrument(**kwargs):
        nonlocal instrumentation_count
        instrumentation_count += 1
        events.append(f"instrument-{instrumentation_count}")
        return f"instrumented-{instrumentation_count}", f"trace-{instrumentation_count}"

    def debug_repair(**kwargs):
        nonlocal debug_count
        debug_count += 1
        events.append(f"debug-{debug_count}")
        debug_calls.append(
            {
                "trace": kwargs["runtime_output"],
                "feedback": kwargs["feedback"],
            }
        )
        return False, f"debug-error-{debug_count}", f"debug-patch-{debug_count}", {}

    monkeypatch.setattr(info_debug, "direct_repair_pipeline", direct_repair)
    monkeypatch.setattr(info_debug, "insert_print_pipeline", instrument)
    monkeypatch.setattr(info_debug, "debug_repair_pipeline", debug_repair)
    monkeypatch.setattr(
        info_debug,
        "patch_augment_pipeline",
        lambda **kwargs: (False, "", "", {}),
    )

    info_debug.pipeline(
        "Chart-1",
        SimpleNamespace(),
        object(),
        SimpleNamespace(
            build_feedback=lambda message, patch: f"PATCH={patch}; ERROR={message}"
        ),
    )

    assert events == [
        "direct-1",
        "instrument-1",
        "debug-1",
        "debug-2",
        "direct-2",
        "instrument-2",
        "debug-3",
        "debug-4",
    ]
    assert [call["trace"] for call in debug_calls] == [
        "trace-1",
        "trace-1",
        "trace-2",
        "trace-2",
    ]
    assert "direct-patch-1" in debug_calls[0]["feedback"]
    assert "debug-patch-1" in debug_calls[1]["feedback"]
    assert "direct-patch-1" not in debug_calls[2]["feedback"]
    assert "direct-patch-2" in debug_calls[2]["feedback"]


def test_missing_runtime_trace_skips_debug_rounds_and_retries_session(monkeypatch):
    events = []
    statuses = []
    _configure_small_budget(monkeypatch, sessions=2, rounds=3)
    monkeypatch.setattr(
        info_debug,
        "direct_repair_pipeline",
        lambda **kwargs: events.append("direct")
        or (False, "direct failed", "bad patch", {}),
    )
    monkeypatch.setattr(
        info_debug,
        "insert_print_pipeline",
        lambda **kwargs: events.append("instrument") or ("instrumented", ""),
    )
    monkeypatch.setattr(
        info_debug,
        "debug_repair_pipeline",
        lambda **kwargs: events.append("debug")
        or (False, "debug failed", "bad patch", {}),
    )
    monkeypatch.setattr(
        info_debug,
        "patch_augment_pipeline",
        lambda **kwargs: (False, "", "", {}),
    )
    monkeypatch.setattr(
        info_debug,
        "update_status_and_final_msg",
        lambda **kwargs: statuses.append(kwargs),
    )

    info_debug.pipeline(
        "Chart-1",
        SimpleNamespace(),
        object(),
        SimpleNamespace(build_feedback=lambda message, patch: "feedback"),
    )

    assert events == ["direct", "instrument", "direct", "instrument"]
    assert statuses == [
        {
            "bug_id": "Chart-1",
            "status": False,
            "final_msg": "Runtime trace unavailable in debugging session 2",
        }
    ]
