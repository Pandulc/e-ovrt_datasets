from bench.build_person_gt import build_violation_records, build_person_gt_records


def test_violations_come_only_from_explicit_negatives():
    anns = [
        {"category_name": "bare_head", "bbox_xyxy": [0,0,10,10], "source_class": "NO-Hardhat"},
        {"category_name": "helmet",    "bbox_xyxy": [5,5,15,15], "source_class": "Hardhat"},
        {"category_name": "vest",      "bbox_xyxy": [0,0,20,40], "source_class": "Safety Vest"},
    ]
    recs = build_violation_records(anns, negatives={"NO-Hardhat":"no_helmet"})
    assert len(recs) == 1
    assert recs[0]["flag"] == "no_helmet"
    assert recs[0]["condition"] == "CR-01"


def test_person_gt_records_assigns_has_helmet_false():
    # Person at [0,0,100,200]; head_region = [0,0,100,67]
    # bare_head center=(50,32) falls inside head_region → has_helmet=False
    person_anns = [{"bbox_xyxy": [0, 0, 100, 200]}]
    violation_recs = [{"bbox": [10, 5, 90, 60], "flag": "no_helmet", "condition": "CR-01"}]
    result = build_person_gt_records(person_anns, violation_recs)
    assert len(result) == 1
    assert result[0]["has_helmet"] is False
    assert result[0]["has_vest"] is True


def test_person_gt_records_has_helmet_true_when_center_outside():
    # Person at [200,0,300,200]; bare_head center=(5,5) outside head_region → True
    person_anns = [{"bbox_xyxy": [200, 0, 300, 200]}]
    violation_recs = [{"bbox": [0, 0, 10, 10], "flag": "no_helmet", "condition": "CR-01"}]
    result = build_person_gt_records(person_anns, violation_recs)
    assert len(result) == 1
    assert result[0]["has_helmet"] is True


def test_person_gt_records_assigns_has_vest_false():
    # Person at [0,0,100,200]; vest violation center=(50,125) inside person bbox → False
    person_anns = [{"bbox_xyxy": [0, 0, 100, 200]}]
    violation_recs = [{"bbox": [5, 60, 95, 190], "flag": "no_vest", "condition": "CR-02"}]
    result = build_person_gt_records(person_anns, violation_recs)
    assert len(result) == 1
    assert result[0]["has_vest"] is False
    assert result[0]["has_helmet"] is True


def test_person_gt_no_violations_means_all_compliant():
    person_anns = [
        {"bbox_xyxy": [0, 0, 100, 200]},
        {"bbox_xyxy": [200, 0, 300, 200]},
    ]
    result = build_person_gt_records(person_anns, violation_recs=[])
    assert len(result) == 2
    assert all(r["has_helmet"] is True for r in result)
    assert all(r["has_vest"] is True for r in result)
