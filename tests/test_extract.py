from necro.extract import canonical, category, extract, is_dependent, split_elements
from necro.fetch import load_fixture, parse_claims_html

GOOGLE_STYLE = """
<section itemprop="claims"><div class="claims">
 <div class="claim"><div id="CLM-00001" num="00001" class="claim">
   <div class="claim-text">1. A method comprising:
     <div class="claim-text">frobbing a widget;</div>
     <div class="claim-text">and storing the widget in a database.</div></div></div></div>
 <div class="claim-dependent"><div id="CLM-00002" num="00002" class="claim">
   <div class="claim-text">2. The method of <claim-ref idref="CLM-00001">claim 1</claim-ref>, wherein the widget is blue.</div></div></div>
 <div class="claim"><div id="CLM-00003" num="00003" class="claim">
   <div class="claim-text">3. A system comprising: a frobber configured to frob a widget; and a database.</div></div></div>
</div></section>
"""


def test_parses_google_patents_html_without_double_counting_nested_divs():
    claims = parse_claims_html(GOOGLE_STYLE)
    assert [c.split(".")[0] for c in claims] == ["1", "2", "3"]
    assert "frobbing a widget" in claims[0]


def test_dependent_claims_are_dropped():
    chart = extract(parse_claims_html(GOOGLE_STYLE))
    assert [c.number for c in chart] == [1, 3]
    assert is_dependent("The method of claim 1, wherein x")
    assert not is_dependent("A method for claiming land, comprising: x")


def test_elements_split_on_semicolons_and_strip_conjunctions():
    _, parts = split_elements("A method comprising: a; b; and c.")
    assert parts == ["a", "b", "c"]


def test_crm_claim_splits_on_last_transition():
    pre, parts = split_elements(
        "A medium comprising instructions for a method, the method comprising: x; and y"
    )
    assert parts == ["x", "y"] and pre.endswith("the method")


def test_categories():
    assert category("A computer readable storage medium having a program") == "medium"
    assert category("A system for displaying a feed") == "system"
    assert category("A method for displaying a feed") == "method"


def test_us7669123_fixture_chart():
    chart = extract(load_fixture("US7669123B2"))
    assert [(c.number, c.category, len(c.elements)) for c in chart] == [
        (1, "method", 6), (16, "system", 7), (24, "medium", 6)]
    # claim 24 restates claim 1, so it is aliased, not implemented twice
    assert all(e.alias_of == f"C1.E{i}" for i, e in enumerate(chart[2].elements, 1))
    assert len(canonical(chart)) == 13
