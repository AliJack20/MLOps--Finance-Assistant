#things to install in requirmeents.txt
#prometheus_client
#better_profanity
#regex
#sentence-transformers    # optional but recommended for hallucination detection
#scikit-learn             # used for cosine similarity if using embeddings

# src/rag_app/guardrails.py
import re
import logging
from typing import Dict, Any, Tuple, Optional, List

from prometheus_client import Counter
from better_profanity import profanity

# Optional embeddings (used for hallucination detection). Import only if available.
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    EMB_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    _HAS_EMB = True
except Exception:
    EMB_MODEL = None
    _HAS_EMB = False

logger = logging.getLogger("guardrails")

# Prometheus counters
INPUT_VIOLATIONS = Counter("guardrail_input_violations_total", "Number of input validation violations")
OUTPUT_VIOLATIONS = Counter("guardrail_output_violations_total", "Number of output moderation violations")
HALLUCINATION_WARNINGS = Counter("guardrail_hallucination_warnings_total", "Number of hallucination warnings")

# Thresholds & patterns (tune them)
HALLUCINATION_SIM_THRESHOLD = 0.55  # embedding cosine similarity threshold - tune for your data
HALLUCINATION_LEXICAL_THRESHOLD = 0.15  # fraction of answer tokens found in context (lexical fallback)
PROFANITY_FLAG = True

# Common PII regexes
RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
RE_PHONE = re.compile(r"\b(?:\+?\d{1,3}[ -]?)?(?:\(?\d{2,4}\)?[ -]?)?\d{6,10}\b")
RE_CREDIT_CARD = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
RE_SSNLK = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")  # example SSN pattern

# Prompt injection suspicious phrases
PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"disregard (all )?previous",
    r"forget (all )?previous",
    r"override (the )?system",
    r"pretend you are",
    r"you are now",
    r"from now on you will",
]


def detect_pii(text: str) -> List[str]:
    hits = []
    if RE_EMAIL.search(text):
        hits.append("email")
    if RE_PHONE.search(text):
        hits.append("phone")
    if RE_CREDIT_CARD.search(text):
        hits.append("credit_card_like")
    if RE_SSNLK.search(text):
        hits.append("ssn_like")
    return hits


def detect_prompt_injection(text: str) -> List[str]:
    hits = []
    lower = text.lower()
    for pat in PROMPT_INJECTION_PATTERNS:
        if re.search(pat, lower):
            hits.append(pat)
    # also check for user embedding instructions like "system: ..." or long YAML blocks
    if "system:" in lower or "### instructions" in lower:
        hits.append("embedded_instruction_block")
    return hits


def validate_input(user_text: str) -> Dict[str, Any]:
    """
    Validate input: detect PII and prompt injection.
    Returns a dict: {"ok": bool, "reasons": [...], "action": "reject"|"sanitize"|"allow"}
    """
    reasons = []
    pii = detect_pii(user_text)
    if pii:
        reasons.append({"type": "pii", "details": pii})
    inj = detect_prompt_injection(user_text)
    if inj:
        reasons.append({"type": "prompt_injection", "details": inj})

    if reasons:
        INPUT_VIOLATIONS.inc()
        logger.warning("Input validation failed: %s", reasons)
        return {"ok": False, "reasons": reasons, "action": "reject"}
    return {"ok": True, "reasons": [], "action": "allow"}


def _lexical_overlap(answer: str, context: str) -> float:
    """
    Simple lexical overlap fraction: tokens in answer that appear in context.
    """
    a_tokens = set(re.findall(r"\w+", answer.lower()))
    c_tokens = set(re.findall(r"\w+", context.lower()))
    if not a_tokens:
        return 0.0
    overlap = len(a_tokens & c_tokens) / float(len(a_tokens))
    return overlap


def detect_hallucination(answer: str, context: str) -> Dict[str, Any]:
    """
    Return a dict describing hallucination risk.
      - If embeddings available: compute cosine similarity between embeddings of answer and context.
      - Else: use lexical overlap fallback.
    """
    if not context or context.strip() == "":
        # No context — higher risk of hallucination.
        HALLUCINATION_WARNINGS.inc()
        return {"is_hallucination": True, "reason": "no_context"}

    if _HAS_EMB:
        try:
            a_emb = EMB_MODEL.encode([answer])
            c_emb = EMB_MODEL.encode([context])
            sim = float(cosine_similarity(a_emb, c_emb).mean())
            logger.debug("Embedding sim (answer,context)= %.4f", sim)
            if sim < HALLUCINATION_SIM_THRESHOLD:
                HALLUCINATION_WARNINGS.inc()
                return {"is_hallucination": True, "score": sim, "method": "embedding"}
            return {"is_hallucination": False, "score": sim, "method": "embedding"}
        except Exception as e:
            logger.exception("Embedding hallucination check failed: %s", e)

    # fallback: lexical overlap
    overlap = _lexical_overlap(answer, context)
    logger.debug("Lexical overlap = %.4f", overlap)
    if overlap < HALLUCINATION_LEXICAL_THRESHOLD:
        HALLUCINATION_WARNINGS.inc()
        return {"is_hallucination": True, "score": overlap, "method": "lexical"}
    return {"is_hallucination": False, "score": overlap, "method": "lexical"}


def moderate_output(answer: str, context: Optional[str] = "") -> Dict[str, Any]:
    """
    Moderate LLM output: profanity check + hallucination check.
    Returns {"ok": bool, "reasons": [...], "action": "allow"|"warn"|"modify"|"block", "safe_answer": str}
    """
    reasons = []
    action = "allow"
    safe_answer = answer

    # profanity check
    if PROFANITY_FLAG and profanity.contains_profanity(answer):
        reasons.append({"type": "profanity"})
        action = "modify"
        OUTPUT_VIOLATIONS.inc()
        # simple sanitize: mask profane words
        safe_answer = profanity.censor(answer)

    # hallucination check (compare answer vs retrieved context)
    try:
        hall = detect_hallucination(answer, context or "")
        if hall.get("is_hallucination"):
            reasons.append({"type": "hallucination", "details": hall})
            action = "warn" if action == "allow" else action
            OUTPUT_VIOLATIONS.inc()
    except Exception as e:
        logger.exception("Hallucination check error: %s", e)

    if reasons:
        logger.warning("Output moderation flagged. reasons=%s action=%s", reasons, action)
    return {"ok": (action == "allow"), "reasons": reasons, "action": action, "safe_answer": safe_answer}
