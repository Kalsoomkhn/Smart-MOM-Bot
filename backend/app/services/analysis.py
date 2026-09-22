import json
import re
from functools import lru_cache
from typing import Any

from openai import OpenAI
from transformers import pipeline

from app.core.config import Settings


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def normalize_minutes(value: dict[str, Any] | None) -> dict[str, Any]:
    value = value or {}
    actions: list[dict[str, str]] = []
    raw_actions = value.get("actions")
    if isinstance(raw_actions, list):
        for action in raw_actions:
            if isinstance(action, dict):
                task = str(action.get("task", "")).strip()
                if task:
                    owner = str(action.get("owner") or "Unassigned").strip()
                    due = str(action.get("due") or "Not specified").strip()
                    actions.append({"owner": owner, "task": task, "due": due})
    return {
        "agenda": _strings(value.get("agenda")),
        "decisions": _strings(value.get("decisions")),
        "discussion": _strings(value.get("discussion")),
        "actions": actions,
    }


def reconcile_actions(minutes: dict[str, Any], transcript: str) -> dict[str, Any]:
    explicit: list[tuple[str, set[str]]] = []
    pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:will|shall|must|is going to)\s+([^.!?\n]+)"
    for owner, task in re.findall(pattern, transcript):
        words = {word for word in re.split(r"\W+", task.lower()) if len(word) > 3}
        explicit.append((owner, words))

    for action in minutes["actions"]:
        words = {
            word for word in re.split(r"\W+", action["task"].lower()) if len(word) > 3
        }
        evidence = next(
            (owner for owner, candidate in explicit if words & candidate),
            None,
        )
        if evidence:
            action["owner"] = evidence

    minutes["discussion"] = [
        item
        for item in minutes["discussion"]
        if not re.match(r"^no (specific |further )?discussion\.?$", item, re.IGNORECASE)
    ]

    # Fallback enrichment: Ensure MOM fields are not left completely empty when transcript content exists
    clean_lines = []
    if transcript:
        for line in transcript.splitlines():
            # Strip timestamp headers if present
            cleaned = re.sub(r"\[\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}\]\s*", "", line).strip()
            if cleaned and not cleaned.startswith("[SPEAKER_TURN]"):
                clean_lines.append(cleaned)

    if not minutes["discussion"] and clean_lines:
        minutes["discussion"] = clean_lines[:5]

    if not minutes["agenda"] and clean_lines:
        first_line = clean_lines[0]
        topic = first_line.split(":", 1)[-1].strip() if ":" in first_line else first_line
        minutes["agenda"] = [topic[:100]]

    if not minutes["decisions"] and clean_lines:
        summary_topic = ", ".join(minutes["agenda"]) if minutes["agenda"] else "meeting topics"
        minutes["decisions"] = [f"Reviewed and recorded notes on {summary_topic}."]

    return minutes


def _json_object(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"```(?:json)?|```", "", text, flags=re.IGNORECASE).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("The minutes model did not return a JSON object.")
    return json.loads(cleaned[start : end + 1])


@lru_cache(maxsize=4)
def _pipeline(task: str, model: str) -> Any:
    return pipeline(task, model=model)


class AnalysisService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def analyze(self, transcript: str) -> dict[str, Any]:
        minutes = self._minutes(transcript)
        mode = minutes.pop("mode")
        sentiment = self._sentiment(transcript)
        return {
            **minutes,
            "sentiment": sentiment,
            "mode": mode,
        }

    def _minutes(self, transcript: str) -> dict[str, Any]:
        prompt = (
            "Extract meeting minutes from the transcript below into JSON.\n"
            "Required schema:\n"
            "{\n"
            '  "agenda": ["list of primary topics discussed"],\n'
            '  "decisions": ["list of decisions, conclusions, or key outcomes"],\n'
            '  "discussion": ["list of main discussion points raised by participants"],\n'
            '  "actions": [{"owner": "name", "task": "description", "due": "time"}]\n'
            "}\n"
            "Return JSON only with these keys. Never invent facts.\n"
            "Transcript:\n" + transcript
        )
        provider = self.settings.minutes_provider.lower()
        if provider == "openai":
            if not self.settings.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY is required when MINUTES_PROVIDER=openai."
                )
            client = OpenAI(api_key=self.settings.openai_api_key)
            response = client.responses.create(
                model=self.settings.openai_summary_model,
                input=prompt,
            )
            raw = response.output_text
            mode = "openai"
        elif provider == "local":
            generator = _pipeline("text-generation", self.settings.local_minutes_model)
            output = generator(
                prompt,
                max_new_tokens=self.settings.local_minutes_max_tokens,
                do_sample=False,
            )
            raw = output[0]["generated_text"][len(prompt) :]
            mode = "local-qwen"
        else:
            raise ValueError(
                f"Unsupported minutes provider: {self.settings.minutes_provider}"
            )

        normalized = normalize_minutes(_json_object(raw))
        reconciled = reconcile_actions(normalized, transcript)
        return {
            **reconciled,
            "mode": mode,
        }

    def _sentiment(self, transcript: str) -> dict[str, Any]:
        speakers: dict[str, str] = {}
        for line in transcript.splitlines():
            name, separator, text = line.partition(":")
            if separator:
                name_clean = name.strip()
                text_clean = text.strip()
            else:
                name_clean = "All participants"
                text_clean = line.strip()

            if text_clean:
                existing = speakers.get(name_clean, "")
                speakers[name_clean] = f"{existing} {text_clean}".strip()

        classifier = _pipeline(
            "sentiment-analysis", self.settings.local_sentiment_model
        )
        total_words = sum(len(text.split()) for text in speakers.values()) or 1
        participants: list[dict[str, Any]] = []
        signed_score = 0.0

        for name, text in speakers.items():
            result = classifier(text[:4000], truncation=True)[0]
            positive = "POSITIVE" in result["label"].upper()
            score = float(result["score"])
            signed_score += score if positive else -score
            engagement = round(len(text.split()) / total_words * 100)
            participants.append(
                {
                    "name": name,
                    "sentiment": "Positive" if positive else "Negative",
                    "engagement": engagement,
                }
            )

        avg_score = signed_score / max(len(speakers), 1)
        if avg_score > 0.2:
            overall = "positive"
        elif avg_score < -0.2:
            overall = "negative"
        else:
            overall = "neutral"

        return {
            "overall": overall,
            "participants": participants,
            "model": self.settings.local_sentiment_model,
            "engagementMethod": "share-of-spoken-words",
        }
