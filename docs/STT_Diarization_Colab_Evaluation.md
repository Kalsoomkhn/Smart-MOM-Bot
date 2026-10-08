# SmartMOM Whisper and Sortformer evaluation

**Status:** Benchmark implementation complete; Colab GPU measurements pending.  
**Evaluation date:** 7 October 2026  
**Notebook:** `experiments/SmartMOM_STT_Diarization_Colab.ipynb`

## Objective

This experiment addresses the two weakest components in the current pipeline:
speech-to-text and speaker diarization. The baseline uses Whisper Tiny with
automatic language detection and alternating two-speaker labels. Across five
AMI meetings it produced 93.24% macro WER and approximately 81.00% macro DER.

The candidate comparison is:

| Component | Candidate | Purpose |
| --- | --- | --- |
| STT | `openai/whisper-base` | Low-resource accuracy and speed baseline |
| STT | `openai/whisper-large-v3-turbo` | Higher-capacity multilingual candidate |
| Diarization | `nvidia/diar_sortformer_4spk-v1` | Persistent labels for up to four speakers |

Whisper Base has approximately 73 million parameters and is Apache-2.0. Turbo
uses a 1.62 GB weights file and is MIT-licensed. Sortformer v1 has approximately
100 million parameters, accepts mono 16 kHz audio, and uses CC BY-NC 4.0. The
Sortformer license permits the research evaluation but is a blocker for
commercial deployment without a different license or model.

Sources:

- [Whisper Base model card](https://huggingface.co/openai/whisper-base)
- [Whisper Large V3 Turbo model card](https://huggingface.co/openai/whisper-large-v3-turbo)
- [NVIDIA Sortformer v1 model card](https://huggingface.co/nvidia/diar_sortformer_4spk-v1)
- [AMI Meeting Corpus](https://groups.inf.ed.ac.uk/ami/corpus/)

## Dataset and controls

The comparison reuses `ES2004a`, `EN2002a`, `EN2003a`, `IB4001`, and `IN1009`
from the baseline. Every recording is the official AMI 16 kHz mono Mix-Headset
stream, and the official manual word and speaker-segment annotations provide
references.

Controls applied to both Whisper candidates:

- complete recordings, not selected easy clips;
- identical 30-second chunk length and batch size;
- English transcription forced for both models;
- identical lowercase alphanumeric normalization;
- the same GPU runtime within a comparison run;
- failures retained in results rather than excluded.

Forced English is deliberate because the baseline's automatic language
detection failed catastrophically on `IN1009`. It means this experiment does
not measure multilingual language identification.

## STT metrics and decision rule

The primary metric is word error rate (WER). The report also records runtime,
real-time factor (runtime divided by audio duration), peak allocated GPU memory,
and reference/hypothesis word counts.

Turbo is selected only if it:

1. completes all five meetings on the selected Colab GPU;
2. reduces macro WER by at least 10% relative to Whisper Base;
3. has no catastrophic repetition or language failure; and
4. has a real-time factor suitable for the deployment target.

Otherwise, Base remains the low-resource candidate. These thresholds are set
before observing results to avoid choosing a model from anecdotal transcripts.

## Diarization metrics and decision rule

Sortformer is scored on the first 300 seconds of every meeting. DER uses a
0.25-second collar and includes overlapping speech. Runtime, real-time factor,
peak GPU memory, and failed meetings are also retained.

The excerpt scope is required because NVIDIA documents the following limits:

- offline rather than streaming inference;
- a maximum of four speakers;
- reduced performance for non-English or noisy out-of-domain audio;
- an approximately 12-minute maximum even on an RTX A6000 with 48 GB VRAM.

The project recordings last 17.5–37.3 minutes. Full-length deployment would
therefore need windowing and cross-window speaker identity stitching. This
benchmark evaluates diarization quality before that extra engineering work.

Sortformer advances to a pipeline prototype only if:

1. it completes every five-minute excerpt;
2. macro DER is below 30%;
3. no individual meeting exceeds 50% DER; and
4. its non-commercial license is acceptable for the intended FYP/demo scope.

## Required result tables

### Speech-to-text

| Meeting | Base WER | Turbo WER | Base RTF | Turbo RTF | Base peak MB | Turbo peak MB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ES2004a | Pending | Pending | Pending | Pending | Pending | Pending |
| EN2002a | Pending | Pending | Pending | Pending | Pending | Pending |
| EN2003a | Pending | Pending | Pending | Pending | Pending | Pending |
| IB4001 | Pending | Pending | Pending | Pending | Pending | Pending |
| IN1009 | Pending | Pending | Pending | Pending | Pending | Pending |
| **Macro mean** | **Pending** | **Pending** | **Pending** | **Pending** | **Pending** | **Pending** |

### Speaker diarization

| Meeting | Excerpt | Sortformer DER | RTF | Peak MB | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| ES2004a | 300 s | Pending | Pending | Pending | Pending |
| EN2002a | 300 s | Pending | Pending | Pending | Pending |
| EN2003a | 300 s | Pending | Pending | Pending | Pending |
| IB4001 | 300 s | Pending | Pending | Pending | Pending |
| IN1009 | 300 s | Pending | Pending | Pending | Pending |
| **Macro mean** |  | **Pending** | **Pending** | **Pending** |  |

## Reproducibility and evidence

The benchmark downloads audio and annotations directly from AMI, stores raw
transcripts and RTTM output, and writes CSV/JSON results plus the Python,
platform, CUDA, PyTorch, and GPU environment. Results must not be copied into
the main pipeline report unless those raw artifacts are retained.

The benchmark code has local unit coverage for normalization, AMI annotation
parsing/trimming, and Sortformer output normalization. It cannot validate model
inference without the Colab CUDA/NeMo runtime.

## Current conclusion

No candidate is selected yet. The code and decision rules are ready, but any
accuracy or speed conclusion before GPU execution would be unsupported. After
the result archive is returned, the pending tables can be populated and the
selected STT and diarization models can be tested together before integration.
