"""Colab-oriented Whisper and Sortformer evaluation on AMI meetings."""

from __future__ import annotations

import argparse
import csv
import gc
import importlib.metadata
import json
import platform
import re
import subprocess
import time
import urllib.request
import wave
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_MEETINGS = ("ES2004a", "EN2002a", "EN2003a", "IB4001", "IN1009")
WHISPER_MODELS = ("openai/whisper-base", "openai/whisper-large-v3-turbo")
SORTFORMER_MODEL = "nvidia/diar_sortformer_4spk-v1"
AMI_AUDIO_URL = (
    "https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus/"
    "{meeting}/audio/{meeting}.Mix-Headset.wav"
)
AMI_ANNOTATIONS_URL = (
    "https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip"
)


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    speaker: str


@dataclass
class Result:
    component: str
    meeting: str
    model: str
    audio_seconds: float
    runtime_seconds: float
    real_time_factor: float
    peak_gpu_memory_mb: float | None
    wer: float | None = None
    der: float | None = None
    reference_words: int | None = None
    hypothesis_words: int | None = None
    error: str | None = None


def download(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size:
        return destination
    print(f"Downloading {url} -> {destination}")
    urllib.request.urlretrieve(url, destination)
    return destination


def prepare_ami(work_dir: Path, meetings: Iterable[str]) -> tuple[Path, Path]:
    audio_dir = work_dir / "audio"
    annotation_dir = work_dir / "annotations"
    archive = work_dir / "ami_public_manual_1.6.2.zip"

    for meeting in meetings:
        download(AMI_AUDIO_URL.format(meeting=meeting), audio_dir / f"{meeting}.wav")

    if not annotation_dir.exists():
        download(AMI_ANNOTATIONS_URL, archive)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(annotation_dir)
    return audio_dir, annotation_dir


def _annotation_files(annotation_dir: Path, meeting: str, category: str) -> list[Path]:
    return sorted(annotation_dir.rglob(f"{meeting}.*.{category}.xml"))


def _speaker_from_filename(path: Path, meeting: str) -> str:
    suffix = path.name.removeprefix(f"{meeting}.")
    return suffix.split(".", maxsplit=1)[0]


def parse_reference_words(annotation_dir: Path, meeting: str) -> str:
    words: list[tuple[float, str]] = []
    for path in _annotation_files(annotation_dir, meeting, "words"):
        for node in ET.parse(path).getroot().iter():
            if not node.tag.endswith("w") or not node.text:
                continue
            start = node.attrib.get("starttime")
            if start is not None:
                words.append((float(start), node.text))
    if not words:
        raise FileNotFoundError(f"No AMI word annotations found for {meeting}")
    return " ".join(text for _, text in sorted(words))


def parse_reference_segments(
    annotation_dir: Path, meeting: str, max_seconds: float | None = None
) -> list[Segment]:
    segments: list[Segment] = []
    for path in _annotation_files(annotation_dir, meeting, "segments"):
        speaker = _speaker_from_filename(path, meeting)
        for node in ET.parse(path).getroot().iter():
            if not node.tag.endswith("segment"):
                continue
            start = float(node.attrib["transcriber_start"])
            end = float(node.attrib["transcriber_end"])
            if max_seconds is not None:
                if start >= max_seconds:
                    continue
                end = min(end, max_seconds)
            if end > start:
                segments.append(Segment(start, end, speaker))
    if not segments:
        raise FileNotFoundError(f"No AMI segment annotations found for {meeting}")
    return sorted(segments, key=lambda item: (item.start, item.end, item.speaker))


def normalize_text(text: str) -> str:
    text = text.lower().replace("'", "")
    return " ".join(re.findall(r"[a-z0-9]+", text))


def audio_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def make_clip(source: Path, destination: Path, seconds: int) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size:
        return destination
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-t",
            str(seconds),
            "-ac",
            "1",
            "-ar",
            "16000",
            str(destination),
        ],
        check=True,
    )
    return destination


def _gpu_peak_mb(torch_module: Any) -> float | None:
    if not torch_module.cuda.is_available():
        return None
    return torch_module.cuda.max_memory_allocated() / (1024**2)


def run_whisper(
    audio_dir: Path,
    annotation_dir: Path,
    meetings: Iterable[str],
    output_dir: Path,
) -> list[Result]:
    import torch
    from jiwer import wer
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    results: list[Result] = []

    for model_id in WHISPER_MODELS:
        print(f"\nLoading {model_id}")
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id,
            torch_dtype=dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True,
        ).to(device)
        processor = AutoProcessor.from_pretrained(model_id)
        asr = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            chunk_length_s=30,
            batch_size=8,
            torch_dtype=dtype,
            device=device,
        )

        for meeting in meetings:
            audio_path = audio_dir / f"{meeting}.wav"
            duration = audio_duration(audio_path)
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.reset_peak_memory_stats()
                started = time.perf_counter()
                prediction = asr(
                    str(audio_path),
                    return_timestamps=True,
                    generate_kwargs={"task": "transcribe", "language": "en"},
                )
                elapsed = time.perf_counter() - started
                reference = normalize_text(parse_reference_words(annotation_dir, meeting))
                hypothesis = normalize_text(prediction["text"])
                result = Result(
                    component="stt",
                    meeting=meeting,
                    model=model_id,
                    audio_seconds=duration,
                    runtime_seconds=elapsed,
                    real_time_factor=elapsed / duration,
                    peak_gpu_memory_mb=_gpu_peak_mb(torch),
                    wer=wer(reference, hypothesis),
                    reference_words=len(reference.split()),
                    hypothesis_words=len(hypothesis.split()),
                )
                transcript_path = output_dir / "transcripts" / model_id.split("/")[-1]
                transcript_path.mkdir(parents=True, exist_ok=True)
                (transcript_path / f"{meeting}.txt").write_text(
                    prediction["text"].strip() + "\n", encoding="utf-8"
                )
            except Exception as exc:  # Continue the matrix and record failures.
                result = Result(
                    component="stt",
                    meeting=meeting,
                    model=model_id,
                    audio_seconds=duration,
                    runtime_seconds=0,
                    real_time_factor=0,
                    peak_gpu_memory_mb=_gpu_peak_mb(torch),
                    error=f"{type(exc).__name__}: {exc}",
                )
            results.append(result)
            print(asdict(result))

        del asr, processor, model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    return results


def parse_sortformer_segments(raw: Any) -> list[Segment]:
    """Normalize NeMo's string/tuple/dict segment representations."""
    if isinstance(raw, list) and len(raw) == 1 and isinstance(raw[0], list):
        raw = raw[0]
    parsed: list[Segment] = []
    for item in raw:
        if isinstance(item, str):
            start, end, speaker = item.split()[:3]
        elif isinstance(item, dict):
            start = item.get("start", item.get("begin"))
            end = item["end"]
            speaker = item.get("speaker", item.get("label"))
        else:
            start, end, speaker = item[:3]
        parsed.append(Segment(float(start), float(end), str(speaker)))
    return parsed


def diarization_error_rate(reference: list[Segment], hypothesis: list[Segment]) -> float:
    from pyannote.core import Annotation
    from pyannote.core import Segment as PyannoteSegment
    from pyannote.metrics.diarization import DiarizationErrorRate

    ref = Annotation()
    hyp = Annotation()
    for index, segment in enumerate(reference):
        ref[PyannoteSegment(segment.start, segment.end), index] = segment.speaker
    for index, segment in enumerate(hypothesis):
        hyp[PyannoteSegment(segment.start, segment.end), index] = segment.speaker
    metric = DiarizationErrorRate(collar=0.25, skip_overlap=False)
    return float(metric(ref, hyp))


def run_sortformer(
    audio_dir: Path,
    annotation_dir: Path,
    meetings: Iterable[str],
    output_dir: Path,
    excerpt_seconds: int,
) -> list[Result]:
    import torch
    from nemo.collections.asr.models import SortformerEncLabelModel

    model = SortformerEncLabelModel.from_pretrained(SORTFORMER_MODEL)
    model.eval()
    if torch.cuda.is_available():
        model = model.cuda()

    results: list[Result] = []
    for meeting in meetings:
        source = audio_dir / f"{meeting}.wav"
        clip = make_clip(source, output_dir / "clips" / f"{meeting}.wav", excerpt_seconds)
        duration = audio_duration(clip)
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
            started = time.perf_counter()
            raw_segments = model.diarize(audio=str(clip), batch_size=1)
            elapsed = time.perf_counter() - started
            hypothesis = parse_sortformer_segments(raw_segments)
            reference = parse_reference_segments(annotation_dir, meeting, duration)
            der = diarization_error_rate(reference, hypothesis)
            result = Result(
                component="diarization",
                meeting=meeting,
                model=SORTFORMER_MODEL,
                audio_seconds=duration,
                runtime_seconds=elapsed,
                real_time_factor=elapsed / duration,
                peak_gpu_memory_mb=_gpu_peak_mb(torch),
                der=der,
            )
            rttm_dir = output_dir / "rttm"
            rttm_dir.mkdir(parents=True, exist_ok=True)
            with (rttm_dir / f"{meeting}.rttm").open("w", encoding="utf-8") as handle:
                for segment in hypothesis:
                    handle.write(
                        f"SPEAKER {meeting} 1 {segment.start:.3f} "
                        f"{segment.end - segment.start:.3f} <NA> <NA> "
                        f"{segment.speaker} <NA> <NA>\n"
                    )
        except Exception as exc:  # Continue the matrix and record failures.
            result = Result(
                component="diarization",
                meeting=meeting,
                model=SORTFORMER_MODEL,
                audio_seconds=duration,
                runtime_seconds=0,
                real_time_factor=0,
                peak_gpu_memory_mb=_gpu_peak_mb(torch),
                error=f"{type(exc).__name__}: {exc}",
            )
        results.append(result)
        print(asdict(result))
    return results


def write_results(results: list[Result], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = [asdict(result) for result in results]
    (output_dir / "results.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    with (output_dir / "results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    environment = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {
            package: importlib.metadata.version(package)
            for package in (
                "accelerate",
                "jiwer",
                "nemo_toolkit",
                "pyannote.core",
                "pyannote.metrics",
                "torch",
                "transformers",
            )
        },
    }
    try:
        import torch

        environment.update(
            {
                "torch": torch.__version__,
                "cuda_available": torch.cuda.is_available(),
                "cuda": torch.version.cuda,
                "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            }
        )
    except ImportError:
        pass
    (output_dir / "environment.json").write_text(
        json.dumps(environment, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-dir", type=Path, default=Path("/content/smartmom-evaluation"))
    parser.add_argument("--output-dir", type=Path, default=Path("/content/smartmom-results"))
    parser.add_argument("--meetings", nargs="+", default=list(DEFAULT_MEETINGS))
    parser.add_argument("--component", choices=("all", "stt", "diarization"), default="all")
    parser.add_argument("--diarization-seconds", type=int, default=300)
    args = parser.parse_args()

    audio_dir, annotation_dir = prepare_ami(args.work_dir, args.meetings)
    results: list[Result] = []
    if args.component in {"all", "stt"}:
        results.extend(run_whisper(audio_dir, annotation_dir, args.meetings, args.output_dir))
    if args.component in {"all", "diarization"}:
        results.extend(
            run_sortformer(
                audio_dir,
                annotation_dir,
                args.meetings,
                args.output_dir,
                args.diarization_seconds,
            )
        )
    write_results(results, args.output_dir)


if __name__ == "__main__":
    main()
