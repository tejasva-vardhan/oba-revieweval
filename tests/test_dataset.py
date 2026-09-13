from oba_revieweval.annotation.schema import HumanComment, in_reference_set
from oba_revieweval.dataset import is_bot_login, is_forbidden_gold_author


def test_bots_are_excluded():
    assert is_bot_login("coderabbitai[bot]")
    assert is_bot_login("dependabot")
    assert is_bot_login("CLAassistant")
    assert not is_bot_login("aaronbrethorst")


def test_author_comments_are_never_gold():
    assert is_forbidden_gold_author("tejasva-vardhan")
    comment = HumanComment(
        pr_id=702,
        comment_id=1,
        source="issue",
        author_login="tejasva-vardhan",
        is_pr_author=True,
        text="I think this is fine",
        class_="design",
        atomic_issue_id="a1",
        in_reference_set=False,
    )
    assert not in_reference_set(comment.class_, comment.author_login)


def test_style_is_not_reference():
    comment = HumanComment(
        pr_id=1,
        comment_id=2,
        source="inline",
        author_login="reviewer",
        is_pr_author=False,
        text="please rename",
        class_="style",
        atomic_issue_id="a2",
        in_reference_set=False,
    )
    assert not in_reference_set(comment.class_, comment.author_login)
