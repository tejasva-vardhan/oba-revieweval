from oba_revieweval.dataset.github import GitHubClient
from oba_revieweval.dataset.search import consider_additional, search_issue_numbers
from tests.fixtures.github.pr_sample import FakeOpener, ROUTES, file_payload, pr_payload


def test_search_issue_numbers_reads_items():
    routes = {
        "/search/issues": {
            "total_count": 1,
            "items": [{"number": 457}, {"number": 702}],
        }
    }
    client = GitHubClient(token=None, opener=FakeOpener(routes))
    assert search_issue_numbers(client, "race") == [457, 702]


def test_consider_additional_rejects_title_hit_without_human_review():
    routes = dict(ROUTES)
    routes["/repos/OneBusAway/maglev/pulls/457"] = pr_payload(
        457, title="Fix data race", author="tejasva-vardhan"
    )
    routes["/repos/OneBusAway/maglev/pulls/457/files"] = [file_payload("handler.go")]
    routes["/repos/OneBusAway/maglev/pulls/457/reviews"] = []
    routes["/repos/OneBusAway/maglev/pulls/457/comments"] = []
    routes["/repos/OneBusAway/maglev/issues/457/comments"] = []
    client = GitHubClient(token=None, opener=FakeOpener(routes))
    rows = consider_additional(client, [457], exclude={702}, query="race")
    assert rows[0]["decision"] == "rejected"
    assert rows[0]["eligible_for_primary_gold"] is False
