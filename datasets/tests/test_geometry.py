from bench.geometry import iou, head_region, center_in_bbox

def test_iou_identical_is_one():
    assert iou([0,0,10,10],[0,0,10,10]) == 1.0

def test_iou_disjoint_is_zero():
    assert iou([0,0,10,10],[20,20,30,30]) == 0.0

def test_head_region_is_top_third():
    x0,y0,x1,y1 = head_region([0,0,10,30])
    assert (y0, y1) == (0, 10)

def test_center_in_bbox_true_when_inside():
    assert center_in_bbox([40,40,60,60], [0,0,100,100]) is True

def test_center_in_bbox_false_when_outside():
    assert center_in_bbox([0,0,10,10], [200,200,300,300]) is False
