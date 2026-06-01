from src.runner import power


def test_prevent_system_sleep_is_noop_off_windows(monkeypatch):
    calls = []
    monkeypatch.setattr(power.os, "name", "posix")
    monkeypatch.setattr(power, "_set_thread_execution_state", calls.append)

    with power.prevent_system_sleep():
        pass

    assert calls == []


def test_prevent_system_sleep_requests_and_clears_windows_state(monkeypatch):
    calls = []

    def fake_set_thread_execution_state(flags):
        calls.append(flags)
        return 1

    monkeypatch.setattr(power.os, "name", "nt")
    monkeypatch.setattr(power, "_set_thread_execution_state", fake_set_thread_execution_state)

    with power.prevent_system_sleep():
        assert calls == [power.ES_CONTINUOUS | power.ES_SYSTEM_REQUIRED]

    assert calls == [
        power.ES_CONTINUOUS | power.ES_SYSTEM_REQUIRED,
        power.ES_CONTINUOUS,
    ]


def test_prevent_system_sleep_does_not_clear_failed_windows_request(monkeypatch):
    calls = []

    def fake_set_thread_execution_state(flags):
        calls.append(flags)
        return 0

    monkeypatch.setattr(power.os, "name", "nt")
    monkeypatch.setattr(power, "_set_thread_execution_state", fake_set_thread_execution_state)

    with power.prevent_system_sleep():
        pass

    assert calls == [power.ES_CONTINUOUS | power.ES_SYSTEM_REQUIRED]
