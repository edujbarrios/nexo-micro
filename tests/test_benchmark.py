from nexo_micro.benchmark import measure


def test_bytes_smaller_on_demo_corpus():
    result = measure(10, lambda s: len(s.encode('utf-8')))
    assert result["micro"] < result["json_compact"]
    assert result["messages"] == 40
    assert result["micro_with_primer"] == result["micro"] + result["primer_once"]
