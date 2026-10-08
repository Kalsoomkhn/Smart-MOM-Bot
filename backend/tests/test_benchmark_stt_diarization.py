from pathlib import Path

from experiments.benchmark_stt_diarization import (
    Segment,
    normalize_text,
    parse_reference_segments,
    parse_reference_words,
    parse_sortformer_segments,
)


def test_normalizes_transcript_for_wer():
    assert normalize_text("Hello, Speaker's WORLD!") == "hello speakers world"


def test_normalizes_sortformer_output_shapes():
    strings = parse_sortformer_segments([["0.00 1.25 speaker_0", "1.25 2.00 speaker_1"]])
    mappings = parse_sortformer_segments([{"start": 0.0, "end": 1.0, "speaker": "speaker_0"}])

    assert strings == [Segment(0.0, 1.25, "speaker_0"), Segment(1.25, 2.0, "speaker_1")]
    assert mappings == [Segment(0.0, 1.0, "speaker_0")]


def test_parses_and_trims_ami_annotations(tmp_path: Path):
    words_dir = tmp_path / "words"
    segments_dir = tmp_path / "segments"
    words_dir.mkdir()
    segments_dir.mkdir()
    (words_dir / "ES2004a.A.words.xml").write_text(
        '<nite:root xmlns:nite="urn:nite"><w starttime="1.0">world</w>'
        '<w starttime="0.0">Hello</w></nite:root>',
        encoding="utf-8",
    )
    (segments_dir / "ES2004a.A.segments.xml").write_text(
        '<nite:root xmlns:nite="urn:nite">'
        '<segment transcriber_start="0.0" transcriber_end="4.0" />'
        '<segment transcriber_start="5.0" transcriber_end="8.0" />'
        "</nite:root>",
        encoding="utf-8",
    )

    assert parse_reference_words(tmp_path, "ES2004a") == "Hello world"
    assert parse_reference_segments(tmp_path, "ES2004a", 6.0) == [
        Segment(0.0, 4.0, "A"),
        Segment(5.0, 6.0, "A"),
    ]
