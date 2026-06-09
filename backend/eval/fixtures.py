"""The golden eval set (Layer A of 03) — the acceptance bar as data.

Each fixture is the golden bar for one question, encoding:
  - required_facts:    substrings that MUST appear in the answer (figures/findings)
  - required_citations: (file, loc_pattern) pairs — at least one cited token must match each
  - must_open:         files the trace MUST show opened (Layer C / T1)
  - must_not_open:     files the trace must NOT open (the leak guard / T2)
  - forbidden:         substrings that must be ABSENT (fabrications / cross-domain leaks)
  - behavior:          a tag the gates interpret ("honest_refusal", "conflict", "pivot")

Facts re-verified against the real data at asOfDate = 2026-06-09 (see 02/03).
"""
from dataclasses import dataclass, field


@dataclass
class Fixture:
    id: str
    question: str
    lang: str  # "en" | "he"
    required_facts: list[str] = field(default_factory=list)
    # each inner list is a set of acceptable ALTERNATES — at least one must appear (e.g. a date that
    # may be written "2026-07-09" or "7/9/2026"). Avoids brittle single-form assertions.
    required_facts_any: list[list[str]] = field(default_factory=list)
    required_citations: list[tuple[str, str]] = field(default_factory=list)  # (file_substr, loc_regex)
    must_open: list[str] = field(default_factory=list)
    must_not_open: list[str] = field(default_factory=list)
    forbidden: list[str] = field(default_factory=list)
    behavior: list[str] = field(default_factory=list)
    judge_rubric: str = ""


# Cross-domain stop-lists (Layer F): a school-operations answer must contain zero Carter tokens,
# and vice versa. Lower-cased substring match.
CARTER_TOKENS = ["child support", "custody", "joni", "michel", "final judgment", "divorce", "home sale"]
SCHOOL_TOKENS = ["contract id", "annual cost", "maintenance ticket", "vendor spend", "labor cost"]
# Tokens that would only appear if the agent leaked from a DROPPED source (Layer F T4) — payroll
# and student/enrollment data were quarantined; no answer should surface them.
DROPPED_TOKENS = ["net_pay", "base_salary", "pay_period", "enrollment_date", "course_code", "ip_address"]

# The dropped sources must NEVER be opened by any answer (T4). Any fixture's must_not_open includes
# these so a leak from a quarantined file reds the trace gate.
DROPPED_FILES = [
    "school-operations/_dropped/enrollment.csv",
    "school-operations/_dropped/payroll_v1.csv",
    "school-operations/_dropped/payroll_v2.csv",
    "school-operations/_dropped/invoice_volume.csv",
    "school-operations/_dropped/people.csv",
]

CONTRACTS = "school-operations/contracts.csv"
MAINTENANCE = "school-operations/maintenance.csv"
COURT = "carter-case/family-court-case-file.pdf"
STORY = "carter-case/case-story.pdf"


FIXTURES: list[Fixture] = [
    Fixture(
        id="F-G1",
        question="What contracts expire in the next 90 days and what penalties are defined in those contracts?",
        lang="en",
        required_facts=["38", "18,924,883.79"],
        required_citations=[(CONTRACTS, r"row=.+")],
        must_open=[CONTRACTS],
        must_not_open=[COURT, STORY],
        forbidden=CARTER_TOKENS + ["early-termination fee", "penalty of $", "typically include"],
        behavior=["honest_refusal"],  # penalties not available
        judge_rubric=(
            "The answer must state exactly 38 contracts expiring in the 90-day window with combined "
            "annual cost $18,924,883.79, list expiring contracts cited by (Vendor, End Date), and "
            "honestly state that penalty/termination terms are NOT AVAILABLE because contracts.csv "
            "has no penalty column and no contract documents exist — fabricating no penalty value and "
            "pulling in no Carter-case content."
        ),
    ),
    Fixture(
        id="F-G2",
        question="What was the final child support amount, and who got primary residence in the Carter case?",
        lang="en",
        required_facts=["1,285", "Joni"],
        required_citations=[(COURT, r"p\d+")],
        must_open=[COURT],
        must_not_open=[CONTRACTS, MAINTENANCE],
        forbidden=["several", "some child support"],
        behavior=[],
        judge_rubric=(
            "The answer must state child support of $1,285/month and primary residence to Joni Carter, "
            "cited to a printed PAGE label of family-court-case-file.pdf (the Final Judgment, Page 24) "
            "— not vague, not cited to the story PDF."
        ),
    ),
    Fixture(
        id="F-G3",
        question="Which customers have overdue payments and what does the agreement say about service suspension?",
        lang="en",
        required_facts=["40,597"],
        required_citations=[(MAINTENANCE, r".+")],
        must_open=[MAINTENANCE],
        must_not_open=[COURT, STORY],
        # Note: do NOT forbid "overdue list" — an honest refusal legitimately says "I won't
        # fabricate an overdue list". Forbid only a FABRICATED overdue figure/name.
        forbidden=CARTER_TOKENS + ["$1,733", "oyoba owes", "voolith owes"],
        behavior=["honest_refusal", "pivot"],
        judge_rubric=(
            "The answer must HONESTLY REFUSE the overdue/suspension question — citing that "
            "maintenance.csv has no payment-status/due-date field and the vendors are providers we "
            "pay (not customers who owe us) and no service-agreement document exists — fabricating no "
            "overdue list, then PIVOT to the real total maintenance spend $40,597.00 over 750 tickets "
            "computed and cited to maintenance.csv."
        ),
    ),
    Fixture(
        id="F-G4",
        question="When did Joni Carter file for divorce?",
        lang="en",
        required_facts=[],
        required_facts_any=[
            ["10 february 2026", "february 10, 2026", "feb 10"],
            ["3 february 2026", "february 3, 2026", "feb 3"],
        ],
        # Cover (Feb 10) cited to the court-file Page 1; Feb 3 cited to the story PDF — the
        # unambiguous, resolvable pair. (The court-file body's Feb-3 page has no printed PAGE label,
        # so it is NOT a required citation; the agent must not cite a non-existent page.)
        required_citations=[(COURT, r"p1\b|p1$"), (STORY, r".+")],
        must_open=[COURT, STORY],
        must_not_open=[CONTRACTS, MAINTENANCE],
        forbidden=[],
        behavior=["conflict"],
        judge_rubric=(
            "The answer must SURFACE THE CONFLICT: the cover sheet says 10 February 2026 (cited to the "
            "court file cover, Page 1) while the grounds narrative and the case story say February 3, "
            "2026 (the story PDF cited) — presenting BOTH with both citations and not silently picking "
            "one."
        ),
    ),
    Fixture(
        id="F-single",
        # the expiry date is the same fact whether written 2026-07-09 or 7/9/2026 — the alternates
        # are encoded in required_facts_any (see gates.gate_required_facts).
        question="When does the Skalith Project Manager contract expire and what is its penalty?",
        lang="en",
        required_facts=["25,629.50"],
        required_facts_any=[["2026-07-09", "7/9/2026", "July 9, 2026"]],
        required_citations=[(CONTRACTS, r"row=Skalith\|.+")],
        must_open=[CONTRACTS],
        must_not_open=[COURT, STORY],
        forbidden=CARTER_TOKENS + ["penalty of $", "termination fee"],
        behavior=["honest_refusal"],
        judge_rubric=(
            "The answer must state the Skalith (Project Manager) contract expires 2026-07-09 with "
            "annual cost $25,629.50 cited to its contracts.csv row, and that penalty terms are not "
            "available — fabricating no penalty and pulling in no Carter content."
        ),
    ),
    # ── Hebrew twins — identical facts + citations + honesty ───────────────────
    Fixture(
        id="F-G1-HE",
        question="אילו חוזים יפוגו ב-90 הימים הקרובים ומהם הקנסות המוגדרים באותם חוזים?",
        lang="he",
        required_facts=["38", "18,924,883.79"],
        required_citations=[(CONTRACTS, r"row=.+")],
        must_open=[CONTRACTS],
        must_not_open=[COURT, STORY],
        forbidden=CARTER_TOKENS,
        behavior=["honest_refusal"],
        judge_rubric="Hebrew twin of F-G1 — identical 38 / $18,924,883.79 / honest penalty refusal, in Hebrew.",
    ),
    Fixture(
        id="F-G2-HE",
        question="מה היה סכום המזונות הסופי ולמי ניתנה המשמורת העיקרית בתיק קרטר?",
        lang="he",
        required_facts=["1,285"],
        required_citations=[(COURT, r"p\d+")],
        must_open=[COURT],
        must_not_open=[CONTRACTS, MAINTENANCE],
        behavior=[],
        judge_rubric="Hebrew twin of F-G2 — $1,285 + Joni Carter cited to Page 24, in Hebrew.",
    ),
    Fixture(
        id="F-G3-HE",
        question="אילו לקוחות מאחרים בתשלומים ומה אומר ההסכם על השעיית שירות?",
        lang="he",
        required_facts=["40,597"],
        required_citations=[(MAINTENANCE, r".+")],
        must_open=[MAINTENANCE],
        must_not_open=[COURT, STORY],
        forbidden=CARTER_TOKENS,
        behavior=["honest_refusal", "pivot"],
        judge_rubric="Hebrew twin of F-G3 — honest refusal + $40,597 pivot, in Hebrew.",
    ),
    Fixture(
        id="F-G4-HE",
        question="מתי ג'וני קרטר הגישה לגירושין?",
        lang="he",
        required_facts=["10 February 2026", "February 3, 2026"],
        required_citations=[(COURT, r".+"), (STORY, r".+")],
        must_open=[COURT, STORY],
        must_not_open=[CONTRACTS, MAINTENANCE],
        behavior=["conflict"],
        judge_rubric="Hebrew twin of F-G4 — both filing dates surfaced with both citations, in Hebrew.",
    ),
]
