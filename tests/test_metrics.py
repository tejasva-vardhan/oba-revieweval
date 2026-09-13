from oba_revieweval.evaluation.metrics import f1, precision, rate, recall


def test_precision_recall_f1():
    p = precision(6, 2)
    r = recall(6, 4)
    assert p == 0.75
    assert r == 0.6
    assert abs(f1(p, r) - 0.6666666667) < 1e-9


def test_empty_denominators_are_zero():
    assert precision(0, 0) == 0.0
    assert recall(0, 0) == 0.0
    assert f1(0.0, 0.0) == 0.0
    assert rate(1, 0) == 0.0


def test_rate():
    assert rate(3, 10) == 0.3
