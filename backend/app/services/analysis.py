import json
import re
from functools import lru_cache

from openai import OpenAI
from transformers import pipeline

from app.core.config import Settings


def _strings(value) -> list[str]:
    return [item.strip() for item in value if isinstance(item, str) and item.strip()] if isinstance(value, list) else []


def normalize_minutes(value: dict | None) -> dict:
    value = value or {}
    actions = []
    for action in value.get("actions", []) if isinstance(value.get("actions"), list) else []:
        task = str(action.get("task", "")).strip() if isinstance(action, dict) else ""
        if task: actions.append({"owner": str(action.get("owner") or "Unassigned"), "task": task, "due": str(action.get("due") or "Not specified")})
    return {"agenda": _strings(value.get("agenda")), "decisions": _strings(value.get("decisions")), "discussion": _strings(value.get("discussion")), "actions": actions}


def reconcile_actions(minutes: dict, transcript: str) -> dict:
    explicit = []
    pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:will|shall|must|is going to)\s+([^.!?\n]+)"
    for owner, task in re.findall(pattern, transcript):
        explicit.append((owner, {word for word in re.split(r"\W+", task.lower()) if len(word) > 3}))
    for action in minutes["actions"]:
        words = {word for word in re.split(r"\W+", action["task"].lower()) if len(word) > 3}
        evidence = next((owner for owner, candidate in explicit if words & candidate), None)
        if evidence: action["owner"] = evidence
    minutes["discussion"] = [x for x in minutes["discussion"] if not re.match(r"^no (specific |further )?discussion\.?$", x, re.I)]
    return minutes


def _json_object(text: str) -> dict:
    cleaned = re.sub(r"```(?:json)?|```", "", text, flags=re.I).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start: raise ValueError("The minutes model did not return a JSON object.")
    return json.loads(cleaned[start:end + 1])


@lru_cache(maxsize=4)
def _pipeline(task: str, model: str):
    return pipeline(task, model=model)


class AnalysisService:
    def __init__(self, settings: Settings): self.settings = settings

    def analyze(self, transcript: str) -> dict:
        minutes = self._minutes(transcript)
        mode = minutes.pop("mode")
        return {**minutes, "sentiment": self._sentiment(transcript), "mode": mode}

    def _minutes(self, transcript: str) -> dict:
        prompt = 'Return JSON only with keys agenda:string[], decisions:string[], discussion:string[], actions:[{owner:string,task:string,due:string}]. Never invent facts. Transcript:\n' + transcript
        if self.settings.minutes_provider.lower() == "openai":
            if not self.settings.openai_api_key: raise ValueError("OPENAI_API_KEY is required when MINUTES_PROVIDER=openai.")
            response = OpenAI(api_key=self.settings.openai_api_key).responses.create(model=self.settings.openai_summary_model, input=prompt)
            raw, mode = response.output_text, "openai"
        elif self.settings.minutes_provider.lower() == "local":
            generator = _pipeline("text-generation", self.settings.local_minutes_model)
            output = generator(prompt, max_new_tokens=self.settings.local_minutes_max_tokens, do_sample=False)
            raw, mode = output[0]["generated_text"][len(prompt):], "local-qwen"
        else: raise ValueError(f"Unsupported minutes provider: {self.settings.minutes_provider}")
        return {**reconcile_actions(normalize_minutes(_json_object(raw)), transcript), "mode": mode}

    def _sentiment(self, transcript: str) -> dict:
        speakers: dict[str, str] = {}
        for line in transcript.splitlines():
            name, separator, text = line.partition(":")
            name, text = (name.strip(), text.strip()) if separator else ("All participants", line.strip())
            if text: speakers[name] = f"{speakers.get(name, '')} {text}".strip()
        classifier = _pipeline("sentiment-analysis", self.settings.local_sentiment_model)
        total = sum(len(text.split()) for text in speakers.values()) or 1
        participants, signed = [], 0.0
        for name, text in speakers.items():
            result = classifier(text[:4000], truncation=True)[0]
            positive, score = "POSITIVE" in result["label"].upper(), float(result["score"])
            signed += score if positive else -score
            participants.append({"name": name, "sentiment": "Positive" if positive else "Negative", "engagement": round(len(text.split()) / total * 100)})
        average = signed / max(len(speakers), 1)
        return {"overall": "positive" if average > .2 else "negative" if average < -.2 else "neutral", "participants": participants, "model": self.settings.local_sentiment_model, "engagementMethod": "share-of-spoken-words"}
