import sys

from oba_revieweval.dataset.corpus import load_recommended
from oba_revieweval.models.constants import repo_root
from scripts import run_models


def test_cli_refuses_full_corpus(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["run_models.py"])
    assert run_models.main() == 2
    err = capsys.readouterr().err
    assert "Refusing to run the full corpus" in err
    assert "1404" in err


def test_cli_refuses_explicit_33_without_approval(monkeypatch, capsys):
    numbers = [row["pr_number"] for row in load_recommended(repo_root() / "data" / "candidates" / "recommended_corpus.csv")]
    argv = ["run_models.py"]
    for number in numbers:
        argv.extend(["--pr", number])
    monkeypatch.setattr(sys, "argv", argv)
    assert run_models.main() == 2
    err = capsys.readouterr().err
    assert "before the 3-PR pilot is explicitly approved" in err
