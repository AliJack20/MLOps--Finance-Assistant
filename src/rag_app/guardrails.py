# rag_app/guardrails.py
import re
import logging
from typing import Dict, Any, List, Tuple
from prometheus_client import Counter
import numpy as np

logger = logging.getLogger("guardrails")

# Prometheus counters
INPUT_VIOLATIONS = Counter("guardrail_input_violations_total", "Total input validation violations", ["rule"])
OUTPUT_VIOLATIONS = Counter("guardrail_output_violations_total", "Total output moderation violations", ["rule"])
INPUT_CHECKS = Counter("guardrail_input_checks_total", "Total input validation checks")
OUTPUT_CHECKS = Counter("guardrail_output_checks_total", "Total output moderation checks")

# --- Simple PII regexes (extend as needed) ---
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PHONE_RE = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}")
_CREDIT_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")  # naive CC-like pattern
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# Prompt injection heuristics (case-insensitive)
_PROMPT_INJECTION_PATTERNS = [
    r"ignore (previous|above|before) instructions",
    r"disregard (previous|above|before) instructions",
    r"you are now (my|the) assistant",
    r"treat the following as system prompt",
    r"insert arbitrary code",
    r"do not mention you're an AI",
]
_PROMPT_INJECTION_RE = re.compile("|".join(_PROMPT_INJECTION_PATTERNS), re.IGNORECASE)

# Toxicity simple wordlist (expand with your org's list)
_TOXIC_WORDS = {"idiot", "stupid", "hate", "dumb", "kill", "terror"}  # minimal example

class Guardrails:
    def __init__(self, embeddings=None,
                 tox_threshold: float = 0.3,
                 hallucination_threshold: float = 0.6):
        """
        embeddings: optional Embeddings instance (from your RAG) used for semantic checks.
        tox_threshold: optional threshold used if you later add a model-based toxicity scorer.
        hallucination_threshold: cosine-similarity threshold below which a sentence is considered *unsupported*.
        """
        self.embeddings = embeddings
        self.tox_threshold = tox_threshold
        self.hallucination_threshold = hallucination_threshold

    # -----------------------
    # INPUT VALIDATION RULES
    # -----------------------
    def validate_input(self, text: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Run all input validation checks. Returns (ok, details).
        ok==True -> input passes.
        ok==False -> details contains rule and evidence.
        """
        INPUT_CHECKS.inc()
        # 1) PII detection
        pii_matches = []
        for (name, regex) in [
            ("email", _EMAIL_RE),
            ("phone", _PHONE_RE),
            ("ssn", _SSN_RE),
            ("credit_card_like", _CREDIT_RE),
        ]:
            found = regex.findall(text)
            if found:
                pii_matches.append({"type": name, "examples": found[:3]})

        if pii_matches:
            rule = "pii_detected"
            logger.warning("Input validation failed: %s -- %s", rule, pii_matches)
            INPUT_VIOLATIONS.labels(rule=rule).inc()
            return False, {"rule": rule, "evidence": pii_matches}

        # 2) Prompt injection heuristics
        if _PROMPT_INJECTION_RE.search(text):
            rule = "prompt_injection"
            evidence = _PROMPT_INJECTION_RE.findall(text)[:3]
            logger.warning("Input validation failed: %s -- %s", rule, evidence)
            INPUT_VIOLATIONS.labels(rule=rule).inc()
            return False, {"rule": rule, "evidence": evidence}

        # passed basic checks
        return True, {"rule": "ok"}

    # -----------------------
    # OUTPUT MODERATION RULES
    # -----------------------
    def moderate_output(self, answer: str, context: str = "") -> Tuple[bool, Dict[str, Any]]:
        """
        Run moderation checks on model output. Returns (ok, details).
        - toxicity check (wordlist; optional model integration)
        - hallucination check: compare sentence embeddings to context embeddings and flag unsupported sentences
        """
        OUTPUT_CHECKS.inc()
        # 1) Toxicity wordlist heuristic
        ans_lower = answer.lower()
        found_toxic = [w for w in _TOXIC_WORDS if w in ans_lower]
        if found_toxic:
            rule = "toxic_language"
            OUTPUT_VIOLATIONS.labels(rule=rule).inc()
            logger.warning("Output moderation failed: %s -- words=%s", rule, found_toxic)
            return False, {"rule": rule, "evidence": found_toxic}

        # 2) Hallucination detection via embeddings (requires embeddings configured)
        if self.embeddings is not None and context:
            # split answer into sentences (simple)
            sentences = [s.strip() for s in re.split(r'[.?!]\s+', answer) if s.strip()]
            if sentences:
                # embed each sentence and the context (context may be multiple documents separated by ---)
                try:
                    ctx_vec = self.embeddings.embed_documents([context])
                    # ctx_vec shape (1, D) -> use that
                    ctx_vec = np.asarray(ctx_vec, dtype=np.float32)[0]
                    unsupported = []
                    for sent in sentences:
                        sent_vec = self.embeddings.embed_query(sent)
                        if sent_vec is None:
                            continue
                        # cosine similarity
                        dot = np.dot(sent_vec, ctx_vec)
                        denom = (np.linalg.norm(sent_vec) * np.linalg.norm(ctx_vec))
                        sim = dot / denom if denom != 0 else 0.0
                        if sim < self.hallucination_threshold:
                            unsupported.append({"sentence": sent, "similarity": float(sim)})
                    if unsupported:
                        rule = "hallucination"
                        OUTPUT_VIOLATIONS.labels(rule=rule).inc()
                        logger.warning("Output moderation failed: %s -- %s", rule, unsupported[:3])
                        return False, {"rule": rule, "evidence": unsupported}
                except Exception as e:
                    # if embedding check fails, log but do not block by default
                    logger.exception("Embedding-based hallucination check failed: %s", e)

        # If all checks passed
        return True, {"rule": "ok"}

    # -----------------------
    # Logging helper
    # -----------------------
    def log_event(self, event_type: str, detail: Dict[str, Any]):
        """
        Centralized guardrail event logging which you can expand to send to your monitoring/alerting system.
        Logged via `logger` and Prometheus counters are incremented in rule checks above.
        """
        logger.info("Guardrail event: %s %s", event_type, detail)
        # If you have a monitoring exporter, send event there as well.
        # e.g., send to Datadog, Splunk, or other monitoring APIs here.
