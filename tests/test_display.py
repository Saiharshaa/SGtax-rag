from rag.display import RETRIEVAL_LABELS, excerpt, markdown_safe
from rag.retrieve import CONFIGS


def test_dollar_amounts_are_not_read_as_latex():
    assert markdown_safe("from $150,000 to $300,000") == r"from \$150,000 to \$300,000"


def test_excerpt_cuts_at_a_word_and_flattens_lines():
    assert excerpt("one two\nthree four", chars=12) == "one two …"
    assert excerpt("short\n text") == "short text"


def test_every_app_config_has_a_label():
    assert set(RETRIEVAL_LABELS) <= set(CONFIGS)
