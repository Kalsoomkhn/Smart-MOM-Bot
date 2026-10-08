"""Benchmark open-weight instruction models for structured meeting minutes."""

from __future__ import annotations

import argparse
import csv
import gc
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

MODELS = (
    "Qwen/Qwen2.5-1.5B-Instruct",
    "Qwen/Qwen2.5-3B-Instruct",
)
REQUIRED_KEYS = ("agenda", "decisions", "discussion", "actions")
MINUTES_SCHEMA = {
    "type": "object",
    "properties": {
        "agenda": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
        "decisions": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
        "discussion": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "task": {"type": "string"},
                    "due": {"type": "string"},
                },
                "required": ["owner", "task", "due"],
                "additionalProperties": False,
            },
            "maxItems": 8,
        },
    },
    "required": list(REQUIRED_KEYS),
    "additionalProperties": False,
}


@dataclass
class Result:
    meeting: str
    model: str
    runtime_seconds: float
    peak_gpu_memory_mb: float | None
    input_words: int
    output_words: int
    compression_ratio: float
    valid_json: bool
    valid_schema: bool
    nonempty_sections: int
    actions: int
    grounded_actions: int
    unsupported_dates: int
    error: str | None = None


def prompt_for(transcript: str) -> str:
    return (
        "Extract faithful meeting minutes from the transcript into JSON.\n"
        "Use exactly this schema:\n"
        '{"agenda":["topic"],"decisions":["decision"],'
        '"discussion":["point"],"actions":'
        '[{"owner":"name or Unassigned","task":"task",'
        '"due":"time or Not specified"}]}\n'
        "Only include decisions and actions explicitly supported by the transcript. "
        "Never invent owners, dates, decisions, or facts. Return JSON only.\n"
        f"Transcript:\n{transcript}"
    )


def parse_json(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"```(?:json)?|```", "", text, flags=re.IGNORECASE).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("No complete JSON object")
    value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise TypeError("Top-level result is not an object")
    return value


def schema_valid(value: dict[str, Any]) -> bool:
    if set(value) != set(REQUIRED_KEYS):
        return False
    if not all(isinstance(value[key], list) for key in REQUIRED_KEYS):
        return False
    if not all(
        isinstance(item, str)
        for key in ("agenda", "decisions", "discussion")
        for item in value[key]
    ):
        return False
    return all(
        isinstance(action, dict)
        and all(isinstance(action.get(key), str) for key in ("owner", "task", "due"))
        for action in value["actions"]
    )


def action_metrics(value: dict[str, Any], transcript: str) -> tuple[int, int, int]:
    transcript_lower = transcript.lower()
    actions = value.get("actions") if isinstance(value.get("actions"), list) else []
    grounded = 0
    unsupported_dates = 0
    for action in actions:
        if not isinstance(action, dict):
            continue
        task_words = {
            word
            for word in re.findall(r"[a-z0-9]+", str(action.get("task", "")).lower())
            if len(word) > 3
        }
        transcript_words = set(re.findall(r"[a-z0-9]+", transcript_lower))
        if task_words and len(task_words & transcript_words) / len(task_words) >= 0.6:
            grounded += 1
        due = str(action.get("due", "")).strip().lower()
        if due and due not in {"not specified", "none", "n/a", "unknown"}:
            if due not in transcript_lower:
                unsupported_dates += 1
    return len(actions), grounded, unsupported_dates


def write_results(results: list[Result], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = [asdict(result) for result in results]
    (output_dir / "results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    with (output_dir / "results.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transcript-dir",
        type=Path,
        default=Path("/content/smartmom-stt-results/transcripts/whisper-large-v3-turbo"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("/content/smartmom-mom-results"))
    parser.add_argument(
        "--models",
        nargs="+",
        default=list(MODELS),
        help="Hugging Face model IDs to benchmark.",
    )
    parser.add_argument(
        "--meetings",
        nargs="+",
        default=None,
        help="Optional transcript stems to benchmark, for example ES2004a IB4001.",
    )
    parser.add_argument(
        "--constrained-json",
        action="store_true",
        help="Enforce the minutes JSON schema with lm-format-enforcer.",
    )
    parser.add_argument("--max-new-tokens", type=int, default=700)
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

    transcripts = sorted(args.transcript_dir.glob("*.txt"))
    if args.meetings:
        requested_meetings = set(args.meetings)
        transcripts = [path for path in transcripts if path.stem in requested_meetings]
    if not transcripts:
        raise FileNotFoundError(f"No transcripts found in {args.transcript_dir}")

    results: list[Result] = []
    raw_dir = args.output_dir / "outputs"
    raw_dir.mkdir(parents=True, exist_ok=True)

    for model_id in args.models:
        print(f"Loading {model_id}", flush=True)
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.float16,
            device_map="auto",
            low_cpu_mem_usage=True,
        )
        generator = pipeline("text-generation", model=model, tokenizer=tokenizer)
        generation_kwargs: dict[str, Any] = {}
        if args.constrained_json:
            from lmformatenforcer import JsonSchemaParser
            from lmformatenforcer.integrations.transformers import (
                build_transformers_prefix_allowed_tokens_fn,
            )

            generation_kwargs["prefix_allowed_tokens_fn"] = (
                build_transformers_prefix_allowed_tokens_fn(
                    tokenizer,
                    JsonSchemaParser(MINUTES_SCHEMA),
                )
            )

        for transcript_path in transcripts:
            transcript = transcript_path.read_text(encoding="utf-8")
            # Keep the most recent context within a safe T4-friendly prompt budget.
            prompt = prompt_for(transcript[-48000:])
            messages = [
                {"role": "system", "content": "You produce grounded JSON meeting minutes."},
                {"role": "user", "content": prompt},
            ]
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
            started = time.perf_counter()
            error = None
            raw = ""
            value: dict[str, Any] = {}
            valid_json = False
            try:
                output = generator(
                    messages,
                    max_new_tokens=args.max_new_tokens,
                    do_sample=False,
                    return_full_text=False,
                    **generation_kwargs,
                )
                raw = output[0]["generated_text"]
                if isinstance(raw, list):
                    raw = raw[-1]["content"]
                value = parse_json(str(raw))
                valid_json = True
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            elapsed = time.perf_counter() - started
            (raw_dir / f"{model_id.split('/')[-1]}-{transcript_path.stem}.txt").write_text(
                str(raw), encoding="utf-8"
            )
            actions, grounded, unsupported_dates = action_metrics(value, transcript)
            result = Result(
                meeting=transcript_path.stem,
                model=model_id,
                runtime_seconds=elapsed,
                peak_gpu_memory_mb=(
                    torch.cuda.max_memory_allocated() / 1024**2
                    if torch.cuda.is_available()
                    else None
                ),
                input_words=len(transcript.split()),
                output_words=len(str(raw).split()),
                compression_ratio=len(str(raw).split()) / max(len(transcript.split()), 1),
                valid_json=valid_json,
                valid_schema=valid_json and schema_valid(value),
                nonempty_sections=sum(bool(value.get(key)) for key in REQUIRED_KEYS),
                actions=actions,
                grounded_actions=grounded,
                unsupported_dates=unsupported_dates,
                error=error,
            )
            results.append(result)
            print(asdict(result), flush=True)

        del generator, model, tokenizer
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    write_results(results, args.output_dir)


if __name__ == "__main__":
    main()
