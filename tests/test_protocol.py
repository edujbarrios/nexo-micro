import pytest
from nexo_micro import Macro, MicroSession, ProtocolError, b36, from_b36, choose, receive


def test_roundtrip():
    a, b = MicroSession(), MicroSession()
    messages = [
        {"intent": "status", "task": 42},
        {"intent": "progress", "task": 42, "percent": 80},
        {"intent": "complete", "task": 42, "critical": 3},
        {"intent": "error", "task": 42, "code": 4},
        {"intent": "next", "task": 42},
        {"intent": "complete", "task": 999, "critical": 0},
    ]
    expected_wire = ["@16|?", "~28", "!3", "x4", ">", "@RR|!0"]
    for message, wire in zip(messages, expected_wire):
        assert a.encode(message) == wire
        assert b.decode(wire) == message


def test_binder_only():
    b = MicroSession()
    assert b.decode("@16") == {"intent": "bind", "task": 42}
    assert b.decode("!3") == {"intent": "complete", "task": 42, "critical": 3}


def test_shared_macro():
    macros = (Macro("review_diff", "A", ("files", "critical")),)
    a, b = MicroSession(macros=macros), MicroSession(macros=macros)
    message = {"task": 42, "intent": "macro", "name": "review_diff", "args": {"files": 7, "critical": 3}}
    wire = a.encode(message)
    assert wire == "@16|^A.7.3"
    assert b.decode(wire) == message
    assert a.fingerprint == b.fingerprint


def test_atomic_decode_on_failure():
    s = MicroSession(active_task=10)
    for wire in ["@16|~ZZ", "@16|!", "@16|x000", "@16|~2T", "@16|^A", "@16|?|"]:
        with pytest.raises(ProtocolError):
            s.decode(wire)
        assert s.active_task == 10


def test_strict_types_and_overflow():
    s = MicroSession()
    for msg in [
        {"task": True, "intent": "status"},
        {"task": 1, "intent": "progress", "percent": 101},
        {"task": 1, "intent": "complete", "critical": -1},
        {"task": 1, "intent": "complete", "critical": "3"},
        {"task": 1, "intent": "status", "extra": "ignored?"},
    ]:
        with pytest.raises(ProtocolError):
            s.encode(msg)
        assert s.active_task is None
    with pytest.raises(ProtocolError):
        from_b36("000")
    with pytest.raises(ProtocolError):
        from_b36("ZZZZZZZZZZZZZ")


def test_base36():
    for value in [0, 7, 10, 35, 36, 42, 999, 2**53-1]:
        assert from_b36(b36(value)) == value


def test_adaptive_selection():
    msg = {"intent": "complete", "task": 42, "critical": 3}
    a, b = MicroSession(), MicroSession()
    pick = choose(a, msg, lambda s: len(s))
    assert pick.format == "micro/1"
    assert receive(b, pick) == msg
    c, d = MicroSession(), MicroSession()
    pick2 = choose(c, msg, lambda s: 100 if s.startswith("@") else 1)
    assert pick2.format == "json"
    assert receive(d, pick2) == msg
    assert c.active_task == d.active_task


def test_reject_unsynced_dictionary():
    a = MicroSession(macros=(Macro("review", "A", ("issues",)),))
    b = MicroSession(macros=(Macro("search", "A", ("issues",)),))
    assert a.fingerprint != b.fingerprint
    # In actual use handshake must reject mismatched fingerprint!
    with pytest.raises(ProtocolError):
        MicroSession().decode("@16|^A.3")


def test_missing_task_expands_using_context():
    s = MicroSession(active_task=42)
    assert s.encode({"intent": "complete", "critical": 3}) == "!3"


def test_train_macro_dictionary():
    from nexo_micro import train_macros
    schemas = {"review": ("files", "critical"), "deploy": ("environment",)}
    events = [
        {"name": "review", "args": {"files": 4, "critical": 1}},
        {"name": "review", "args": {"files": 8, "critical": 2}},
        {"name": "deploy", "args": {"environment": 3}},
    ]
    macros = train_macros(schemas, events, lambda text: len(text))
    assert len(macros) == 2 and len({m.code for m in macros}) == 2
    a, b = MicroSession(macros=macros), MicroSession(macros=macros)
    msg = {"task": 1, "intent": "macro", "name": "review", "args": {"files": 4, "critical": 1}}
    assert b.decode(a.encode(msg)) == msg


def test_json_frame_invalid_rejected_atomically():
    s = MicroSession(active_task=42)
    with pytest.raises(ProtocolError):
        receive(s, '{"intent":"complete","task":43,"critical":-1}', format="json")
    assert s.active_task == 42


def test_reject_duplicate_json_keys():
    session = MicroSession()
    with pytest.raises(ProtocolError, match="duplicate JSON keys"):
        receive(session, '{"task":42,"task":43,"intent":"status"}', format="json")
    assert session.active_task is None


def test_macro_registry_validation():
    for macros in [
        (Macro("review", "A"), Macro("review", "B")),
        (Macro("review", "A"), Macro("search", "A")),
    ]:
        with pytest.raises(ProtocolError):
            MicroSession(macros=macros)
