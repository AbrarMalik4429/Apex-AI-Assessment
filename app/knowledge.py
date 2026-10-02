"""Local lexical RAG over reviewed JSON data. No pickle or uploaded code execution."""

import json
import math
import re
from collections import Counter
from datetime import date
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from app.contracts import ProviderError
from app.security import injection_attempt

ROOT = Path(__file__).resolve().parents[1] / "knowledge-base"
STOP = set(
    "a an the is are was be do does did can could would should i my me you your we our it its this that to of in on for and or with what which how when where please about have has at as from will am if by not".split()
)
MODES = {
    "state_plainly": "According to the supplied reference:",
    "hedge": "Typical information; this can vary:",
    "cite_and_verify": "Published source information; confirm against your own policy:",
    "hedge_and_verify": "This varies. Confirm with your insurer or care provider:",
    "state_as_clinic_policy": "For this synthetic clinic demo:",
    "state_with_safety_wrapper": "Follow the emergency operator's instructions. This does not replace medical care:",
}
FALLBACK = "I do not have enough reliable information in the supplied knowledge base to answer that. Please confirm with the clinic or your insurer. I have not sent a handoff or changed an appointment."
EMERGENCY = "If this is happening now, call 997 for an ambulance in Saudi Arabia, or your local emergency number elsewhere. Follow the emergency operator's instructions. Do not wait for a chatbot appointment. I cannot dispatch help or send a human handoff."


def knowledge_request_kind(query):
    text = query.casefold().strip().rstrip("?.!")
    if re.fullmatch(
        r"(?:please )?(?:how (?:do i|can i|to)|explain how to) (?:book|make|schedule) (?:an? |my )?appointment",
        text,
    ):
        return "booking_help"
    if re.fullmatch(
        r"(?:(?:show|give|tell) me |what are |can you show me )?(?:some |the |your )?(?:faqs?(?: questions)?|frequently asked questions)",
        text,
    ):
        return "faq_menu"
    if (
        "bupa" in text
        and re.search(r"\b(?:categories|category|types|tiers|plans|products|schemes)\b", text)
        and not re.search(
            r"\b(?:dental|optical|maternity|cover|pay|claim|gold|silver|bronze)\b", text
        )
    ):
        return "insurer_overview"
    return None


def terms(text):
    words = re.findall(r"[a-z0-9]+", text.casefold())
    return [w[:-1] if len(w) > 4 and w.endswith("s") else w for w in words if w not in STOP]


TAG_PATTERN = (
    r"`?\[(REGULATORY|OFFICIAL|INSURER|GUIDELINE|TYPICAL|VARIES|DEMO_CONFIG)(?::[^\]]*)?\]`?"
)


def row_confidence(row):
    """A cell inherits its document default, not uncertainty from unrelated cells."""
    tags = set(re.findall(TAG_PATTERN, row))
    if re.search(
        r"\b(?:verify|varies|depending|per contract|per scheme|chosen per|not published|not stated)\b",
        row,
        re.I,
    ):
        tags.add("VARIES")
    if re.search(r"\b(?:inferred|typically|usually)\b", row, re.I):
        tags.add("TYPICAL")
    if "CHI floor" in row:
        tags.add("REGULATORY")
    if not tags:
        tags.add("INSURER")
    mode = (
        "hedge_and_verify"
        if "VARIES" in tags
        else "hedge"
        if "TYPICAL" in tags
        else "cite_and_verify"
        if "INSURER" in tags
        else "state_plainly"
    )
    return sorted(tags), mode


def public_url(value):
    parts = urlsplit(value or "")
    return bool(
        parts.scheme in {"https", "http"}
        and parts.hostname
        and not parts.username
        and not parts.password
    )


@lru_cache(maxsize=1)
def load_corpus():
    chunks = [
        json.loads(line)
        for line in (ROOT / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    sources = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    seen = set()
    for c in chunks:
        if c["id"] in seen or c["answer_mode"] not in MODES or len(c["text"]) > 12000:
            raise ValueError("Invalid knowledge corpus")
        date.fromisoformat(c["review_by"])
        seen.add(c["id"])
    return chunks, sources


def runtime_text(c, settings):
    """Historical demo prose cannot override actual behavior or configured limits."""
    key = c["id"]
    if c["doc_id"] != "clinic-policies" and "DEMO_CONFIG" not in c["tags"]:
        return None
    if any(w in key for w in ("cancel", "reschedul")):
        return (
            f"Cancellation requires more than {settings.cancellation_notice_hours} hours' notice; "
            f"rescheduling requires more than {settings.reschedule_notice_hours} hours. "
            "Changes require your explicit confirmation. Inside those limits, human approval is needed, "
            "but this demo cannot send a handoff. No cancellation fee is defined."
        )
    if any(w in key for w in ("far-ahead", "available-slots")):
        return (
            f"The current booking horizon is {settings.booking_horizon_days} days. "
            "Availability takes account of recurring schedules, leave, occupied slots and your own overlapping appointments."
        )
    if any(w in key for w in ("hand", "human", "real-person")):
        return "This is an AI demo. It cannot transfer you to a person or send an escalation. Please contact the clinic directly."
    if any(w in key for w in ("opening", "contact", "phone-number", "accept-my-insurance")):
        return "The supplied demo does not confirm clinic opening hours, address, contact number or accepted insurers. Please contact the clinic directly."
    if any(w in key for w in ("identity", "privacy", "private", "family", "anyone-else")):
        return "The demo uses a shared synthetic patient session. It only accesses appointments belonging to that session. Production login and phone verification are not implemented."
    if "follow-up" in key:
        return "You can schedule an existing unscheduled follow-up linked to your earlier visit. Choose a valid time and explicitly confirm it."
    if "same-time" in key:
        return "The assistant rejects appointments that overlap your existing confirmed appointments, including with other doctors."
    if "confirmation" in key:
        return "Only a successfully saved result confirms a change. Check your active appointments if unsure; retry an uncertain request with the same request ID."
    if any(w in key for w in ("how-patients", "how-do-i-book", "specialty-i-need")):
        return "Book by doctor name, an explicitly named specialty, a previously seen doctor, or an existing follow-up. This demo does not infer a specialty from symptoms. Choose a time and explicitly confirm."
    if any(w in key for w in ("diagnos", "will-not-do")):
        return "I cannot diagnose, prescribe treatment or confirm your personal insurance coverage. Booking changes require your confirmation and a committed database result."
    return None


class KnowledgeBase:
    def __init__(self, settings):
        self.settings = settings
        raw, self.sources = load_corpus()
        self.chunks = []
        for original in raw:
            c = dict(original)
            override = runtime_text(c, settings)
            if override:
                c.update(
                    text=override,
                    answer_mode="state_as_clinic_policy",
                    tags=["DEMO_CONFIG"],
                    runtime_override=True,
                )
            # First aid procedural material needs clinician review; emergency contact guidance
            # is served independently and immediately. Keep originals for review, not generation.
            if c["category"] == "first_aid" or "GUIDELINE" in c["tags"]:
                continue
            if "rules-for-the-assistant" in c["id"] or injection_attempt(c["text"]):
                continue
            if not override and re.search(
                r"(?:hand (?:you|this)|pass (?:you|this)|escalat|transfer)", c["text"], re.I
            ):
                continue
            self.chunks.append(c)
            # The supplied insurer tables are split by plan. Add benefit-level views
            # so a dental question does not retrieve an entire plan's unrelated limits.
            lines = c["text"].splitlines()
            if (
                c["category"] == "insurance"
                and "benefit" in c["section"].casefold()
                and len(lines) > 5
            ):
                for row in lines[2:]:
                    if ":" not in row:
                        continue
                    label = row.split(":", 1)[0].strip()
                    row_id = re.sub(r"[^a-z0-9]+", "-", label.casefold()).strip("-")
                    row_tags, row_mode = row_confidence(row)
                    self.chunks.append(
                        {
                            **c,
                            "tags": row_tags,
                            "answer_mode": row_mode,
                            "field_label": label,
                            "field_value": row.split(":", 1)[1].strip(),
                            "plan": c.get("subsection") or c["section"],
                            "id": c["id"] + "--field-" + row_id,
                            "parent_id": c["id"],
                            "subsection": (c.get("subsection") or "") + " / " + label,
                            "text": lines[0] + " > " + label + "\n" + row,
                        }
                    )
        products = [
            c
            for c in self.chunks
            if c["doc_id"] == "ins-bupa"
            and c["section"] == "Product lines and schemes"
            and c.get("subsection")
        ]
        if products:
            overview = dict(products[0])
            rows = []
            for product in products:
                details = [
                    line
                    for line in product["text"].splitlines()
                    if line.startswith(("Product line:", "Who it is for:", "Schemes:"))
                ]
                rows.append("; ".join(details))
            overview.update(
                id="ins-bupa--product-overview",
                section="Product lines and schemes",
                subsection="Categories and plans",
                answer_mode="cite_and_verify",
                tags=["INSURER"],
                text="Bupa Arabia > Categories and plans\nThe supplied reference lists these product lines and schemes. Scheme names belong to their product line; they are not one universal category ladder.\n"
                + "\n".join(rows),
            )
            self.chunks.append(overview)
        counts = [
            Counter(
                terms(
                    c["title"]
                    + " "
                    + c["section"]
                    + " "
                    + (c.get("subsection") or "")
                    + " "
                    + c["text"]
                )
            )
            for c in self.chunks
        ]
        df = Counter(t for count in counts for t in count)
        self.idf = {t: math.log((1 + len(counts)) / (1 + n)) + 1 for t, n in df.items()}
        self.vectors = [self.vector(count) for count in counts]

    def vector(self, counts):
        vector = {t: (1 + math.log(n)) * self.idf[t] for t, n in counts.items() if t in self.idf}
        norm = math.sqrt(sum(x * x for x in vector.values())) or 1
        return {t: v / norm for t, v in vector.items()}

    def search(self, query):
        kind = knowledge_request_kind(query)
        target = {
            "booking_help": "faq-patient--booking-and-appointments--how-do-i-book-an-appointment",
            "insurer_overview": "ins-bupa--product-overview",
        }.get(kind)
        if target:
            return [
                {**c, "score": 1.0, "match_type": "topic"} for c in self.chunks if c["id"] == target
            ]
        search_query = query
        if re.search(
            r"\b(?:abroad|overseas|outside|countries|international|geographic)\b", query, re.I
        ):
            search_query += " geographic coverage"
        q = self.vector(Counter(terms(search_query)))
        mentioned = [
            name for name in ("bupa", "tawuniya", "medgulf", "rajhi") if name in query.casefold()
        ]
        scored = []
        topics = (
            set(terms(search_query))
            - set(terms(" ".join(mentioned)))
            - {"cover", "coverage", "insurance", "plan", "policy", "arabia", "al", "takaful"}
        )
        specific = [
            c
            for c in self.chunks
            if c["category"] == "insurance"
            and any(name in c["doc_id"] for name in mentioned)
            and topics.intersection(
                terms(
                    c["subsection"].split(" / ")[-1]
                    if c.get("parent_id")
                    else (c.get("subsection") or "") + " " + c["section"]
                )
            )
        ]
        specific_ids = {c["id"] for c in specific}

        for c, vector in zip(self.chunks, self.vectors):
            if (
                mentioned
                and c["category"] == "insurance"
                and not any(name in c["doc_id"] for name in mentioned)
            ):
                continue
            score = sum(v * vector.get(t, 0) for t, v in q.items())
            if c["id"] in specific_ids:
                score += 0.25
            if score >= 0.14:
                scored.append({**c, "score": round(score, 4)})
        return sorted(scored, key=lambda c: (-c["score"], c["id"]))[:5]

    def answer(self, query, interpreter, today):
        if knowledge_request_kind(query) == "faq_menu":
            questions = [
                c.get("subsection")
                for c in self.chunks
                if c["doc_id"] == "faq-patient" and c.get("subsection") and not c.get("parent_id")
            ]
            suggestions = [
                q
                for q in questions
                if q
                in {
                    "How do I book an appointment?",
                    "How far ahead can I book?",
                    "What is pre-authorization?",
                    "What is a co-payment or deductible?",
                    "How do I cancel an appointment?",
                    "Does this clinic accept my insurance company?",
                }
            ]
            return "Here are some questions you can ask:\n" + "\n".join(
                "- " + q for q in suggestions
            ) + "\nWhich would you like help with?", {
                "kind": "knowledge",
                "grounded": False,
                "code": "knowledge_topic_required",
                "citations": [],
                "suggestions": suggestions,
            }
        hits = self.search(query)
        if not hits:
            return FALLBACK, {
                "kind": "knowledge",
                "grounded": False,
                "citations": [],
                "code": "knowledge_no_matches",
            }
        selection = interpreter.select_knowledge(query, hits)
        allowed = {c["id"]: c for c in hits}
        if any(key not in allowed for key in selection.chunk_ids):
            raise ProviderError("groq_invalid_output")
        chosen = [allowed[key] for key in dict.fromkeys(selection.chunk_ids)]
        if not chosen:
            return FALLBACK, {
                "kind": "knowledge",
                "grounded": False,
                "citations": [],
                "code": "knowledge_evidence_rejected",
            }
        paragraphs, citations = [], []
        for n, c in enumerate(chosen, 1):
            body = c["text"] if c.get("runtime_override") else c["text"].partition("\n")[2]
            body = re.split(r"(?:Questions this answers:|Also asked as:)", body)[0].strip()
            body = re.sub(TAG_PATTERN, "", body).strip()
            if c.get("field_label"):
                value = re.sub(TAG_PATTERN, "", c["field_value"]).strip()
                scope = f"{c['title']} — {c['plan']}"
                body = f"{scope}: {c['field_label']}: {value}."
                if (
                    c["field_label"].casefold() == "geographic coverage"
                    and value.casefold() == "ksa"
                ):
                    body = (
                        f"The knowledge base lists coverage within Saudi Arabia (KSA) for {scope}."
                    )
                    if re.search(r"\b(?:outside|abroad|overseas|countries)\b", query, re.I):
                        body += " It does not establish cover outside KSA; check whether your policy includes an international extension."
            prefix = "For this synthetic clinic demo: " if c.get("runtime_override") else ""
            caveats = []
            if c["answer_mode"] == "hedge":
                caveats.append("These are typical terms and can vary.")
            elif c["answer_mode"] == "hedge_and_verify":
                caveats.append(
                    "The reference leaves this benefit dependent on the plan or contract; confirm that detail with your insurer."
                )
            # Keep source-specific limitations; do not repeat a blanket disclaimer on every fact.
            if c["doc_id"] == "ins-tawuniya" or "Tawuniya" in body:
                caveats.append(
                    "Source: June 2012 leaflet; figures are historical. Confirm with your insurer for current amounts."
                )
            if "REGULATORY" in c["tags"] and re.search(r"\d", body):
                caveats.append(
                    "These statutory figures come from the supplied summaries and require current verification."
                )
            if date.fromisoformat(c["review_by"]) < today and not c.get("runtime_override"):
                caveats.append("This reference is past its review date and may be out of date.")
            paragraphs.append(
                f"[{n}] {prefix}{body}" + ("\n" + " ".join(caveats) if caveats else "")
            )
            source = self.sources.get(c["doc_id"], {})
            citations.append(
                {
                    "number": n,
                    "chunk_id": c["id"],
                    "title": c["title"],
                    "section": c.get("subsection") or c["section"],
                    "answer_mode": c["answer_mode"],
                    "last_verified": c["last_verified"],
                    "review_by": c["review_by"],
                    "runtime_override": bool(c.get("runtime_override")),
                    "sources": [
                        {
                            "name": s["name"],
                            **({"url": s["url"]} if public_url(s.get("url")) else {}),
                        }
                        for s in source.get("sources", [])
                    ]
                    if not c.get("runtime_override")
                    else [{"name": "Current Python settings and implemented workflow"}],
                }
            )
        return "\n\n".join(paragraphs), {
            "kind": "knowledge",
            "grounded": True,
            "citations": citations,
        }
