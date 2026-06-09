"""The agent output contract — exactly what the Aletheia UI consumes.

Shape:
{
  answer: str,                       # prose with inline [F:<file>#<loc>] citation tokens
  evidence: [EvidenceItem, ...],     # one per cited source, each resolvable
  trace: [TraceStep, ...],           # maps + files the agent opened (the agent TRACE panel)
  validation: { ok: bool, reasons: [str] }
}
"""
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str


class EvidenceItem(BaseModel):
    """One resolvable source backing a claim in the answer.

    `loc` is the in-file locator that pairs with the inline token:
      - PDF page:  "p6"        -> [F:carter-case/family-court-case-file.pdf#p6]
      - CSV row:   "row-12"    -> [F:school-district/contracts/vendor-contracts.csv#row-12]
      - section:   "filing"    -> [F:.../doc.pdf#filing]
    """
    file: str
    loc: str
    snippet: str = ""

    def token(self) -> str:
        return f"[F:{self.file}#{self.loc}]"


class TraceStep(BaseModel):
    """One step the agent took: a map it read or a file it opened.

    `kind` is one of: "map" (read a data_structure.md), "open" (read/extracted a
    source file), "grep" (searched), "note" (a routing/guardrail decision).
    """
    kind: str
    detail: str


class Validation(BaseModel):
    ok: bool
    reasons: list[str] = Field(default_factory=list)


class AskResponse(BaseModel):
    question: str
    answer: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    trace: list[TraceStep] = Field(default_factory=list)
    validation: Validation
