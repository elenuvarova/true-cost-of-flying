"""Track slimming for the web export (scripts/export_web_data.py)."""
from scripts.export_web_data import slim_feature


def _feature(coords, props):
    return {"type": "Feature", "geometry": {"type": "LineString", "coordinates": coords}, "properties": props}


def test_coordinates_keep_altitude_rounded_to_10_m():
    f = slim_feature(_feature([[-115.30643516, 34.06114982, 7559.152472]], {"ef": 0.0, "ef_share": 0.0}))
    assert f["geometry"]["coordinates"] == [[-115.30644, 34.06115, 7560.0]]


def test_missing_altitude_becomes_zero_not_a_short_coordinate():
    f = slim_feature(_feature([[-115.3, 34.0]], {"ef": 0.0, "ef_share": 0.0}))
    assert f["geometry"]["coordinates"] == [[-115.3, 34.0, 0.0]]


def test_signed_ef_is_kept_in_terajoules():
    # 1 TJ = 1e12 J, so -4.4761e13 J is -44.761 TJ.
    f = slim_feature(_feature([[0.0, 0.0, 0.0]], {"ef": -4.4761e13, "ef_share": -0.14}))
    assert f["properties"]["ef_tj"] == -44.761
    assert f["properties"]["ef_share"] == -0.14


def test_rounding_never_zeroes_the_smallest_real_segment():
    # The smallest non-zero segment in the committed set is 2.389e8 J. It must
    # survive the export, or a non-zero segment count the story rests on changes.
    f = slim_feature(_feature([[0.0, 0.0, 0.0]], {"ef": 2.389e8, "ef_share": 0.0001}))
    assert f["properties"]["ef_tj"] != 0.0


def test_absent_properties_default_to_zero():
    f = slim_feature(_feature([[0.0, 0.0, 0.0]], {}))
    assert f["properties"] == {"ef_share": 0.0, "ef_tj": 0.0}


def test_non_linestring_geometry_is_passed_through_untouched():
    f = slim_feature({"type": "Feature", "geometry": {"type": "Point", "coordinates": [1.0, 2.0]}, "properties": {}})
    assert f["geometry"]["coordinates"] == [1.0, 2.0]
