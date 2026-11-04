"""Tiered element alignment: exact -> lexical -> semantic -> LLM fallback.

Every node of both models ends up in exactly one :class:`Pair`.  A pair is
labelled ``identical``, ``synonym``, ``meaning_changed`` or ``unmatched`` and
carries a confidence value.  Ambiguous candidates are marked ``needs_review``
when no LLM adjudicator is available.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from .model import Node, ProcessModel, kind_family


# ---------------------------------------------------------------------------
# Text normalisation and similarity
# ---------------------------------------------------------------------------
_STOPWORDS = {
    "a", "an", "the", "of", "to", "for", "and", "or", "in", "on", "at", "by",
    "with", "from", "into", "is", "are", "be", "it", "this", "that", "their",
    "its", "his", "her", "as", "then", "than", "if", "when", "which", "has",
    "have", "do", "does", "done",
}

# Lightweight canonicalisation acting as an offline stand-in for embeddings.
_SYNONYMS = {
    "save": "store", "saves": "store", "saved": "store", "saving": "store",
    "store": "store", "stores": "store", "stored": "store", "record": "store",
    "persist": "store", "keep": "store",
    "display": "show", "displays": "show", "displayed": "show", "show": "show",
    "shows": "show", "view": "show", "views": "show", "see": "show",
    "sees": "show", "render": "show", "renders": "show",
    "search": "find", "searches": "find", "searched": "find", "find": "find",
    "finds": "find", "look": "find", "looks": "find", "looking": "find",
    "query": "find", "queries": "find", "retrieve": "find", "retrieves": "find",
    "enter": "input", "enters": "input", "entered": "input", "input": "input",
    "inputs": "input", "fill": "input", "fills": "input", "type": "input",
    "select": "choose", "selects": "choose", "selected": "choose",
    "choose": "choose", "chooses": "choose", "click": "choose",
    "clicks": "choose", "press": "choose", "pick": "choose",
    "create": "create", "creates": "create", "add": "create", "adds": "create",
    "insert": "create", "inserts": "create",
    "update": "change", "updates": "change", "modify": "change",
    "modifies": "change", "edit": "change", "change": "change",
    "remove": "delete", "removes": "delete", "delete": "delete",
    "deletes": "delete",
    "wants": "want", "wishes": "want", "needs": "want",
    "transaction": "transaction", "transactions": "transaction",
    "payment": "payment", "payments": "payment", "pay": "payment",
    "down": "deposit", "deposit": "deposit", "deposits": "deposit",
    "print": "print", "prints": "print", "printing": "print",
    "generate": "generate", "generates": "generate", "make": "make",
    "makes": "make", "perform": "make", "performs": "make",
}

_PHRASES = {
    "down payment": "deposit",
    "medical record id": "medical record",
    "medical record number": "medical record",
    "register number": "registration number",
    "registration number": "registration number",
    "general patient": "general patient",
    "corporate patient": "corporate patient",
}

#: Tokens from the same group are mutually exclusive business alternatives.
#: A label pair that swaps one for another is a meaning change, not a rename.
_CONTRAST_GROUPS = [
    {"general", "corporate"},
    {"old", "new"},
    {"inpatient", "outpatient"},
    {"cashier", "warehouse"},
    {"daily", "monthly", "yearly"},
    {"principal", "mandatory", "voluntary"},
    {"cash", "credit"},
    {"local", "foreign"},
    {"male", "female"},
    {"before", "after"},
]


def basic_stem(token: str) -> str:
    """Very small English stemmer sufficient for process labels."""
    if token.endswith("ies") and len(token) > 4:
        token = token[:-3] + "y"
    elif token.endswith("sses"):
        token = token[:-2]
    elif token.endswith("es") and len(token) > 4:
        token = token[:-2]
    elif token.endswith("s") and not token.endswith("ss") and len(token) > 3:
        token = token[:-1]
    if token.endswith("ing") and len(token) > 6:
        token = token[:-3]
    return token


def normalize_label(text: str) -> str:
    """Lowercase, strip punctuation and collapse whitespace."""
    text = (text or "").lower().replace("&", " and ")
    text = text.replace("'s ", " ").replace("'", "")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def canonical_tokens(text: str) -> set[str]:
    normalized = normalize_label(text)
    for phrase, replacement in _PHRASES.items():
        normalized = normalized.replace(phrase, replacement)
    tokens: set[str] = set()
    for raw in normalized.split():
        if raw in _STOPWORDS:
            continue
        stem = basic_stem(raw)
        tokens.add(_SYNONYMS.get(stem, _SYNONYMS.get(raw, stem)))
    return tokens


def jaro(a: str, b: str) -> float:
    """Jaro similarity (stdlib-only implementation)."""
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    match_distance = max(len(a), len(b)) // 2 - 1
    a_matches = [False] * len(a)
    b_matches = [False] * len(b)
    matches = 0
    for i, ch in enumerate(a):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len(b))
        for j in range(start, end):
            if not b_matches[j] and b[j] == ch:
                a_matches[i] = b_matches[j] = True
                matches += 1
                break
    if matches == 0:
        return 0.0
    transpositions = 0
    k = 0
    for i, ch in enumerate(a):
        if a_matches[i]:
            while not b_matches[k]:
                k += 1
            if ch != b[k]:
                transpositions += 1
            k += 1
    transpositions //= 2
    return (
        matches / len(a)
        + matches / len(b)
        + (matches - transpositions) / matches
    ) / 3.0


def jaro_winkler(a: str, b: str) -> float:
    score = jaro(a, b)
    prefix = 0
    for ca, cb in zip(a, b):
        if ca != cb or prefix == 4:
            break
        prefix += 1
    return score + prefix * 0.1 * (1.0 - score)


def token_dice(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return 2.0 * len(a & b) / (len(a) + len(b))


def label_similarity(a: str, b: str) -> tuple[float, str]:
    """Return ``(score, reason)`` for two node labels."""
    na, nb = normalize_label(a), normalize_label(b)
    if not na or not nb:
        return 0.0, "empty label"
    if na == nb:
        return 1.0, "exact normalised label"

    ta, tb = canonical_tokens(a), canonical_tokens(b)
    if ta and ta == tb:
        return 0.94, "semantic synonym (canonical tokens)"

    dice = token_dice(ta, tb)
    char = jaro_winkler(na, nb)
    sequence = SequenceMatcher(None, na, nb).ratio()

    # Long labels: token overlap dominates.  Very similar strings are often
    # typos/spelling variants, so character similarity gets a high weight.
    if len(ta) >= 3 and len(tb) >= 3:
        score = max(dice, 0.72 * char)
        if sequence >= 0.88:
            score = max(score, 0.97 * sequence)
        elif char >= 0.88:
            score = max(score, 0.96 * char)
        reason = f"token overlap {dice:.2f}, string {char:.2f}, sequence {sequence:.2f}"
    else:
        score = max(char, dice)
        reason = f"string {char:.2f}"
    if na in nb or nb in na:
        score = max(score, 0.86)
        reason += ", containment"

    # Domain contrasts ("general" vs "corporate", "inpatient" vs
    # "outpatient", ...) change the business meaning even when the remaining
    # wording is identical.
    for group in _CONTRAST_GROUPS:
        a_hits = ta & group
        b_hits = tb & group
        if a_hits and b_hits and not (a_hits & b_hits):
            score = min(score, 0.68)
            reason += f", domain contrast {sorted(a_hits)} vs {sorted(b_hits)}"
            break

    return min(score, 0.99), reason


# ---------------------------------------------------------------------------
# Alignment data structures
# ---------------------------------------------------------------------------
@dataclass
class AlignmentConfig:
    synonym_threshold: float = 0.72
    match_threshold: float = 0.45
    review_low: float = 0.45
    review_high: float = 0.62
    structural_threshold: float = 0.34
    use_llm: bool = False


@dataclass
class Pair:
    a: str | None
    b: str | None
    label: str
    score: float = 0.0
    reason: str = ""
    confidence: str = "high"
    needs_review: bool = False
    llm_reason: str = ""

    @property
    def matched(self) -> bool:
        return self.a is not None and self.b is not None

    def to_dict(self) -> dict:
        return {
            "a": self.a,
            "b": self.b,
            "label": self.label,
            "score": round(self.score, 3),
            "reason": self.reason,
            "confidence": self.confidence,
            "needs_review": self.needs_review,
            "llm_reason": self.llm_reason,
        }


@dataclass
class Alignment:
    pairs: list[Pair] = field(default_factory=list)
    a_to_b: dict[str, str] = field(default_factory=dict)
    b_to_a: dict[str, str] = field(default_factory=dict)
    pair_of_a: dict[str, Pair] = field(default_factory=dict)
    pair_of_b: dict[str, Pair] = field(default_factory=dict)

    def add(self, pair: Pair) -> None:
        self.pairs.append(pair)
        if pair.a is not None:
            self.pair_of_a[pair.a] = pair
        if pair.b is not None:
            self.pair_of_b[pair.b] = pair
        if pair.a is not None and pair.b is not None:
            self.a_to_b[pair.a] = pair.b
            self.b_to_a[pair.b] = pair.a

    @property
    def matched_pairs(self) -> list[Pair]:
        return [p for p in self.pairs if p.matched]

    @property
    def unmatched_a(self) -> list[Pair]:
        return [p for p in self.pairs if p.a is not None and p.b is None]

    @property
    def unmatched_b(self) -> list[Pair]:
        return [p for p in self.pairs if p.b is not None and p.a is None]

    def counts(self) -> dict[str, int]:
        result = {"identical": 0, "synonym": 0, "meaning_changed": 0, "unmatched": 0}
        for pair in self.pairs:
            result[pair.label] = result.get(pair.label, 0) + 1
        result["matched"] = len(self.matched_pairs)
        result["needs_review"] = sum(1 for p in self.pairs if p.needs_review)
        return result

    def to_dict(self) -> dict:
        return {"counts": self.counts(), "pairs": [p.to_dict() for p in self.pairs]}


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------
def _context_labels(model: ProcessModel, node_id: str) -> set[str]:
    labels: set[str] = set()
    for nid in model.predecessors(node_id) + model.successors(node_id):
        node = model.nodes.get(nid)
        if node is not None and node.name.strip():
            labels.add(normalize_label(node.name))
    return labels


def _structural_similarity(a: ProcessModel, a_id: str, b: ProcessModel, b_id: str) -> tuple[float, str]:
    na, nb = a.nodes[a_id], b.nodes[b_id]
    ca, cb = _context_labels(a, a_id), _context_labels(b, b_id)
    if ca and cb:
        context = len(ca & cb) / len(ca | cb)
    else:
        context = 0.0
    deg_a = (a.in_degree(a_id), a.out_degree(a_id))
    deg_b = (b.in_degree(b_id), b.out_degree(b_id))
    degree = 1.0 - (abs(deg_a[0] - deg_b[0]) + abs(deg_a[1] - deg_b[1])) / max(
        1, sum(deg_a) + sum(deg_b)
    )
    type_bonus = 0.0
    if na.kind == nb.kind:
        type_bonus = 0.18
    elif na.is_gateway and nb.is_gateway:
        type_bonus = 0.04
    score = min(1.0, 0.68 * context + 0.22 * degree + type_bonus)
    return score, f"structural context {context:.2f}, degree {degree:.2f}"


def _initial_pairs(a: ProcessModel, b: ProcessModel, config: AlignmentConfig) -> list[Pair]:
    candidates: list[tuple[float, str, str, str]] = []
    for na in a.nodes.values():
        if na.is_gateway or not na.name.strip():
            continue
        for nb in b.nodes.values():
            if nb.is_gateway or not nb.name.strip():
                continue
            if na.family != nb.family:
                continue
            score, reason = label_similarity(na.name, nb.name)
            if score >= config.match_threshold:
                candidates.append((score, na.id, nb.id, reason))
    candidates.sort(key=lambda item: (-item[0], a.nodes[item[1]].display_name.lower()))
    used_a: set[str] = set()
    used_b: set[str] = set()
    pairs: list[Pair] = []
    for score, a_id, b_id, reason in candidates:
        if a_id in used_a or b_id in used_b:
            continue
        used_a.add(a_id)
        used_b.add(b_id)
        if normalize_label(a.nodes[a_id].name) == normalize_label(b.nodes[b_id].name):
            label = "identical"
        elif score >= config.synonym_threshold:
            label = "synonym"
        else:
            label = "meaning_changed"
        needs_review = config.review_low <= score < config.review_high
        confidence = "high" if score >= config.review_high else ("low" if needs_review else "medium")
        pairs.append(
            Pair(
                a_id,
                b_id,
                label,
                score,
                reason,
                confidence=confidence,
                needs_review=needs_review,
            )
        )
    return pairs


def _structural_pairs(
    a: ProcessModel, b: ProcessModel, alignment: Alignment, config: AlignmentConfig
) -> list[Pair]:
    """Pair gateways and unnamed events using their matched neighbourhood."""
    used_a = set(alignment.pair_of_a)
    used_b = set(alignment.pair_of_b)
    candidates: list[tuple[float, str, str, str]] = []
    for na in a.nodes.values():
        if na.id in used_a:
            continue
        if not (na.is_gateway or (na.is_event and not na.name.strip())):
            continue
        for nb in b.nodes.values():
            if nb.id in used_b:
                continue
            if not (nb.is_gateway or (nb.is_event and not nb.name.strip())):
                continue
            if na.family != nb.family:
                continue
            if na.kind != nb.kind and not (na.is_gateway and nb.is_gateway):
                continue
            if na.is_event and nb.is_event and na.kind != nb.kind and "event" not in (na.kind, nb.kind):
                continue
            score, reason = _structural_similarity(a, na.id, b, nb.id)
            if score >= config.structural_threshold:
                candidates.append((score, na.id, nb.id, reason))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    pairs: list[Pair] = []
    for score, a_id, b_id, reason in candidates:
        if a_id in used_a or b_id in used_b:
            continue
        used_a.add(a_id)
        used_b.add(b_id)
        pairs.append(
            Pair(
                a_id,
                b_id,
                "identical",
                score,
                reason,
                confidence="medium" if score < config.review_high else "high",
                needs_review=False,
            )
        )
    return pairs


def _cross_family_pairs(a: ProcessModel, b: ProcessModel, alignment: Alignment) -> list[Pair]:
    """Detect same-label nodes whose type changed (e.g. task -> gateway)."""
    used_a = set(alignment.pair_of_a)
    used_b = set(alignment.pair_of_b)
    pairs: list[Pair] = []
    for na in a.nodes.values():
        if na.id in used_a or not na.name.strip():
            continue
        for nb in b.nodes.values():
            if nb.id in used_b or not nb.name.strip():
                continue
            if na.family == nb.family:
                continue
            if normalize_label(na.name) == normalize_label(nb.name):
                pairs.append(
                    Pair(na.id, nb.id, "identical", 1.0, "same label, different element type")
                )
                used_a.add(na.id)
                used_b.add(nb.id)
                break
    return pairs


def align(
    a: ProcessModel,
    b: ProcessModel,
    config: AlignmentConfig | None = None,
    llm=None,
) -> Alignment:
    """Align the nodes of ``a`` (reference) and ``b`` (variant)."""
    config = config or AlignmentConfig()
    result = Alignment()

    for pair in _initial_pairs(a, b, config):
        result.add(pair)

    for pair in _structural_pairs(a, b, result, config):
        result.add(pair)

    for pair in _cross_family_pairs(a, b, result):
        result.add(pair)

    # Optional LLM adjudication for ambiguous label pairs.
    ambiguous = [
        p for p in result.matched_pairs
        if p.needs_review and a.nodes[p.a].name.strip() and b.nodes[p.b].name.strip()
    ]
    if config.use_llm and llm is not None and ambiguous:
        verdicts = llm.adjudicate(
            [(a.nodes[p.a].display_name, b.nodes[p.b].display_name) for p in ambiguous]
        )
        for pair, verdict in zip(ambiguous, verdicts):
            if not verdict:
                continue
            label = verdict.get("label", "")
            if label in {"identical", "synonym", "meaning_changed", "unmatched"}:
                pair.label = label
                pair.confidence = verdict.get("confidence", "high")
                pair.needs_review = label == "unmatched" or pair.confidence == "low"
                pair.llm_reason = verdict.get("reason", "")

    # Build the final one-to-one mapping (drop pairs re-labelled unmatched).
    matched = [p for p in result.pairs if p.matched and p.label != "unmatched"]
    covered_a = {p.a for p in matched}
    covered_b = {p.b for p in matched}
    final = list(matched)
    for node in a.nodes.values():
        if node.id not in covered_a:
            final.append(Pair(node.id, None, "unmatched"))
    for node in b.nodes.values():
        if node.id not in covered_b:
            final.append(Pair(None, node.id, "unmatched"))

    # Re-create alignment maps.
    result = Alignment()
    for pair in final:
        result.add(pair)
    return result


def relabel_map(a: ProcessModel, b: ProcessModel, alignment: Alignment) -> dict[str, str]:
    """Map every matched variant task/event to the reference display name."""
    mapping: dict[str, str] = {}
    for pair in alignment.matched_pairs:
        if pair.a and pair.b:
            mapping[pair.b] = a.nodes[pair.a].display_name
    return mapping
