import sys

from scripts import run_models


def test_cli_refuses_full_corpus(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["run_models.py"])
    assert run_models.main() == 2
    err = capsys.readouterr().err
    assert "Refusing to run the full corpus" in err
    assert "1404" in err
