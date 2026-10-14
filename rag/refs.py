"""Find references to Act sections in free text.

Used on user questions ("what does s 14Q(2) allow?") to boost exact section matches,
and on Act and e-Tax guide text to record which sections a chunk cites.

Matched:  s 14, s. 14, S14Q, sec 37A, section 10(1)(a), sections 14 and 14A, ss 14, 14A and 14B
Ignored:  bare numbers ("14Q", "2019"), possessives ("company's 14 staff"), relative refs
          ("subsection (2)", "paragraph (a)"), guide paragraph numbers ("para 5.2").
Ranges ("sections 14 to 14B") give the two endpoints only; they are not expanded.
"""

import re
from dataclasses import dataclass

# A subsection/paragraph label: (1), (1A), (a), (za), (ii)
_LABEL = r"\((?:\d+[A-Za-z]{0,2}|[ivxl]{1,6}|[a-z]{1,3})\)"
# Section number + letter suffix. Suffixes are upper case ("14Q"); a single lower-case letter is
# accepted for typed queries ("14q"). Lower-case runs are words, even when glued on by PDF
# extraction ("43Vor 43X" is 43V).
_NUMBER = r"\d+(?:[A-Z]{1,3}|[a-z](?![a-z]))?"
_SECTION = rf"{_NUMBER}(?:\s?{_LABEL})*(?![A-Z0-9])"
# "s", "s.", "ss", "sec", "section(s)", any case, not preceded by a letter or apostrophe ("company's 14").
_TRIGGER = r"(?<![\w'’])(?i:sections?|secs?\.?|ss\.?|s\.?)\s*"

_REF_LIST = re.compile(rf"{_TRIGGER}(?P<list>{_SECTION}(?:\s*(?:,|&|and|or|to)\s*{_SECTION})*)")
_ONE_SECTION = re.compile(rf"(?P<number>{_NUMBER})(?P<labels>(?:\s?{_LABEL})*)")
# "... of the Goods and Services Tax Act 1993", "... of the Criminal Procedure Code 2010", "... of that Act".
_OF_ACT = re.compile(
    r"\s*of\s+(?:the\s+)?(?P<act>that Act|said Act|"
    r"(?:(?:[A-Z][\w'-]*|\([^)]{1,40}\)|and|of|&)\s+)*?(?:Act|Code)\b(?:\s+\d{4})?)"
)
_THIS_ACT = re.compile(r"^(?:Act|Income Tax Act(?: 1947)?)$")


@dataclass(frozen=True)
class SectionRef:
    section: str                    # "10", "14Q"
    labels: tuple[str, ...] = ()    # ("1", "a") for s 10(1)(a)
    act: str | None = None          # set when the text says "... of the <X> Act"

    @property
    def canonical(self) -> str:
        return self.section + "".join(f"({label})" for label in self.labels)

    @property
    def is_external(self) -> bool:
        """True when the reference is to a different Act (e.g. the Companies Act)."""
        return self.act is not None and not _THIS_ACT.match(self.act)


def _normalise_label(label: str) -> str:
    return label.upper() if label[0].isdigit() else label.lower()


def _parse_labels(labels: str) -> tuple[str, ...]:
    return tuple(_normalise_label(label) for label in re.findall(r"\(([^)]+)\)", labels))


def find_section_refs(text: str) -> list[SectionRef]:
    """All explicit section references in text, in order of first mention, without duplicates."""
    refs = []
    for match in _REF_LIST.finditer(text):
        of_act = _OF_ACT.match(text, match.end())
        act = of_act.group("act") if of_act else None
        for one in _ONE_SECTION.finditer(match.group("list")):
            refs.append(SectionRef(one.group("number").upper(), _parse_labels(one.group("labels")), act))
    return list(dict.fromkeys(refs))


def cited_sections(text: str, include_external: bool = False) -> list[str]:
    """Section numbers of this Act cited in text, e.g. ["4", "14Q"], in order of first mention."""
    numbers = [ref.section for ref in find_section_refs(text) if include_external or not ref.is_external]
    return list(dict.fromkeys(numbers))
