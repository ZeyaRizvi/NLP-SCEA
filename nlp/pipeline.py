import re
from dataclasses import dataclass
import importlib
import math
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple


_WS_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-zA-Z0-9\s]")
_DURATION_RE = re.compile(r"(\d+)\s*(hour|hr|hrs|hours|minute|min|mins|minutes)\b")
_DEFAULT_SPACY_MODEL = "en_core_web_sm"


def _normalize_text(text: str) -> str:
    text = text.strip().lower()
    text = _NON_ALNUM_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text)
    return text


def _duration_hours(text: str) -> Optional[float]:
    """
    Extract a single duration expression like "2 hours" or "30 mins" from text.
    Returns None if no duration is detected.
    """
    match = _DURATION_RE.search(text.lower())
    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2)

    unit = unit.lower()
    if unit in {"minute", "min", "mins", "minutes"}:
        return value / 60.0
    return value


@dataclass(frozen=True)
class ClassificationResult:
    issue_type: str
    score: float
    matched_keywords: List[str]


@dataclass(frozen=True)
class UrgencyResult:
    level: str  # low | medium | high
    score: float
    matched_signals: List[str]


class ElectricityComplaintNLP:
    """
    Lightweight spaCy-powered pipeline with deterministic (rule-based) logic:
    - Text preprocessing
    - Keyword extraction
    - Issue classification
    - Urgency detection

    Note: this avoids needing a large pre-trained spaCy/ML model for bootstrapping.
    """

    ISSUE_TYPES = (
        "power_cut",
        "voltage_issue",
        "transformer_fault",
        "billing_issue",
        "wire_issue",
        "meter_issue",
    )
    URGENCY_LEVELS = ("low", "medium", "high")
    _TRANSFORMER_MODEL_NAME = os.getenv("NLP_CLASSIFIER_MODEL", "distilbert-base-uncased")
    _AI_CONFIDENCE_THRESHOLD = 0.20

    # Keep these keyword lists easy to extend.
    # Classification uses case-insensitive normalized matching + simple scoring.
    _ISSUE_KEYWORDS: Dict[str, Sequence[str]] = {
        "power_cut": (
            "power cut",
            "no power",
            "no electricity",
            "blackout",
            "outage",
            "line down",
            "electricity gone",
            "power gone",
            "light gone",
            "lights gone",
            "no current",
            "current gone",
            "supply not coming",
            "power not coming",
            "light not coming",
            "no light",
            "no supply",
            "current not coming",
        ),
        "voltage_issue": (
            "low voltage",
            "high voltage",
            "voltage fluctuation",
            "unstable voltage",
            "voltage drop",
            "voltage problem",
            "low current",
            "high current",
            "voltage up down",
            "fluctuating voltage",
            "fan slow",
            "dim light",
            "ac not working properly",
        ),
        "transformer_fault": (
            "transformer blast",
            "transformer issue",
            "burnt transformer",
            "sparking",
            "explosion",
            "transformer fault",
            "transformer burst",
            "transformer burned",
            "transformer smoke",
            "loud sound near transformer",
            "sparks near transformer",
        ),
        "billing_issue": (
            "wrong bill",
            "high bill",
            "billing problem",
            "extra charge",
            "meter issue",
            "billing issue",
            "bill too high",
            "extra bill",
            "wrong amount",
            "electricity bill issue",
            "overcharged",
            "bill mistake",
            "unexpected bill",
        ),
        "wire_issue": (
            "wire cut",
            "electric wire problem",
            "cable damage",
            "loose wire",
            "wire issue",
            "wire broken",
            "cable cut",
            "electric pole wire issue",
            "hanging wire",
            "wire sparking",
        ),
        "meter_issue": (
            "meter not working",
            "faulty meter",
            "reading issue",
            "meter issue",
            "meter not running",
            "meter fast",
            "meter slow",
            "reading wrong",
            "meter dead",
            "meter stuck",
        ),
    }
    _LABEL_PROTOTYPES: Dict[str, str] = {
        "power_cut": (
            "power cut complaint where electricity supply is not available, "
            "no power, no current, blackout, outage, light gone, line down, or power not coming"
        ),
        "voltage_issue": (
            "voltage related complaint such as low voltage, high voltage, unstable voltage, "
            "voltage fluctuation, voltage drop, fan slow due to low current, dim light, or ac not working properly"
        ),
        "transformer_fault": (
            "transformer fault complaint including transformer blast, transformer burst, "
            "transformer smoke, transformer damage, sparks near transformer, loud sound near transformer, or explosion"
        ),
        "billing_issue": (
            "electricity billing complaint such as wrong bill amount, high bill, extra charge, "
            "unexpected bill, overcharged invoice, billing problem, or incorrect electricity bill"
        ),
        "wire_issue": (
            "electric wire complaint including wire cut, wire broken, hanging wire, loose wire, "
            "cable cut, cable damage, electric pole wire issue, or wire sparking problem"
        ),
        "meter_issue": (
            "electric meter problem such as meter running fast, meter running slow, "
            "incorrect reading, faulty meter device, electricity meter not working properly"
        ),
    }

    _URGENCY_HIGH_SIGNALS: Sequence[str] = (
        "urgent",
        "immediately",
        "asap",
        "danger",
        "sparking",
        "fire",
        "blast",
        "explosion",
    )

    _URGENCY_MEDIUM_SIGNALS: Sequence[str] = (
        "problem",
        "not working",
        "issue",
    )

    def __init__(self, spacy_model: Optional[str] = None) -> None:
        # Prefer a pretrained spaCy model so NER can detect locations.
        # Fallback to blank English pipeline when model is unavailable.
        _spacy = importlib.import_module("spacy")
        model_name = spacy_model or _DEFAULT_SPACY_MODEL

        try:
            self.nlp: Any = _spacy.load(model_name)
            self.ner_enabled = "ner" in self.nlp.pipe_names
        except OSError:
            self.nlp = _spacy.blank("en")
            self.ner_enabled = False

        self.stop_words = set(self.nlp.Defaults.stop_words)

        # Ensure the phrase patterns are matched on normalized text.
        self._normalized_issue_keywords: Dict[str, List[str]] = {
            issue: [self._normalize_phrase(p) for p in phrases]
            for issue, phrases in self._ISSUE_KEYWORDS.items()
        }

        # AI classifier (transformer) is optional.
        # If unavailable or low-confidence, keyword rules are used.
        self._ai_enabled = False
        self._hf_tokenizer: Any = None
        self._hf_model: Any = None
        self._torch: Any = None
        self._label_embeddings: Dict[str, Any] = {}
        self._init_ai_classifier()

    def _init_ai_classifier(self) -> None:
        try:
            transformers = importlib.import_module("transformers")
            torch = importlib.import_module("torch")
        except Exception:
            return

        try:
            self._hf_tokenizer = transformers.AutoTokenizer.from_pretrained(self._TRANSFORMER_MODEL_NAME)
            self._hf_model = transformers.AutoModel.from_pretrained(self._TRANSFORMER_MODEL_NAME)
            self._hf_model.eval()
            self._torch = torch

            # Cache label embeddings once for fast repeated inference.
            self._label_embeddings = {
                label: self._embed_text(proto) for label, proto in self._LABEL_PROTOTYPES.items()
            }
            self._ai_enabled = True
        except Exception:
            self._ai_enabled = False
            self._hf_tokenizer = None
            self._hf_model = None
            self._torch = None
            self._label_embeddings = {}

    def _embed_text(self, text: str) -> Any:
        """
        Mean-pool token embeddings from DistilBERT using attention mask,
        then L2-normalize vector for stable cosine-style similarity.
        """
        encoded = self._hf_tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
        with self._torch.no_grad():
            outputs = self._hf_model(**encoded)
        # outputs.last_hidden_state shape: [batch, seq, hidden]
        token_embeddings = outputs.last_hidden_state
        attention_mask = encoded["attention_mask"].unsqueeze(-1).expand(token_embeddings.size()).float()

        summed = (token_embeddings * attention_mask).sum(dim=1)
        counts = attention_mask.sum(dim=1).clamp(min=1e-9)
        mean_pooled = summed / counts

        normalized = self._torch.nn.functional.normalize(mean_pooled, p=2, dim=1)
        return normalized.squeeze(0)

    def _classify_issue_ai(self, text: str) -> Optional[ClassificationResult]:
        if not self._ai_enabled:
            return None

        try:
            text_vec = self._embed_text(text)
            sims: List[Tuple[str, float]] = []
            for label in self.ISSUE_TYPES:
                label_vec = self._label_embeddings[label]
                # Both vectors are already normalized, so dot product equals cosine similarity.
                sim = float(self._torch.dot(text_vec, label_vec).item())
                sims.append((label, sim))

            # Convert similarities to pseudo-probabilities via stable softmax.
            max_sim = max(s for _, s in sims)
            exps = [(label, math.exp(sim - max_sim)) for label, sim in sims]
            denom = sum(v for _, v in exps) or 1.0
            probs = [(label, val / denom) for label, val in exps]
            probs.sort(key=lambda x: x[1], reverse=True)
            best_label, best_prob = probs[0]

            return ClassificationResult(
                issue_type=best_label,
                score=float(best_prob),
                matched_keywords=[f"ai:{best_label}"],
            )
        except Exception:
            return None

    @staticmethod
    def _normalize_phrase(phrase: str) -> str:
        phrase = phrase.lower().strip()
        phrase = _NON_ALNUM_RE.sub(" ", phrase)
        phrase = _WS_RE.sub(" ", phrase)
        return phrase

    def preprocess(self, text: str) -> str:
        return _normalize_text(text)

    def extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        normalized = self.preprocess(text)
        doc = self.nlp(normalized)

        candidates: List[str] = []
        for token in doc:
            if token.is_stop:
                continue
            if not token.is_alpha:
                continue
            if len(token.text) <= 2:
                continue
            candidates.append(token.text.lower())

        # Basic frequency ranking.
        freq: Dict[str, int] = {}
        for c in candidates:
            freq[c] = freq.get(c, 0) + 1

        # Add phrase-like keywords based on known issue keywords.
        phrase_keywords: List[str] = []
        for issue_keywords in self._normalized_issue_keywords.values():
            for kw in issue_keywords:
                if " " in kw and kw in normalized:
                    phrase_keywords.append(kw)

        # Keep ordering stable-ish: frequency first, then phrase matches.
        ranked = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        keyword_list = [w for w, _ in ranked[:top_k]]

        for pk in phrase_keywords:
            if pk not in keyword_list and len(keyword_list) < top_k:
                keyword_list.append(pk)

        return keyword_list

    def _classify_issue_keyword(self, text: str) -> ClassificationResult:
        normalized = self.preprocess(text)
        token_set = set(normalized.split())

        best_issue = "power_cut"
        best_score = 0.0
        best_matches: List[str] = []

        for issue_type in self.ISSUE_TYPES:
            matched: List[str] = []
            score = 0.0
            for kw in self._normalized_issue_keywords[issue_type]:
                parts = kw.split()

                # Strong phrase hit.
                if kw in normalized:
                    matched.append(kw)
                    score += 2.0
                    continue

                # Flexible partial hit: most terms from a phrase appear in text.
                matched_count = sum(1 for p in parts if p in token_set)
                # Partial phrase logic:
                # - 2-word phrases should match both words (to reduce false positives).
                # - 3+ word phrases can match when most words appear.
                if len(parts) == 2 and matched_count == 2:
                    matched.append(kw)
                    score += 1.0
                    continue
                if len(parts) >= 3 and matched_count >= (len(parts) - 1):
                    matched.append(kw)
                    score += 1.0
                    continue

                # Single token hit.
                if len(parts) == 1 and parts[0] in token_set:
                    matched.append(kw)
                    score += 0.75

            if score > best_score:
                best_score = score
                best_issue = issue_type
                best_matches = matched

        if best_score <= 0:
            return ClassificationResult(issue_type="power_cut", score=0.05, matched_keywords=[])

        confidence = max(0.05, min(1.0, best_score / 4.0))
        return ClassificationResult(issue_type=best_issue, score=confidence, matched_keywords=best_matches)

    def classify_issue(self, text: str) -> ClassificationResult:
        ai_result = self._classify_issue_ai(text)
        if ai_result and ai_result.score >= self._AI_CONFIDENCE_THRESHOLD:
            return ai_result
        return self._classify_issue_keyword(text)

    def extract_location_and_issue(self, text: str) -> Dict[str, object]:
        """
        Named Entity Extraction + issue hint extraction.

        Returns:
        {
            "location": "<area_name_or_unknown>",
            "issue_type": "<predicted_issue_type>",
            "issue_keywords": ["..."]
        }
        """
        location = "unknown"

        # 1) Regex detection: "in Mirpur", "at Hazaribagh"
        # Capture stops before common delimiters/continuations (e.g., "for", "since", comma, period).
        regex = re.compile(
            r"\b(?:in|at)\s+([a-z][a-z\s]{1,50}?)(?=\s*(?:,|\.|;|:|\bfor\b|\bsince\b|\bnear\b|\barea\b|\bfrom\b|\bwith\b|\bwithout\b|$))",
            flags=re.IGNORECASE,
        )
        match = regex.search(text)
        if match:
            candidate = match.group(1).strip()
            if candidate:
                # Preserve original casing from the input span.
                location = text[match.start(1) : match.end(1)].strip()

        # 2) Fallback to predefined Indian locations list (case-insensitive).
        if location == "unknown":
            indian_locations = [
                "hazaribagh",
                "mirpur",
                "anna nagar",
                "ambattur",
                "delhi",
                "mumbai",
            ]
            lowered = text.lower()
            for loc in indian_locations:
                if re.search(rf"\b{re.escape(loc)}\b", lowered):
                    location = " ".join(w.capitalize() for w in loc.split())
                    break

        classification = self.classify_issue(text)
        return {
            "location": location,
            "issue_type": classification.issue_type,
            "issue_keywords": classification.matched_keywords,
        }

    def extract_location_issue_summary(self, text: str) -> Dict[str, str]:
        """
        Strict minimal NER summary requested by downstream consumers:
        {
            "location": "...",
            "issue_type": "..."
        }
        """
        result = self.extract_location_and_issue(text)
        return {
            "location": str(result["location"]),
            "issue_type": str(result["issue_type"]),
        }

    def detect_urgency(self, text: str, issue_type: str) -> UrgencyResult:
        original_lower = text.lower().strip()

        duration = _duration_hours(original_lower)

        matched_high = [s for s in self._URGENCY_HIGH_SIGNALS if s in original_lower]
        matched_medium = [s for s in self._URGENCY_MEDIUM_SIGNALS if s in original_lower]
        since_pattern = any(s in original_lower for s in ("since morning", "since night"))

        score = 0.0
        matched_signals: List[str] = []

        # Base score by issue category.
        if issue_type in {"transformer_fault", "wire_issue"}:
            score += 0.22
        elif issue_type in {"power_cut", "voltage_issue", "meter_issue"}:
            score += 0.15
        else:
            score += 0.1

        # High urgency keyword triggers.
        if matched_high:
            score += 0.6
            matched_signals.extend(matched_high[:4])

        # Duration-based urgency.
        if duration is not None:
            if duration > 3:
                score += 0.5
                matched_signals.append("duration_>3h")
            elif duration >= 1:
                score += 0.3
                matched_signals.append("duration_1_to_3h")
            else:
                score += 0.1
                matched_signals.append("duration_<1h")

        # Textual long-duration hint.
        if since_pattern:
            score += 0.7
            matched_signals.append("since_morning_or_night")

        # Medium urgency words.
        if matched_medium:
            score += 0.25
            matched_signals.extend(matched_medium[:3])

        # Clamp score.
        score = max(0.0, min(1.0, score))

        if score >= 0.8:
            level = "high"
        elif score >= 0.35:
            level = "medium"
        else:
            level = "low"

        return UrgencyResult(level=level, score=score, matched_signals=matched_signals)

    def analyze(self, complaint_text: str) -> Dict[str, object]:
        preprocessed = self.preprocess(complaint_text)
        keywords = self.extract_keywords(complaint_text)
        classification = self.classify_issue(complaint_text)
        entity_result = self.extract_location_and_issue(complaint_text)
        urgency = self.detect_urgency(complaint_text, classification.issue_type)

        return {
            "input_text": complaint_text,
            "preprocessed_text": preprocessed,
            "keywords": keywords,
            "entity_extraction": entity_result,
            "issue_classification": {
                "issue_type": classification.issue_type,
                "matched_keywords": classification.matched_keywords,
            },
            "urgency": {
                "level": urgency.level,
                "score": urgency.score,
                "matched_signals": urgency.matched_signals,
            },
        }

