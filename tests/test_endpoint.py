import pytest

from nexo_micro import Frame, HandshakeError, Hello, Macro, MicroEndpoint, ProtocolError


def pair(*, token_count=None):
    a = MicroEndpoint(token_count=token_count)
    b = MicroEndpoint()
    a.connect(b.hello())
    b.connect(a.hello())
    return a, b


def test_first_and_subsequent_messages():
    a, b = pair()
    samples = [
        {"task": 42, "intent": "status"},
        {"task": 42, "intent": "complete", "critical": 3},
        {"task": 43, "intent": "progress", "percent": 100},
    ]
    for idx, msg in enumerate(samples):
        frame = a.send(msg)
        assert frame.sequence == idx
        assert b.receive(Frame.from_dict(frame.to_dict())) == msg
    assert a.send({"task": 43, "intent": "status"}).payload == "?"


def test_full_duplex_separate_contexts():
    a, b = pair()
    assert b.receive(a.send({"task": 12, "intent": "status"})) == {"task": 12, "intent": "status"}
    assert a.receive(b.send({"task": 88, "intent": "status"})) == {"task": 88, "intent": "status"}
    assert a.send({"task": 12, "intent": "next"}).payload == ">"
    assert b.send({"task": 88, "intent": "next"}).payload == ">"


def test_replay_and_gaps_are_rejected():
    a, b = pair()
    first = a.send({"intent": "status", "task": 42})
    second = a.send({"intent": "status", "task": 42})
    with pytest.raises(ProtocolError, match="out-of-order"):
        b.receive(second)
    assert b.receive(first) == {"intent": "status", "task": 42}
    with pytest.raises(ProtocolError, match="out-of-order"):
        b.receive(first)
    assert b.receive(second) == {"intent": "status", "task": 42}


def test_invalid_frame_does_not_change_receive_state():
    a, b = pair()
    valid = a.send({"intent": "status", "task": 42})
    broken = Frame(valid.session_id, valid.sequence, "micro/1", "@16|~ZZ")
    with pytest.raises(ProtocolError):
        b.receive(broken)
    assert b.receive(valid)["task"] == 42


def test_invalid_payload_does_not_advance_sender():
    a, b = pair()
    with pytest.raises(ProtocolError):
        a.send({"task": 42, "intent": "complete", "critical": -1})
    frame = a.send({"task": 42, "intent": "status"})
    assert frame.sequence == 0
    assert b.receive(frame)["intent"] == "status"


def test_mismatch_and_handshake_required():
    a = MicroEndpoint(macros=(Macro("review", "A"),))
    b = MicroEndpoint(macros=(Macro("search", "A"),))
    with pytest.raises(HandshakeError, match="mismatch"):
        a.connect(b.hello())
    with pytest.raises(HandshakeError):
        a.send({"task": 1, "intent": "status"})
    with pytest.raises(HandshakeError):
        b.receive(Frame(a.hello().session_id, 0, "micro/1", "@1|?"))
    with pytest.raises(HandshakeError):
        a.connect(a.hello())


def test_wrong_peer_and_repeat_connection():
    a, b = pair()
    outsider = MicroEndpoint()
    with pytest.raises(ProtocolError, match="another session"):
        b.receive(Frame(outsider.hello().session_id, 0, "micro/1", "@1|?"))
    with pytest.raises(HandshakeError, match="already connected"):
        a.connect(b.hello())


def test_token_selection_json_path():
    a, b = pair(token_count=lambda text: 100 if text.startswith("@") else 1)
    msg = {"task": 42, "intent": "complete", "critical": 3}
    frame = a.send(msg)
    assert frame.format == "json"
    assert b.receive(frame) == msg
    assert b.receive(a.send({"task": 42, "intent": "status"})) == {"task": 42, "intent": "status"}


def test_frame_validation_and_untrusted_input():
    a, _ = pair()
    with pytest.raises(ProtocolError):
        Frame.from_dict({"session_id": a.hello().session_id, "sequence": True, "format": "json", "payload": "{}"})
    with pytest.raises(ProtocolError):
        Frame(a.hello().session_id, 0, "json", "x" * 16385)
    with pytest.raises(HandshakeError):
        Hello.from_dict({"protocol": "micro/2", "dictionary": a.hello().dictionary, "session_id": a.hello().session_id})
    with pytest.raises(HandshakeError):
        Hello.from_dict({"unexpected": "x"})


def test_bad_counter_is_atomic():
    a, b = pair(token_count=lambda x: True)
    with pytest.raises(ValueError):
        a.send({"task": 1, "intent": "status"})
    a.token_count = lambda x: len(x)
    assert b.receive(a.send({"task": 1, "intent": "status"}))["task"] == 1


def test_bad_types_are_protocol_errors():
    a, _ = pair()
    with pytest.raises(HandshakeError):
        Hello("micro/1", 123, a.hello().session_id)
    with pytest.raises(ProtocolError):
        Frame(42, 0, "micro/1", "?")


def test_randomized_roundtrips():
    import random
    random.seed(17)
    a, b = pair()
    for _ in range(250):
        task = random.randrange(2**20)
        kind = random.choice(("status", "progress", "complete", "error", "next"))
        message = {"intent": kind, "task": task}
        if kind == "progress":
            message["percent"] = random.randrange(101)
        elif kind == "complete":
            message["critical"] = random.randrange(1000)
        elif kind == "error":
            message["code"] = random.randrange(1000)
        assert b.receive(a.send(message)) == message
