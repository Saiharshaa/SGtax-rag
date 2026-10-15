from rag.bm25 import BM25Index, tokenize

DOCS = {
    "pre": "Deduction for expenses incurred before the first dollar of income from a trade",
    "group": "Group relief: a transferor company may transfer a qualifying deduction to a claimant company",
    "rr": "Renovation or refurbishment expenditure is deductible up to the expenditure cap",
    "s14r": "Income Tax Act 1947 > s 14R > (1)\n\nSubject to section 14X, a person who derives income",
}


def test_tokenize_stems_drops_stopwords_and_keeps_section_numbers():
    assert tokenize("The expenses incurred under s 14R(2)") == ["expens", "incur", "14r", "2"]


def test_query_term_in_one_document_ranks_it_first():
    index = BM25Index.build(list(DOCS), list(DOCS.values()))
    assert index.search("refurbishment cap")[0][0] == "rr"
    assert index.search("transfer losses to a claimant company")[0][0] == "group"


def test_section_number_in_query_matches_the_path():
    index = BM25Index.build(list(DOCS), list(DOCS.values()))
    assert index.search("what does s 14R say")[0][0] == "s14r"


def test_rare_terms_weigh_more_than_common_ones():
    index = BM25Index.build(list(DOCS), list(DOCS.values()))
    assert index.idf("refurbish") > index.idf("deduct")


def test_documents_without_query_terms_are_not_returned():
    index = BM25Index.build(list(DOCS), list(DOCS.values()))
    assert [id_ for id_, _ in index.search("refurbishment")] == ["rr"]
    assert index.search("the of and") == []


def test_save_and_load_round_trip(tmp_path):
    index = BM25Index.build(list(DOCS), list(DOCS.values()))
    index.save(tmp_path / "bm25.json")
    loaded = BM25Index.load(tmp_path / "bm25.json")
    assert loaded.search("company deduction", 4) == index.search("company deduction", 4)
