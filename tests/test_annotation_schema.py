from oba_revieweval.annotation.schema import in_reference_set


def test_defect_from_other_reviewer_is_reference():
    assert in_reference_set("defect", "aaronbrethorst") is True


def test_style_is_not_reference():
    assert in_reference_set("style", "aaronbrethorst") is False


def test_own_comment_never_reference():
    assert in_reference_set("defect", "tejasva-vardhan") is False
    assert in_reference_set("design", "tejasva-vardhan") is False
