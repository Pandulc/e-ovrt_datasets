from curate.build_role_views import meets_min_per_class


def test_balance_pass():
    assert meets_min_per_class({"person": 500, "helmet": 400, "vest": 200, "bare_head": 300}, minimum=150)


def test_balance_fail_on_vest():
    assert not meets_min_per_class({"person": 500, "helmet": 400, "vest": 50, "bare_head": 300}, minimum=150)
