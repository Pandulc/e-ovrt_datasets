from selection.quality_sample import sample_image_ids


def test_sample_is_deterministic_for_seed():
    ids = [f"img_{i}" for i in range(100)]
    a = sample_image_ids(ids, n=50, seed=42)
    b = sample_image_ids(ids, n=50, seed=42)
    assert a == b
    assert len(a) == 50


def test_sample_caps_at_population():
    ids = [f"img_{i}" for i in range(10)]
    assert len(sample_image_ids(ids, n=50, seed=42)) == 10
