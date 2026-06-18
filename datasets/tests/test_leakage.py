from curate.leakage_check import find_leaks


def test_detects_shared_ids():
    assert find_leaks({"a", "b", "c"}, {"c", "d"}) == {"c"}


def test_no_leak_when_disjoint():
    assert find_leaks({"a", "b"}, {"c", "d"}) == set()
