import inspect

from oba_revieweval.models import context as context_mod
from oba_revieweval.models import preflight as preflight_mod
from oba_revieweval.models import runner as runner_mod
from oba_revieweval.models.context import load_pr_bundle
from oba_revieweval.models.preflight import approx_tokens, leak_snippets, prompt_leaks, provisional_cost_usd
from oba_revieweval.models.runner import analyze_pr, run_pilot


def test_approx_tokens_uses_documented_heuristic():
    assert approx_tokens(0) == 20
    assert approx_tokens(4) == 21


def test_provisional_cost_matches_config_rates():
    cost = provisional_cost_usd(
        1_000_000,
        1_000_000,
        {"input_usd_per_million": 2.5, "output_usd_per_million": 10.0},
    )
    assert cost == 12.5


def test_leak_snippets_ignore_text_already_in_the_diff():
    snippets = leak_snippets(
        ["this unique review sentence is definitely long enough", "package maglev"],
        "package maglev\nfunc F() {}",
    )
    assert snippets == ["this unique review sentence is definitely long enough"]
    assert prompt_leaks("title\ndiff only", snippets) == []
    assert prompt_leaks("title\nthis unique review sentence is definitely long enough", snippets)


def test_preflight_does_not_import_openai_client():
    source = inspect.getsource(preflight_mod)
    assert "OpenAIChatClient" not in source
    assert "urllib.request" not in source
    assert "api.openai.com" not in source


def test_bundle_loader_does_not_open_reviews_or_gold():
    source = inspect.getsource(load_pr_bundle)
    assert "metadata.json" in source
    assert "diff.patch" in source
    assert "files.json" in source
    assert "comments.json" not in source
    assert "reviews.json" not in source
    assert "human_review" not in source
    assert "lint_findings" not in source
    assert "GITHUB_TOKEN" not in inspect.getsource(context_mod)
    assert "OPENAI_API_KEY" not in inspect.getsource(context_mod)


def test_runner_does_not_load_forbidden_inputs():
    for source in (inspect.getsource(analyze_pr), inspect.getsource(run_pilot), inspect.getsource(runner_mod)):
        assert "comments.json" not in source
        assert "reviews.json" not in source
        assert "human_review" not in source
        assert "lint_findings" not in source
        assert "GITHUB_TOKEN" not in source
