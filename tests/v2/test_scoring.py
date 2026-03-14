from __future__ import annotations

import math

from herald.scoring import article_score_base, effective_source_count, story_score


def test_article_baseline():
    assert article_score_base(source_weight=0.3, points=0,
                               keyword_density=0.0, is_release=False) == 0.3


def test_article_points_cap():
    score = article_score_base(0.2, points=1500, keyword_density=0.0, is_release=False)
    assert score == 0.2 + 3.0


def test_article_points_partial():
    score = article_score_base(0.2, points=250, keyword_density=0.0, is_release=False)
    assert score == 0.2 + 0.5


def test_article_release_boost():
    score = article_score_base(0.2, 0, 0.0, is_release=True)
    assert score == 0.2 + 0.2


def test_article_density():
    score = article_score_base(0.2, 0, keyword_density=0.5, is_release=False)
    assert score == 0.2 + 0.5 * 0.2


def test_story_single_source():
    assert story_score(max_article_score=1.0, source_count=1, has_recent=False) == 1.0


def test_story_multi_source():
    expected = 1.0 + math.log(3) * 0.3
    assert abs(story_score(1.0, 3, False) - expected) < 0.001


def test_story_momentum():
    expected = 1.0 + 0.0 + 0.2
    assert story_score(1.0, 1, has_recent=True) == expected


# -- effective_source_count --------------------------------------------------

def test_effective_source_count_no_mirrors():
    data = [("hn", "https://example.com/foo"), ("reddit", "https://reddit.com/bar")]
    assert effective_source_count(data) == 2


def test_effective_source_count_arxiv_mirror_collapsed():
    """arxiv.org + tldr.takara.ai with same paper ID count as 1 source."""
    data = [
        ("arxiv", "https://arxiv.org/abs/2603.12345"),
        ("hf_papers", "https://tldr.takara.ai/p/2603.12345"),
    ]
    assert effective_source_count(data) == 1


def test_effective_source_count_different_papers_not_collapsed():
    """Different arxiv papers from the same mirror domain count separately."""
    data = [
        ("arxiv", "https://arxiv.org/abs/2603.11111"),
        ("hf_papers", "https://tldr.takara.ai/p/2603.22222"),
    ]
    assert effective_source_count(data) == 2


def test_effective_source_count_mixed_mirror_and_regular():
    """Mirror pair + independent source = 2 effective sources."""
    data = [
        ("arxiv", "https://arxiv.org/abs/2603.12345"),
        ("hf_papers", "https://tldr.takara.ai/p/2603.12345"),
        ("hn", "https://news.ycombinator.com/item?id=99999"),
    ]
    assert effective_source_count(data) == 2


def test_effective_source_count_empty():
    assert effective_source_count([]) == 1


def test_effective_source_count_single():
    data = [("arxiv", "https://arxiv.org/abs/2603.12345")]
    assert effective_source_count(data) == 1
