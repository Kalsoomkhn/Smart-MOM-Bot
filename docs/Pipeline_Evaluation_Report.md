# SmartMOM current-pipeline evaluation: AMI meeting sample

**Evaluation date:** 29 September 2026  
**Sample:** five complete AMI meetings, 17.5–37.3 minutes, 16 kHz mono Mix-Headset audio.  
**Purpose:** evaluate the configured ASR path against human word/speaker annotations, then test the configured Qwen model family on the pipeline's extraction prompt.

## Colab candidate-model experiment update (8 October 2026)

The follow-up Colab experiment completed successfully on a T4 GPU using the same five full AMI Mix-Headset recordings for Whisper and the first 300 seconds of each recording for Sortformer. These measurements supersede vendor-reported performance for this project-specific comparison.

### Whisper Base versus Whisper Large-v3-Turbo

| Meeting | Duration (min) | Base WER | Base RTF | Turbo WER | Turbo RTF |
|---|---:|---:|---:|---:|---:|
| ES2004a | 17.5 | 80.93% | 0.074 | 27.89% | 0.051 |
| EN2002a | 35.7 | 90.91% | 0.117 | 42.94% | 0.081 |
| EN2003a | 37.3 | 47.72% | 0.094 | 23.97% | 0.057 |
| IB4001 | 29.7 | 36.14% | 0.076 | 23.97% | 0.053 |
| IN1009 | 20.9 | 83.78% | 0.099 | 36.32% | 0.052 |
| **Macro mean** | **28.2** | **67.89%** | **0.092** | **31.02%** | **0.059** |

The reference-word-weighted WER was **66.94% for Base** and **31.81% for Turbo**. Turbo reduced macro WER by **36.87 percentage points** (a **54.3% relative reduction**) and was approximately **1.57 times faster** by mean real-time factor. Peak allocated GPU memory was approximately **1.20 GB for Base** and **3.21 GB for Turbo**. Total measured inference time across the five recordings was approximately **13.3 minutes for Base** and **8.6 minutes for Turbo**, excluding dependency installation and model download.

The TensorFlow message saying CUDA drivers were unavailable was emitted by an optional TensorFlow initialization path. It did not describe the PyTorch benchmark: the Transformers pipeline explicitly selected `cuda:0`, and the measured CUDA allocations confirm GPU execution.

### NVIDIA Sortformer

| Meeting | Evaluated audio | DER | Runtime | RTF |
|---|---:|---:|---:|---:|
| ES2004a | 300 s | 34.02% | 34.12 s | 0.114 |
| EN2002a | 300 s | 31.47% | 1.89 s | 0.006 |
| EN2003a | 300 s | 30.56% | 1.92 s | 0.006 |
| IB4001 | 300 s | 16.97% | 1.88 s | 0.006 |
| IN1009 | 300 s | 23.25% | 1.87 s | 0.006 |
| **Macro mean** | **300 s** | **27.25%** | **8.34 s** | **0.028** |

Peak allocated GPU memory was approximately **3.70 GB**. The first recording includes model initialization overhead; the remaining recordings processed 300 seconds of audio in about 1.9 seconds each. DER used overlap, a 0.25-second collar, and optimal speaker mapping. The test does not remove Sortformer's deployment constraints: the v1 checkpoint supports at most four speakers, is non-streaming, has a practical long-audio limit reported by NVIDIA, and is licensed **CC BY-NC 4.0**.

### Candidate decision

- Select **Whisper Large-v3-Turbo** over Whisper Base for the next integration prototype. It was both substantially more accurate and faster on every tested meeting, at the cost of roughly 2 GB more peak GPU memory.
- Treat **Sortformer v1 as a research benchmark only**, not the default commercial-production choice. Its measured diarization accuracy is much better than the current alternating-label baseline, but the non-commercial license, four-speaker ceiling, non-streaming operation, and long-recording limitation are material blockers.
- Before integration, evaluate at least one commercially usable diarization alternative with the same scorer and audio clips, then run the selected STT/diarization pair end-to-end before judging Qwen/Llama MoM quality.

### Qwen2.5-1.5B-Instruct Colab pilot

A targeted full-precision Transformers pilot ran `Qwen/Qwen2.5-1.5B-Instruct` on the Whisper Large-v3-Turbo transcripts for ES2004a and IB4001. The first run, including model loading after download, finished in 56 seconds; cached generation took 5.65 seconds and 6.66 seconds respectively. Peak allocated GPU memory was 4.01 GB for ES2004a and 5.67 GB for IB4001.

| Meeting | Input words | Output words | Valid JSON | Exact schema | Non-empty sections | Actions |
|---|---:|---:|---:|---:|---:|---:|
| ES2004a | 2,254 | 46 | Yes | No | 2/4 | 0 |
| IB4001 | 4,022 | 36 | Yes | No | 2/4 | 0 |

Both responses were parseable JSON but violated the requested schema. ES2004a returned objects instead of strings in `discussion` and introduced the participant names John, Emily, Tom, and Lucas, none of which appears in the supplied transcript. IB4001 returned a decision as an action-shaped object rather than a decision string. Its November 2 date does appear in the transcript, but the response compressed a lengthy room-allocation discussion into one vague task and omitted explicit action items. Therefore, this pilot achieved **100% JSON parse success but 0% exact-schema success** and materially under-extracted the meetings.

The pilot is sufficient to show that the exact Hugging Face model runs comfortably on a T4 and is fast after loading, but it is not sufficient for model selection. Before integration, test a stronger instruction model (starting with Qwen2.5-3B-Instruct), add constrained JSON/schema generation or a repair pass, and score field-level precision/recall and unsupported claims on all five meetings.

### Qwen2.5-3B-Instruct constrained-JSON pilot

The follow-up used `Qwen/Qwen2.5-3B-Instruct` in FP16 with LM Format Enforcer token filtering against an exact JSON Schema. Transformers had to be pinned below version 5 because the current LM Format Enforcer Transformers integration imports an API removed by the newer Colab package. The model weights occupied about 6.17 GB on disk.

| Meeting | Token limit | Runtime | Peak GPU | Valid JSON | Exact schema | Result |
|---|---:|---:|---:|---:|---:|---|
| ES2004a | 700 | 83.20 s | 7.13 GB | No | No | Truncated inside one repetitive `decisions` string. |
| ES2004a retry | 1,200 | 150.41 s | 7.13 GB | No | No | Still truncated inside the same expanding string. |
| IB4001 | 700 | 18.36 s | 9.27 GB | Yes | Yes | Three populated sections and one action, but the action failed the lexical-grounding threshold. |

Constraining token choices improved structural compliance only when generation completed; it did not guarantee a complete document or semantic correctness. The ES2004a response repeatedly promoted discussion and product requirements into decisions and continued expanding a single string until the token limit. Adding an eight-item maximum to every array did not help because the repetition occurred inside one string value. IB4001 produced concise, valid JSON, but its broad action—finalizing organization, equipment placement, and office assignments—was not grounded closely enough to pass the evaluator's lexical-overlap threshold.

The 3B constrained configuration is therefore **not selected for integration** in its current form. Compared with the 1.5B pilot it used more GPU memory, was substantially slower, and still completed only one of two meetings successfully. The next MoM experiment should control both structure and value length: summarize the transcript hierarchically in chunks, cap each field's characters/tokens, require evidence spans for every decision/action, and apply validation plus targeted retry rather than increasing the global generation limit.

## Executive summary

The evaluation completed five full recordings covering scenario-based product design, meeting-support UI/search, academic event planning, office relocation, and a technical speech-processing discussion. ASR results were poor: macro WER was **93.24%** (micro WER **77.97%**). The approximate diarization error rate averaged **81.00%**. The current code assigns only two speaker labels by alternating ASR chunk index, while AMI references have three or four participants; this produces severe speaker confusion.

Qwen MoMs were generated with the same Qwen2.5 1.5B base model in Q4_K_M GGUF through local Ollama, using the app's JSON prompt, zero temperature, and 700-token limit. This quantized local runner was used because the configured Python full-precision model could not safely be loaded in the available RAM; it approximates the configured model but is not an exact run of the Python model code. One of five outputs was truncated and failed JSON parsing. The remaining outputs contain unsupported decisions, owners, or dates; one meeting received generic placeholders instead of a useful summary.

The sample spans meeting length and topic, but **not recording-condition variety**: all selected audio is the corpus's Mix-Headset stream. These are research corpus recordings, not the project's own demos or production meetings. Scores are a small-sample benchmark, not a general performance guarantee.

## Source, selection, and scoring method

Audio and human annotations come from the AMI Meeting Corpus and a Hugging Face mirror that reproduces corpus audio/annotations. AMI publishes its released signals and transcripts under CC BY 4.0; attribution and corpus citation are required. See the [official AMI corpus](https://groups.inf.ed.ac.uk/ami/corpus/), [official download/annotation page](https://groups.inf.ed.ac.uk/ami/download/), and [mirror dataset card and layout](https://huggingface.co/datasets/ggfox00000/dia-AMICorpus-all). The mirror's `Mix-Headset` files are mixed close-talking headset channels; all **five selected** files use this single stream. Dataset audio is 16 kHz mono. Four recordings are naturally occurring AMI sessions and one is a scenario meeting.

The AMI word XML was sorted by timestamp and normalized to lowercase alphanumeric tokens. WER is Levenshtein edits divided by reference words; overlap is serialized by word start time, which can add error for simultaneous speech. Diarization is an approximate frame-based DER at 100 ms resolution, with a one-to-one mapping from predicted labels to reference participants, overlap counted, and no forgiveness collar. The pipeline's alternating chunk labels were used as-is. Reported 1–5 ratings use explicit thresholds for ASR/diarization and reviewer judgment against the reference transcript for extraction, MoM quality, and faithfulness.

**Rating guide:** ASR: 5 ≤10% WER, 4 ≤20%, 3 ≤30%, 2 ≤40%, 1 >40%; diarization: 5 ≤10% DER, 4 ≤20%, 3 ≤30%, 2 ≤50%, 1 >50%. For information extraction, MoM quality, and faithfulness: 1 = unusable/mostly unsupported; 3 = partially useful with material gaps; 5 = accurate, complete, and grounded. The overall per-meeting rating is the unweighted mean of the five component ratings.

## Results summary

| Meeting | Topic | Length | Recording condition | WER | DER | ASR | Diarization | Extraction | MoM | Faithfulness | Overall |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ES2004a | Scenario project kickoff: designing an original, user-friendly remote control. | 17.5 min | Mix-Headset, 16 kHz mono | 50.89% | 85.13% | 1 | 1 | 2 | 2 | 1 | 1.4 |
| EN2002a | Meeting-support interface discussion: browser/search navigation, meeting and topic views, and summary/transcript usability (topic inferred from the reference transcript). | 35.7 min | Mix-Headset, 16 kHz mono | 74.32% | 83.43% | 1 | 1 | 2 | 2 | 2 | 1.6 |
| EN2003a | Academic event planning: call for abstracts/titles, poster session, invitations, and deadlines (inferred from the reference transcript). | 37.3 min | Mix-Headset, 16 kHz mono | 32.34% | 71.94% | 2 | 1 | 2 | 1 | 2 | 1.6 |
| IB4001 | Office relocation: moving to a larger building and allocating rooms/offices and equipment. | 29.7 min | Mix-Headset, 16 kHz mono | 50.00% | 76.53% | 1 | 1 | 3 | 2 | 2 | 1.8 |
| IN1009 | Technical discussion/interview: speech pitch and speaker/location clustering, with MATLAB/C++ implementation (inferred from the reference transcript). | 20.9 min | Mix-Headset, 16 kHz mono | 258.64% | 87.96% | 1 | 1 | 1 | 1 | 1 | 1.0 |

### Component averages

| Component | Mean 1–5 rating | Additional metric | Interpretation |
|---|---:|---:|---|
| ASR / transcript | 1.20 | macro WER 93.24% (micro 77.97%) | Lowest-performing component; one language-detection failure caused extreme repeated output. |
| Speaker diarization | 1.00 | macro DER 81.00% | Poor; alternating chunk labels cannot track four persistent participants. |
| Information extraction | 2.00 | Reviewer score | Some topical capture, but topics are mislabeled as decisions and unsupported actions/dates are introduced. |
| MoM quality | 1.60 | 1/5 parse failures | Weak; one invalid/truncated response and one placeholder-only response. |
| Faithfulness / hallucination control | 1.60 | Reviewer score | Weak; fabricated owners/dates and unsupported decision framing recur. |
| Overall pipeline | 1.48 | mean ASR runtime 12.1 min per meeting; mean audio length 28.0 min | Not reliable for unattended use on this sample. |

## Per-meeting details

### ES2004a: Scenario project kickoff: designing an original, user-friendly remote control.

**Length/conditions:** 17.5 min; AMI Mix-Headset mix; 16 kHz mono WAV. Audio/noise conditions beyond the source label are undocumented.  
**Topic type:** AMI scenario meeting (Edinburgh). Topic wording is inferred from the human reference transcript except where AMI's scenario annotations identify it.  
**ASR / diarization metrics:** 50.89% WER; 85.13% approximate DER; 2653 reference words, 2547 ASR words; ASR runtime 5.3 min.  
**Ratings (1–5):** ASR 1, diarization 1, extraction 2, MoM 2, faithfulness 1, overall 1.4.  
**Done well:** The ASR preserves the central remote-control design topic and several design terms.  
**Missed / main issues:** It loses much of the exact wording and speaker identity. The MoM captures the product goal but turns design phases into a decision and invents two owners/actions plus a 2022-01-01 due date.

**Generated MoM (Qwen output after the app's normalization/reconciliation):**

```json
{
  "agenda": [
    "Developing a remote control with original features, appealing to a wide market, user-friendly for all ages"
  ],
  "decisions": [
    "The remote control will be functional, conceptual, and detail design"
  ],
  "discussion": [
    "The functional design will focus on fulfilling product requirements, while the conceptual design will outline the product's features and the detail design will specify the implementation of those features"
  ],
  "actions": [
    {
      "owner": "Speaker 1",
      "task": "Discuss the functional design and conceptual design of the remote control",
      "due": "2022-01-01"
    },
    {
      "owner": "Speaker 2",
      "task": "Discuss the detail design of the remote control",
      "due": "2022-01-01"
    }
  ]
}
```

**Generated MoM runtime:** 89.4 seconds. **Model:** Qwen2.5-1.5B-Instruct Q4_K_M via Ollama (approximation of configured HF runner).

### EN2002a: Meeting-support interface discussion: browser/search navigation, meeting and topic views, and summary/transcript usability (topic inferred from the reference transcript).

**Length/conditions:** 35.7 min; AMI Mix-Headset mix; 16 kHz mono WAV. Audio/noise conditions beyond the source label are undocumented.  
**Topic type:** Naturally occurring AMI meeting (Edinburgh). Topic wording is inferred from the human reference transcript except where AMI's scenario annotations identify it.  
**ASR / diarization metrics:** 74.32% WER; 83.43% approximate DER; 7632 reference words, 7677 ASR words; ASR runtime 16.5 min.  
**Ratings (1–5):** ASR 1, diarization 1, extraction 2, MoM 2, faithfulness 2, overall 1.6.  
**Done well:** It captures some interface/search concepts and the real discussion about researching query-language options and revisiting them at a later meeting.  
**Missed / main issues:** The transcript repeats filler (“yeah”) at extreme length. The MoM repeats agenda topics as decisions and invents an XML extraction task. Alternating speaker labels make the owners unreliable.

**Generated MoM (Qwen output after the app's normalization/reconciliation):**

```json
{
  "agenda": [
    "browser and its features",
    "summarization and transcription",
    "topics and meetings"
  ],
  "decisions": [
    "browser and its features",
    "summarization and transcription",
    "topics and meetings"
  ],
  "discussion": [
    "browser and its features",
    "summarization and transcription",
    "topics and meetings"
  ],
  "actions": [
    {
      "owner": "Speaker 1",
      "task": "write code to extract XML data",
      "due": "next week"
    },
    {
      "owner": "Speaker 2",
      "task": "research query language",
      "due": "next meeting"
    }
  ]
}
```

**Generated MoM runtime:** 64.8 seconds. **Model:** Qwen2.5-1.5B-Instruct Q4_K_M via Ollama (approximation of configured HF runner).

### EN2003a: Academic event planning: call for abstracts/titles, poster session, invitations, and deadlines (inferred from the reference transcript).

**Length/conditions:** 37.3 min; AMI Mix-Headset mix; 16 kHz mono WAV. Audio/noise conditions beyond the source label are undocumented.  
**Topic type:** Naturally occurring AMI meeting (Edinburgh). Topic wording is inferred from the human reference transcript except where AMI's scenario annotations identify it.  
**ASR / diarization metrics:** 32.34% WER; 71.94% approximate DER; 6484 reference words, 5929 ASR words; ASR runtime 9.5 min.  
**Ratings (1–5):** ASR 2, diarization 1, extraction 2, MoM 1, faithfulness 2, overall 1.6.  
**Done well:** This was the best ASR result in the sample by WER. It captures much of the discussion about a call for abstracts and event planning.  
**Missed / main issues:** The diarization remains poor. Qwen emitted fenced JSON with a repetitive action list and was truncated at the 700-token limit; parsing failed, so the app’s normalization/reconciliation stage could not run for this meeting.

**Generated MoM (Qwen output after the app's normalization/reconciliation):**

JSON parsing failed after the output was truncated at the token limit. Raw response:

````text
```json
{
  "agenda": ["Call for abstracts", "Post-ecession poster session", "Conference invitations"],
  "decisions": ["Set the latest deadline for titles", "Decide on the structure of the conference"],
  "discussion": ["Agenda items", "Decisions on the structure"],
  "actions": [
    {
      "owner": "Speaker 1",
      "task": "Send out the call for abstracts",
      "due": "end of March"
    },
    {
      "owner": "Speaker 2",
      "task": "Decide on the structure of the conference",
      "due": "end of March"
    },
    {
      "owner": "Speaker 1",
      "task": "Send out the call for titles",
      "due": "Monday, April 7th"
    },
    {
      "owner": "Speaker 2",
      "task": "Decide on the structure of the conference",
      "due": "end of March"
    },
    {
      "owner": "Speaker 1",
      "task": "Send out the call for titles",
      "due": "Monday, April 14th"
    },
    {
      "owner": "Speaker 2",
      "task": "Decide on the structure of the conference",
      "due": "end of March"
    },
    {
      "owner": "Speaker 1",
      "task": "Send out the call for titles",
      "due": "Monday, April 14th"
    },
    {
      "owner": "Speaker 2",
      "task": "Decide on the structure of the conference",
      "due": "end of March"
    },
    {
      "owner": "Speaker 1",
      "task": "Send out the call for titles",
      "due": "Monday, April 14th"
    },
    {
      "owner": "Speaker 2",
      "task": "Decide on the structure of the conference",
      "due": "end of March"
    },
    {
      "owner": "Speaker 1",
      "task": "Send out the call for titles",
      "due": "Monday, April 14th"
    },
    {
      "owner": "Speaker 2",
      "task": "Decide on the structure of the conference",
      "due": "end of March"
    },
    {
      "owner": "Speaker 1",
      "task": "Send out the call for titles",
      "due": "Monday, April 14th"
    },
    {
      "owner": "Speaker 2",
      "task": "Decide on the structure of the conference",
      "due": "end of March"
    },
    {
      "owner": "Speaker 1",
      "task": "Send out the call for titles",
      "due": "Monday, April 14th"
    },
    {
      "owner": "Speaker 2",
      "task": "Decide on the structure of the conference",
      "due": "end of March"
    },
    {
      "owner": "Speaker 1",
      "task": "Send out the call for titles",
      "due": "Monday, April 14th"
    },
    {
      "
````

**Generated MoM runtime:** 58.2 seconds. **Model:** Qwen2.5-1.5B-Instruct Q4_K_M via Ollama (approximation of configured HF runner).

### IB4001: Office relocation: moving to a larger building and allocating rooms/offices and equipment.

**Length/conditions:** 29.7 min; AMI Mix-Headset mix; 16 kHz mono WAV. Audio/noise conditions beyond the source label are undocumented.  
**Topic type:** Naturally occurring AMI partner meeting (IDIAP). Topic wording is inferred from the human reference transcript except where AMI's scenario annotations identify it.  
**ASR / diarization metrics:** 50.00% WER; 76.53% approximate DER; 4690 reference words, 4954 ASR words; ASR runtime 8.3 min.  
**Ratings (1–5):** ASR 1, diarization 1, extraction 3, MoM 2, faithfulness 2, overall 1.8.  
**Done well:** The transcript captures the move and the space-allocation discussion. The MoM identifies the main relocation topics.  
**Missed / main issues:** ASR misrecognizes “ISSCO” as “Cisco.” The MoM recasts discussion as settled decisions, assigns alternating synthetic speaker labels as owners, and adds a November 2 due date not supported by the reference transcript.

**Generated MoM (Qwen output after the app's normalization/reconciliation):**

```json
{
  "agenda": [
    "Cisco's new building location",
    "Decisions on office and equipment allocation",
    "Security and access to the new building"
  ],
  "decisions": [
    "Decide on the new building's location",
    "Allocate office and equipment to each person",
    "Discuss security and access to the new building"
  ],
  "discussion": [
    "Discuss the new building's location",
    "Allocate office and equipment to each person",
    "Discuss security and access to the new building"
  ],
  "actions": [
    {
      "owner": "Speaker 1",
      "task": "Discuss the new building's location",
      "due": "November 2nd"
    },
    {
      "owner": "Speaker 2",
      "task": "Allocate office and equipment to each person",
      "due": "November 2nd"
    },
    {
      "owner": "Speaker 1",
      "task": "Discuss security and access to the new building",
      "due": "November 2nd"
    }
  ]
}
```

**Generated MoM runtime:** 41.1 seconds. **Model:** Qwen2.5-1.5B-Instruct Q4_K_M via Ollama (approximation of configured HF runner).

### IN1009: Technical discussion/interview: speech pitch and speaker/location clustering, with MATLAB/C++ implementation (inferred from the reference transcript).

**Length/conditions:** 20.9 min; AMI Mix-Headset mix; 16 kHz mono WAV. Audio/noise conditions beyond the source label are undocumented.  
**Topic type:** Naturally occurring AMI partner meeting (IDIAP). Topic wording is inferred from the human reference transcript except where AMI's scenario annotations identify it.  
**ASR / diarization metrics:** 258.64% WER; 87.96% approximate DER; 2916 reference words, 7580 ASR words; ASR runtime 21.0 min.  
**Ratings (1–5):** ASR 1, diarization 1, extraction 1, MoM 1, faithfulness 1, overall 1.0.  
**Done well:** The annotated transcript clearly contains technical discussion, allowing direct comparison.  
**Missed / main issues:** Whisper misdetected the language and repeated a French phrase (“C’est bon”) thousands of times: hypothesis length was 7,580 words against 2,916 reference words (258.6% WER). The MoM contains only generic placeholder fields and omits the technical content.

**Generated MoM (Qwen output after the app's normalization/reconciliation):**

```json
{
  "agenda": [
    "meeting agenda"
  ],
  "decisions": [
    "meeting decisions"
  ],
  "discussion": [
    "meeting discussion"
  ],
  "actions": []
}
```

**Generated MoM runtime:** 58.8 seconds. **Model:** Qwen2.5-1.5B-Instruct Q4_K_M via Ollama (approximation of configured HF runner).

## Reference MoM comparison

AMI provides a human abstractive summary for the scenario meeting ES2004a. It covers the kickoff goal and long-range agenda, participant introductions, budget/price/profit, initial remote-control ideas, menu/LCD/material discussion, preparation for the functional-design meeting, and a budget concern. The generated MoM captured the remote-control goal but omitted most of those points, promoted design phases to a decision, and added unsupported owners/actions and a date. AMI does not provide a matching abstractive MoM for the four naturally occurring meetings in this selected subset, so their MoM/faithfulness ratings are reviewer judgments against the human reference transcripts rather than comparison to a gold MoM.

## Models and parameters used

| Stage | Configured value / parameters | Evaluation execution |
|---|---|---|
| ASR | `TRANSCRIPTION_PROVIDER=local`; Transformers ASR model `openai/whisper-tiny`; `return_timestamps=True`; default decoding and automatic language detection. The Python service does not configure Whisper.cpp. | Actual `TranscriptionService` on each complete WAV. A temporary alias exposed the installed ffmpeg binary because Transformers looks for an executable literally named `ffmpeg`. |
| Diarization | No independent diarization model in the active Python path. ASR chunks get `Speaker 2`, `Speaker 1` alternating by chunk index (`1 + idx % 2`). | Same alternating labels as production service; raw ASR chunk timestamps were retained only for evaluation. |
| Minutes | Configured Python model `Qwen/Qwen2.5-1.5B-Instruct`; Transformers text-generation; `max_new_tokens=700`; `do_sample=False`; prompt requires JSON keys `agenda`, `decisions`, `discussion`, `actions` and says never invent facts. | Because full-precision Python loading was not suitable for the available memory, used the same Qwen2.5 1.5B base family as GGUF Q4_K_M via Ollama, with `num_ctx=16384`, `temperature=0`, `num_predict=700`, same prompt. Applied the app's `_json_object`, `normalize_minutes`, and `reconcile_actions` post-processing. This is an approximation, not an exact configured runtime. |
| Action grounding | Token-overlap heuristic; owner cues `will`, `shall`, `must`, `is going to`; word overlap is used to reassign owner. | Applied after successfully parsed outputs. Its weak matching cannot validate task/date or stable speaker identity. |
| Sentiment / engagement | `distilbert/distilbert-base-uncased-finetuned-sst-2-english`; per-speaker text capped at 4,000 chars; engagement is share of spoken words. | Not scored in this meeting-intelligence evaluation; the diarization errors also make per-speaker sentiment/engagement questionable. |
| Optional hosted models | OpenAI transcription `gpt-4o-transcribe-diarize`; minutes `gpt-5-mini`; API key absent in the project `.env`. | Not used. |

## Transcript appendix: actual ASR output

The following are full ASR outputs from the five recordings. Speaker IDs are the pipeline's alternating chunk labels, not reliable identities. Full reference transcripts and timestamps are retained in the downloaded AMI annotations; this appendix contains model output as requested.

### ES2004a

````text
Speaker 2: Are we, we're not likes dim lights, I don't see that, I don't see that, I don't see that.
Speaker 1: I don't know, okay.
Speaker 2: That's right.
Speaker 1: Am I supposed to be standing up there?
Speaker 2: So you've got both of these clips on?
Speaker 1: She got on to me, I've got it, both of her, okay.
Speaker 2: Yeah.
Speaker 1: Don't.
Speaker 2: She's gonna fall off the door.
Speaker 1: Okay, hello everybody, and I'm Sarah project manager.
Speaker 2: And this is our first new team, surprise seeing you next.
Speaker 1: OK, this is our agenda.
Speaker 2: We will do some stuff, get to know each other a bit better.
Speaker 1: We'll come to all each other.
Speaker 2: Then we'll go do two training, talk about Project Plan, discuss our own ideas,
Speaker 1: and everything.
Speaker 2: And we'll go 25 minutes to do that as far as I can understand.
Speaker 1: Now, we're developing a remote control which we've already know, we want it to be original,
Speaker 2: something like that.
Speaker 1: People haven't thought of, it's not iron shops.
Speaker 2: Trendy, appealing to a wide market, but, you know, not a hunk of metal.
Speaker 1: And user-friendly, granny's to kids, maybe even creatures should be able to use it.
Speaker 2: Okay.
Speaker 1: The first is the functional design, this is where we all go off into our individual work.
Speaker 2: What needs need to be fulfilled by the product, what effects the product has to have, and how it's actually going to do that.
Speaker 1: Conceptual design, what we're thinking, how it's going to go, and then the detail design, how we're actually going to put it into practice and make it work.
Speaker 2: Okay, right, we're going to practice with the pens and draw our favorite animal on the whiteboard algorithm.
Speaker 1: And some of the characteristics of that animal.
Speaker 2: So, okay, let me space grab one of them.
Speaker 1: Thank you so much for watching this video and I'll see you in the next video, thanks for watching and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video and I'll see you in the next video Okay, I'm not going to ask you to guess I'm going to tell you that's what's real tiger.
Speaker 2: and I see them as majestic and independent and proud.
Speaker 1: Now, we'd like to go next.
Speaker 2: Okay?
Speaker 1: I wish I got this come from, thank you, maybe you can guess what I'm trying to make.
Speaker 2: It's actually sitting, so it's sitting, it's not standing.
Speaker 1: I see it as one thing, it's very supportive, it's your best friend in your, you can talk to a dog, it can be a best friend, it doesn't discriminate between you, based on what you are,
Speaker 2: Second, it's loyal and third thing, it's got intuition, it means dogs can sometimes make
Speaker 1: out between a three-fanner person, so basically these are the three unique features I
Speaker 2: think belong to a dog.
Speaker 1: Thank you.
Speaker 2: Thank you.
Speaker 1: Thank you.
Speaker 2: Sorry.
Speaker 1: Please leave me a space at the bottom on the show.
Speaker 2: Alright, it's the top. We're standing on a chair.
Speaker 1: Well, since you guys have chosen their ones, I want to stay.
Speaker 2: Okay.
Speaker 1: How's it going to sound around them?
Speaker 2: And also, my drawing scale isn't that great.
Speaker 1: Well, as you can see, the quality of the work today, then.
Speaker 2: I think it's like standing, we're good.
Speaker 1: Okay, now I'm going to have to change what it rules are originally going to be because that looks like a beak now, stay.
Speaker 2: Crocodile?
Speaker 1: Yeah, it can be a crocodile.
Speaker 2: It can be a crocodile.
Speaker 1: Well, it was the best.
Speaker 2: It was an attempt to tear eggs,
Speaker 1: and then it's so changing to a pelican,
Speaker 2: but it can be a crocodile.
Speaker 1: Yeah, and I think on the spot of the things that is scary, strong, yeah, that's funny, I think I'm very impressed with your artistic skills, mine's a dreadful.
Speaker 2: Oops, this is now coming apart, I just put the top thing.
Speaker 1: I'll hold that click, then I'll hold it on again.
Speaker 2: Oops, oh dear, what happened there?
Speaker 1: Time to go out.
Speaker 2: Hopefully that'll stay on 200 version.
Speaker 2: Again, this is off the top of my head. I was going to do a big cat too, and it doesn't look like what I wanted to be. It's not a vampire, but honestly, and somewhere there's a body behind.
Speaker 1: That's my dreadful, that's the worst yet. It's meant to be an eagle.
Speaker 2: You can tell it's a flying animal.
Speaker 1: Could have been a seagull, and I never thought of a seagull.
Speaker 2: An eagle. Again, I'm thinking on my feet, goodness.
Speaker 1: It's because they're also independent. I'll put that one down again.
Speaker 2: They get a girl.
Speaker 1: You say they're good at golf.
Speaker 2: Are they?
Speaker 1: They're good.
Speaker 2: Oh right. I'm not good at golf.
Speaker 1: I'll say they're quite free-spirited.
Speaker 2: Flying around everywhere.
Speaker 1: Doing their own thing.
Speaker 2: And birds of prey aren't like, oh dear, in trepid, in trepid.
Speaker 1: There we go, about 10 is going to be okay?
Speaker 2: What?
Speaker 1: Okay.
Speaker 2: That was fine.
Speaker 1: Right.
Speaker 2: Finance wise, we've got a selling price at 25 euros,
Speaker 1: which I don't actually know what that is in times at all. Any ideas?
Speaker 2: So what might you?
Speaker 1: One point four year old would make it a problem or something?
Speaker 2: Yeah, yeah, same amount, so yeah, about 17, 17, 17, 17 pounds, I know.
Speaker 1: Should we be making notes of this, we can just refer to this later, come on.
Speaker 2: I think so, I think that I'll be able to put it up, or I'll be having a shared folder.
Speaker 1: Having said that, though, if you want to get one of those, the ones on the market, the main list, they're about 20 pounds anyway.
Speaker 2: Right.
Speaker 1: Yeah, we have to fly one.
Speaker 2: So suppose later it depends if we want to undercut the price, or is it going to make our
Speaker 1: product look like a GPT for your share?
Speaker 2: Production costs at 12.50 so if you can imagine half of the selling price is taking that
Speaker 1: by building it and proper aim is 50 million euros which is it?
Speaker 2: You know, first year, yeah, yeah, yeah, I presume so, you've got market range international, and you did see earlier, it's got to be accessible and usable by sort of all age groups.
Speaker 1: Just, we're not focusing on business market, any particular thing, it's everyone, user friendly to everyone. Okay, big target group.
Speaker 2: Yeah, I don't think we have to, I don't think it's a case of worrying about different languages and things like that
Speaker 1: Making that key point just that it's going to be an international market like Australia and America, I think it's like that.
Speaker 2: Okay.
Speaker 1: What are your experiences from these controls?
Speaker 2: I've got three videos, a TV and sort of amp thing all set out.
Speaker 1: So we got one of the universal remote controls.
Speaker 2: You program each of your things into, but that kept losing the signals.
Speaker 1: So we'd have to reprogram it every now and again.
Speaker 2: I think it was quite cheap as well.
Speaker 1: Yeah, that might have happened to me too, but that was quite good about the e-cups.
Speaker 2: You saw the ones you have?
Speaker 1: You have six from out controls.
Speaker 2: Right.
Speaker 1: You want to include everything into one, like...
Speaker 2: Yeah.
Speaker 1: Okay.
Speaker 2: My experience has only been given the remote control with the object I buy,
Speaker 1: not doing any tampering with it and programming,
Speaker 2: using it to program TV or videos and things,
Speaker 1: but basically on or volume up and down,
Speaker 2: channel 1 to that basic function,
Speaker 1: I don't think I could go any further with it.
Speaker 2: than that. So it's because it's got to be something usable by someone like me as well.
Speaker 1: Yeah, the main, that's the main stuff anyway.
Speaker 2: I mean, and you don't want to, I hate, I hate looking at a control and seeing a million tiny little buttons with tiny little words and thing what they all do and just sitting there searching for the tailoring text button.
Speaker 1: you don't necessarily understand, symbols you meant to understand, when you've got the main things on the front of it and a section opens up or something to the other functions when you can do sound or also recording things like that inside it, because it doesn't make when you pick it up, it doesn't make it be complicated to look at it, obviously yes, when you're doing it.
Speaker 2: Actually, that just raises a point. I wonder who our design people think, but you know on a mobile phone
Speaker 1: You can press a key and it gives you a menu. It's got a menu display. I wonder if incorporating that into the design of a remote control
Speaker 2: Why the user see a little LCD display. I was thinking on the same lines. You instead of having too many buttons and make it complicated for the user
Speaker 1: May be have an LCD display or something like that like a mobile with many and with menus
Speaker 2: Yeah, and if it's somewhat similar to what you have on mobile phone people might find it
Speaker 1: easier to browse and maybe get helpful. Yeah. What about the older generation? What about
Speaker 2: Granny and Granddad? I would be excited. My Granddad can answer his mobile phone, but you
Speaker 1: couldn't even dream of texting or something like that. Can he program his remote controller
Speaker 2: is he basic with that too? I don't think they're tasty. Yeah. Right. My Granddad thought she
Speaker 1: better than me using tabletx, right? Right. So that's a problem regardless of any design
Speaker 2: modifications you you come up with yeah that's going to be a problem anyway with the
Speaker 1: older generation perhaps and that's another this year over tackle that.
Speaker 2: Why just needs to be as long as it's sort of self-intuitive and you can work out why
Speaker 1: everything's done because I mean men use on sort of neat films now they're told gold these
Speaker 2: pictures and stuff which makes it fairly obvious what you're trying to do I don't know
Speaker 1: I don't like that you know the new phones that kind of got a windows based
Speaker 2: running system. I find it really confusing. I kept getting lost in the phone. I
Speaker 1: don't have a new one but my friend go and you want let's try and do things
Speaker 2: a bit and I just kept getting lost but that's just me. Yeah I don't know how
Speaker 1: how, for 25 or 12 years, 50, how much of an excellent screen if you get, you'd have
Speaker 2: to keep it down to a black and white LCD thing in your hands.
Speaker 1: Is it possible that, for the older generation, you could have like an extra button that
Speaker 2: you press for large print, like you do in large print books, obviously it displays last
Speaker 1: on the screen, displays less on the screen, but as long as they can read it, that's the
Speaker 2: main thing.
Speaker 1: Or what about kind of a dual function in that you've got the basic buttons just for your
Speaker 2: play, volume, program, things, and also, and then a menu to go into with obvious pictures
Speaker 1: of the assembles and that's where you control recording and things like that.
Speaker 2: The other thing is just tucking into mobile phone design features again, could have a flip
Speaker 1: top remote control, so that when you flip over the top, your screen is, you can have a bigger screen in the flip over.
Speaker 2: I think that's a cost thing.
Speaker 1: I don't know how much we're going to know about.
Speaker 2: It might save up a bit of space.
Speaker 1: So looking bulk-cave, it might look small.
Speaker 2: Yeah, yeah.
Speaker 1: It might have some cost implications.
Speaker 2: And there's no reason we need to make it look as fashionable and stylish as a mobile phone.
Speaker 1: It can still be lightweight plastic, you know.
Speaker 2: Something that's easily molded and produced.
Speaker 1: Sorry, I'm trying to get a new territory going.
Speaker 2: Right, okay, we've got half there for the next meeting.
Speaker 1: So we're all going to go off and do our individual things.
Speaker 2: I think that's probably about it.
Speaker 1: And then we'll come back in the age again.
Speaker 2: Yeah.
Speaker 1: And I get to do another fantastic...
Speaker 2: Just a quick thing about the...
Speaker 1: What you're saying about the...
Speaker 2: Doesn't need to be fashionable.
Speaker 1: So if I had a quick look at the company website and it's like, the, we put the fashion into electronics.
Speaker 2: So I think the whole design thing might be.
Speaker 1: Sure, I mean, you can still have plastic and it look quite good.
Speaker 2: Yeah, I mean, it doesn't have to be that, you know, but that was my main point.
Speaker 1: We do have to use metal. I don't know if using plastic doesn't make it cheap.
Speaker 2: I mean the sky will look at your eyes and they're kind of molded and look a bit different
Speaker 1: and then the telewester will look at your eyes so it's a little bit plastic, it looks a bit
Speaker 2: lighter, so yeah, I guess that's okay, okay, so let's break out there, okay, okay, I'm going
Speaker 1: So, see you in half an hour.
Speaker 2: Do we go back to our new things, do we?
Speaker 1: Yeah.
````

### EN2002a

````text
Speaker 2: I wonder how much of a meeting is talking about the stuff with the meetings?
Speaker 1: Yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, All right, go. Good stuff.
Speaker 2: We'll add up the mind as well.
Speaker 1: Give it to this.
Speaker 2: It's supposed to be a good start.
Speaker 1: Okay, so yep.
Speaker 2: So yeah, we've got a browser we've...
Speaker 1: which comes up automatically with the transcription box and the topics.
Speaker 2: And then when you go on the menu, you can select the summarization box.
Speaker 1: which pops up and an audio player, and I think the search works as well, so pop up a search,
Speaker 2: and it loads up just the background when they're so empty, and so when you start, you have to either open up,
Speaker 1: take the observation or do a search and open it through that.
Speaker 2: The transcription box has got a summarized box, but in which this is doing anything yet.
Speaker 1: Now, I wonder how we want to do, you know, we want to pop up window with a speaker characterization.
Speaker 2: Either we could do that, you know, when does the pop-up come? Either we can, when you click on the, the ID, any sort of ID in the transcription box.
Speaker 1: or we can put an extra button, extra few buttons next to the summarized button so that
Speaker 2: you actually in the transcription box but so like you click on a button and then it opens
Speaker 1: in this way but that speaker characterization is. The problem is the left click is already used
Speaker 2: because it highlights that that part of speech or whatever that. What are you doing?
Speaker 1: left it. I don't know what happens when you don't look like that, but that'll be a bit
Speaker 2: annoying if you have left click for one thing in double click. I think so yeah when you
Speaker 1: left click it you can for example set the marker there so that the audio goes from there I think.
Speaker 2: So we can't put it on left click we could put it on the right click we could for example have
Speaker 1: a little menu that pops up. Yeah, well because I get that's right. So right click on it menu,
Speaker 2: you know, then you can click on speak of categorization of pops in the. What else can we have in
Speaker 1: then? That's a good point. I don't know. I don't know about you, but usually in Windows,
Speaker 2: right click isn't one thing. Do anything doesn't it? It opens a menu. Yeah, that's what it will do.
Speaker 1: It would be a bit weird to start bringing that stuff with it, to just answer the same sort of idiom throughout.
Speaker 2: Yeah.
Speaker 1: Yeah.
Speaker 2: Or just, you know, or just the button.
Speaker 1: I guess the button makes a bit more sense, because otherwise you don't really know that,
Speaker 2: oh, what if I, right click that, what happens then?
Speaker 1: Well, no, it's not that special.
Speaker 2: The menu's on both that.
Speaker 1: Well, oh yeah, it's more obvious isn't it already a proof isn't it? It's got a button
Speaker 2: Yeah, that's true, yeah, I'm going to, it's a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a all the meetings that that user has been in, like a search for that user, yeah. Is that
Speaker 1: going to be useful or too much? I guess so. So what did you part of the many that comes down is
Speaker 2: says, give me all your meetings? Yeah. So when you're right click on it, one option will be
Speaker 1: and give me all you need to use, characterize this speaker.
Speaker 2: Yeah.
Speaker 1: Or is that too much, I mean?
Speaker 2: I don't know.
Speaker 1: I guess so.
Speaker 2: It's more like part of the browsing sort of thing,
Speaker 1: more than this speaking characterization.
Speaker 2: That's the dimension, that's really know how to involve
Speaker 1: the speaking characters to the browser and connect.
Speaker 2: Yeah, I mean, you type it in with dialogue apps,
Speaker 1: or something, as well, and then speak for characterization,
Speaker 2: and then just some way to sort of leverage that information,
Speaker 1: like we have it, we're doing what is to help the browser
Speaker 2: or what can it give us.
Speaker 1: Well, you mean that the speaker characterization, oh well, yeah.
Speaker 2: I mean, I don't know about that.
Speaker 1: I mean, it's the speaker characterization,
Speaker 2: a bit like he said, I mean, it's like a nice thing.
Speaker 1: You don't want to actually show what the user wants for it,
Speaker 2: but it's interesting, so why don't you give it time?
Speaker 1: Yeah, yeah.
Speaker 2: I think we should do it, I mean I guess maybe we could have that as another thing of like
Speaker 1: well if you get to speak characterization that someone talks a lot in a certain topic and then
Speaker 2: if you kind of click on that topic you get from a thing that's in that topic or whatever
Speaker 1: yeah and that's that's still another level further I mean we're not even there you know
Speaker 2: We have to first define what happens when you click on a user.
Speaker 1: With that, let's speak with characterization specifically because of the other version.
Speaker 2: So should we try to do a right click when you then?
Speaker 1: Yeah.
Speaker 2: All right.
Speaker 1: Why not set just from the mean?
Speaker 2: Even if any one is not coming from a particular window,
Speaker 1: like if we want to sort of get, like if we're on the user's versus like a top,
Speaker 2: or something, have a right control for these various things.
Speaker 1: Yes, wait. Yeah, there's a second thing about the topics. The topic window. We want to somehow
Speaker 2: Click be able to click on the topic and it pops up with all the meetings that contain that. Right. Yeah. Yeah. So we could do that in a similar way to it. Right, please well. Okay.
Speaker 1: Yeah, so this is a different system through. Yeah. On the speaker.
Speaker 2: So yeah. So we have basically two options of browsing the meetings is by either
Speaker 1: searching and opening individual observations and then we have the interlinking by, like, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click, click in all meetings or just in one meeting and just show up in particular instances of that topic in the meeting.
Speaker 2: Like, and just think to have the people there, so if somebody knows exactly what they want to do, and we know that that's the most common thing that's going to happen.
Speaker 1: So that don't want people to do that, and so to say from the trouble of right clicking and choosing you at a moment in your opinion.
Speaker 2: I don't see that as anything obvious that would be able to do that would be easy.
Speaker 1: It might come to us starting playing with it.
Speaker 2: What was that I think kind of?
Speaker 1: Do you mean like we have to do it?
Speaker 2: click menu, right click, but instead of like, have a default double click, so it will be a
Speaker 1: choice.
Speaker 2: For example, what was the most common example used to double click?
Speaker 1: Like, I don't know.
Speaker 2: Show the speaker characterization.
Speaker 1: Yeah.
Speaker 2: For instance, there was a problem with a lot of windows popping up again.
Speaker 1: And they pop up without you being quite sure what it is, you know?
Speaker 2: Yeah.
Speaker 1: But if you do double click on something, don't you expect something to happen?
Speaker 2: I'll tell you what it does on double-click at the moment, because I think it will do something, but it's good starting, but I didn't, I didn't, I didn't, I really didn't seem to think obvious that, but I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't, I didn't I mean, if you can think of something like this, I guess at the point I'm the, yeah, what you're clicking on.
Speaker 1: So, um, yeah, another thing, single audio files, do we want to use them a lot?
Speaker 2: We don't know yet, do we? Do you mean single channel?
Speaker 1: Yeah, single channel, but single channel files, do we want them? I mean.
Speaker 2: Probably not, but we might need them for the experiences. If we try to do it in audio.
Speaker 1: Yeah, yeah, yeah, yeah. We might use them at the moment though, but...
Speaker 2: To work with them, but do we want to integrate them so that when you browse, we can...
Speaker 1: We might want to be able to say, oh, just give me what that person's saying.
Speaker 2: Do you, though? No, you're not going to make much sense if you're listening to that person.
Speaker 1: Unless you can't hear it properly or something, somebody's talking over some of the girls or something
Speaker 2: Would you say night for now and put it in my mouth?
Speaker 1: Yeah, because otherwise it will increase the amount of day to be made by a lot of one day.
Speaker 2: Yeah.
Speaker 1: Yeah, what do people think in general about the windows cluttering that you mentioned?
Speaker 2: Do you think we probably need that they don't have the full flexibility we need to have that that's what I'm very much
Speaker 1: I don't want to have everything
Speaker 2: customizable
Speaker 1: The thing is typically though is someone going to have five windows open at the same time probably not
Speaker 2: No, two or three of what I was looking like but yeah, but yeah, it depends
Speaker 1: I mean I really want to put the summary in somewhere
Speaker 2: You know and the summary for example a typical you open the window you read through it
Speaker 1: You might click on you know close it against right away. Yeah, but it'd be good to me. Oh, I think it's funny
Speaker 2: It's funny. Well, couldn't we I mean you probably I don't know if you want to have like the the full transcription and the summary at the same time
Speaker 1: So maybe you can just like
Speaker 2: Choose the same window for transcription and summary. It's like a tab. There. I was a bit of tab. Yeah
Speaker 1: Tabs are nice. Yeah, tab like you
Speaker 2: I'm not sure.
Speaker 1: Yeah.
Speaker 2: I don't know.
Speaker 1: I don't know.
Speaker 2: I don't know.
Speaker 1: I don't know.
Speaker 2: I don't know.
Speaker 1: I don't know.
Speaker 2: I don't know.
Speaker 1: I don't know.
Speaker 2: I don't know.
Speaker 1: It's a bit of a cripple which I've always been doing.
Speaker 2: Sometimes.
Speaker 1: It's a bit of a cripple.
Speaker 2: I can have a look.
Speaker 1: Yeah.
Speaker 2: Yeah.
Speaker 1: We're just, I don't know.
Speaker 2: Yeah.
Speaker 1: Yeah.
Speaker 2: That might be changed to contents of the same window.
Speaker 1: Yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, Fightershop has a lot of windows, if you have a windows, if I just got loads and you're always good forever going, I'll get out of the way, there's always stuff in the ones and there's
Speaker 2: I don't know what, I mean people get used to it, I mean when you use a windows, or in the next fall, you have a lot of windows open
Speaker 1: You do, you manage them
Speaker 2: Yeah
Speaker 1: Yeah
Speaker 2: Unless you can minimize them and stuff like that
Speaker 1: Yeah, you can minimize them, yeah, yeah, yeah
Speaker 2: Okay, well, of course you can, it's like a lot of these can be like once we get the
Speaker 1: disflowns he's out then we can you know transcript without the disflowns he transcript with
Speaker 2: the diploma disflowns. Yeah, that's true. Yeah, that's true. Yeah, that's true. Yeah, that's true.
Speaker 1: Yeah, that's true. Yeah, that's true. Yeah, that's true. Yeah, that's true. Yeah, that's true. Yeah,
Speaker 2: that's true. Yeah, that's true. Yeah, that's true. Yeah, that was a plan for the
Speaker 1: disflowns anyway. Yeah, so yeah, do you want to do that with summaries and put the summaries
Speaker 2: and in the same way now, meet trace.
Speaker 1: Yeah, well, I don't know, with transcripts,
Speaker 2: sounds reasonable to have like transcripts,
Speaker 1: like maybe three-alturns is then, like full meeting,
Speaker 2: meeting without disclosing and sub-rise.
Speaker 1: Yeah, do you want to do that?
Speaker 2: I don't want to make sense.
Speaker 1: Yeah, yeah.
Speaker 2: Yeah, so let's get to it.
Speaker 2: And finally, the prototype is spoken about what kind of prototype could be produced. Because I'm, I'm just, you know, I go into the lab and nothing, I want my going to
Speaker 1: change today, you know? Any kind of just develops? I'm not aiming for anything. Do we want
Speaker 2: I'm pretty much getting there anyway, I guess it is just to try and I mean for us to be able to do something that we can include with your thing.
Speaker 1: So we need something just slightly more than just that on the side.
Speaker 2: Yeah, just so see the integration works, sort of between the difficulty.
Speaker 1: Yeah, definitely.
Speaker 2: So I guess that's what we need to look for.
Speaker 1: I think that's kind of what we meant as well.
Speaker 2: We're thinking it sort of started these stuff rather than just me.
Speaker 1: Well, that's what we need to look for.
Speaker 2: The project's hard for the GUI.
Speaker 1: Yeah, well, I guess I mean, that was probably our intention.
Speaker 2: but we might not have written it down.
Speaker 1: Yeah.
Speaker 2: Actually, is the code accessible?
Speaker 1: Like the GUI stuff that you've done.
Speaker 2: Like can we just copy the latest stuff out of your directory?
Speaker 1: Like you're just trying to take a look for something.
Speaker 2: I don't know if you can access other people's files.
Speaker 1: You can make it well-dreadable then anybody.
Speaker 2: If you just tell us the directory and just make the file readable,
Speaker 1: then we know the directory to get in then.
Speaker 2: Yeah.
Speaker 1: Sure. I don't know if it's readable at the moment, but you can show up and have a few points of fault there
Speaker 2: No, they're not well-dreadable. I don't know if it's all there I need to feel then only you can read them
Speaker 1: You can see them, but you can't read them. Okay, all right. Well, I'll make that readable in here
Speaker 2: So the directory is my number. Are you suggesting mail?
Speaker 1: Okay, yeah, yeah, it's not. It's not. It's your number. Okay. It's in all the emails
Speaker 1: Yeah, you're number. Not 04.
Speaker 2: Okay.
Speaker 1: 04.
Speaker 2: 5, 5, 5.
Speaker 1: 6, 0, 4, 4, 5, 5, 6, 8.
Speaker 2: And then it's...
Speaker 1: And then there's a folder in LSSD.
Speaker 2: And it's called the M browser.
Speaker 1: The M browser.
Speaker 2: Yes.
Speaker 1: And from the same.
Speaker 2: I hope you never have to look in my direction, it's just pure chaos.
Speaker 1: No, I'm extremely old, and I've got all the same thing, I love following you.
Speaker 2: The mind is serious chaos.
Speaker 1: Far as ever, man.
Speaker 2: Yep, so that's me, Dan. Someone else wanted to talk about this, huh?
Speaker 1: I don't know, jump up one.
Speaker 1: Can you tell me what other than this, B2? I don't know, I started browsing a bit just like trying to see if there's anything
Speaker 2: out there to use, sort of, just what were you doing in your journey?
Speaker 1: Yeah, it's so interesting.
Speaker 2: Yeah, oh yeah, it's so interesting.
Speaker 1: Yeah, yeah, yeah.
Speaker 2: It's just, it's just, okay.
Speaker 1: Founded tutorial, but it's interesting, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven't read it yet, but I haven of nonsense but yeah both basics is okay yeah yeah yeah so you think you shouldn't be too
Speaker 2: difficult I don't know I was a bit worried about one well when he talked about this with a
Speaker 1: file that's an old file I mean how much do we actually need to do like extracting things from
Speaker 1: I've been trying to write something to read the XML and get rid of it, and I can get rid of it, but I'm having travel pointy anywhere else. So come up on the screen.
Speaker 2: Further moment, I haven't managed to put it into a vector of wherever and jogging to play with it.
Speaker 1: What are you writing in Java?
Speaker 2: Yeah, okay.
Speaker 1: I don't have a look at the browser code then because
Speaker 2: they are already extracted from example transcripts.
Speaker 1: Yeah, I'm sure they do.
Speaker 2: Yeah.
Speaker 1: I'm sure it's not because I'm sure I'm making a main of it.
Speaker 2: Yeah, I guess, I mean, it was a good point, you had that, like collaborating with foul things.
Speaker 1: I mean, if you already started on stuff, I guess.
Speaker 2: We can share as much as possible.
Speaker 1: Yeah.
Speaker 2: Yeah, she, we, I don't know, meet up and see what we could do. I mean, I don't know.
Speaker 1: See what you've done and see what we need. Well, we know more of what we need, maybe.
Speaker 2: Next week, I'm done.
Speaker 1: So you're still, I actually haven't thought anything this week because this week's
Speaker 2: been manic, but it's not quite certain.
Speaker 1: I mean, this week's only two days alone. Well, whatever it was last week.
Speaker 2: The week as is rather than the proper week, you know, it's been a little bit manic, but I was
Speaker 1: one of those, when you're an SPMLP and SP2 right, that's right, and then we had to do an IRP
Speaker 2: Whatever, it was a last week as well, which is only a page long, but it's quite difficult to write a page
Speaker 1: But it was just it didn't think about it for a bit. It's a bit irritating. Yeah, but SPNL people
Speaker 2: So yeah, I was thinking that we generally yeah, yeah, I'm something by next week that we can sort of try and
Speaker 1: The browser as I use it now, or as it was there when I took it, uses the NXT search to get the data out of the files, which I think is odd, but I'm not quite sure how it works, I don't quite understand it.
Speaker 2: So when it to get the data for example to get the summarization data you have to search for I think the idea is on something
Speaker 1: Yeah, I was pretty sure isn't it I guess it's like where it's got that is pretty bizarre
Speaker 2: So they don't you know, they don't say looking that not folder. Yeah, search everything
Speaker 2: That is very bizarre, what did you say wasn't the most efficient? You just write that quite well, but it's like we know where you have to write it
Speaker 1: such square or is it just what's behind it?
Speaker 2: No, there's not the actual search.
Speaker 1: This is just when you open, you know, to load the transcript, for example, to find the transcript
Speaker 2: it doesn't mean it does, and then you see, search for the string, I don't know, transcript or
Speaker 1: x, okay, whatever.
Speaker 2: For, and it just has an open variable, transcript, just whatever, find everything that's got
Speaker 1: that and the load.
Speaker 2: So, I don't know if you looked at the search query language, but it's like a dollar, a text.
Speaker 1: Yeah, yeah, because that's the, the guy could be closer variable, doesn't he?
Speaker 2: Yeah, and then, yeah.
Speaker 1: because every, every of all of these,
Speaker 2: these files have got an ID and all the transcript files have got a string.
Speaker 1: I don't know what it is where it's on text or something.
Speaker 2: So I just search as for those files.
Speaker 1: Okay.
Speaker 2: When you, like, is there a open thingy or what do you, like,
Speaker 1: what did you do to, like, how do you figure out that this uses?
Speaker 2: It makes the research, it's in the code, just that you define a search object and then
Speaker 1: search about the string.
Speaker 2: I had to figure out how to do the same thing for the summary, that's my way.
Speaker 1: I had to understand how to do the transcript, how they did the transcript to do
Speaker 2: something myself.
Speaker 1: So did you have to write it in the way that they wrote it?
Speaker 2: Is that what we did?
Speaker 1: Yeah, just search for specific string.
Speaker 2: You could just use that when you if you want to take the data out.
Speaker 1: If you have a question about what the code means or where to find the code that you want, whatever you want to do, and just send me, you know.
Speaker 2: I can explain.
Speaker 1: you're going to take it to your clothing.
Speaker 2: Oh yeah.
Speaker 1: Actually, in the moment, it's got a load of rubbish, because the
Speaker 2: the browser that I used from the, you know, that they gave us,
Speaker 1: I had a lot of extra stuff in, and I hung dead thrown out,
Speaker 2: just threw out all the functions of the house.
Speaker 1: Just touched, just touched, just touched, just touched.
Speaker 2: So they're all in there yet, still.
Speaker 1: A lot of rubbish, but it will be good.
Speaker 2: We'll be chucked out about the end of the week.
Speaker 1: Coming, commenting it out one bit of time, running it to work, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah Yeah, I actually had that much to do at the moment.
Speaker 2: Well, should you funny what to explore any other?
Speaker 1: Yeah.
Speaker 2: Yeah.
Speaker 1: Yeah, do.
Speaker 2: How's your, how's your, um, uh, quantifier racy?
Speaker 1: I can't remember what I'm supposed to do, by the way.
Speaker 2: Am I supposed to do the summarization thing you bought?
Speaker 1: No.
Speaker 2: Who was dream?
Speaker 1: You do.
Speaker 2: Well, I'll do that then.
Speaker 1: This can be changed.
Speaker 2: So I do that then.
Speaker 1: I don't know, it doesn't matter.
Speaker 2: If you want to, and then it's just, you know, play around to make sure stuff you have some time.
Speaker 1: Why not?
Speaker 2: It shouldn't be, did it.
Speaker 1: So what courses should I pick to be not doing any courses?
Speaker 2: Yeah.
Speaker 1: Well, I do in communications with which we had one exercise and I've done that like two weeks ago.
Speaker 2: That's in two weeks.
Speaker 1: So in products?
Speaker 2: Of course.
Speaker 1: Yeah, it's like 9.5 or 10 a.m.
Speaker 2: Okay.
Speaker 1: Oh, it says it is.
Speaker 2: And then I'm doing
Speaker 1: Palo programming languages and systems,
Speaker 2: which we had one exercise as well.
Speaker 1: And that was the end of the project.
Speaker 2: Well, I'm not doing any back-rads.
Speaker 1: I'm not doing any back-rads.
Speaker 2: I'm sorry.
Speaker 1: Just a big one.
Speaker 2: Yeah.
Speaker 2: We'll be happy when this week is over. Have we ever win these courses at work?
Speaker 1: Yeah.
Speaker 2: I don't know, is that about it then?
Speaker 1: Anything else we need to discuss?
Speaker 2: Did we want to meet before we talk to Steve next week?
Speaker 1: Well, we'll probably get some work done over the weekend, so I know.
Speaker 2: After DMLG or something, and just have a little quick little update, and just...
Speaker 1: Yeah, if you like, we can always decide then.
Speaker 2: Yeah exactly, yeah.
Speaker 1: So what are you planning to do over the weekend then?
Speaker 2: Search.
Speaker 1: You're going to do the search.
Speaker 2: You're going to do the search.
Speaker 1: Yeah, sure.
Speaker 2: Yeah.
Speaker 1: It can be done, aren't I?
Speaker 2: Yeah.
Speaker 1: It'll be, you know, still limited version of, you know, the next query.
Speaker 2: don't be the whole thing. Like we can just decide sort of things that we do
Speaker 1: want to do. Actually, Moses just dial on that, because I'm not supposed to know.
Speaker 2: There's somebody.
Speaker 2: She's not, I think we need to ask ourselves some milestones, because otherwise, you know. Yeah, I don't get it.
Speaker 1: We will get by.
Speaker 2: We will get by.
Speaker 1: Yeah, pretty quick.
Speaker 2: Like you're saying.
Speaker 1: I actually do we want to set a date for interim prototype, specifically I think.
Speaker 2: Oh, you decide, I'm not even much of a person, but the progress of parties, June 23rd, very
Speaker 1: of February, so what is that two weeks, like, yeah, well, how about we get it done by then,
Speaker 2: I mean, issue, then we can write about it in the interim report, yes, you know,
Speaker 1: I'm just looking at my own deadlines, I see, yep, I'm putting the search interface, maybe you should decide pretty early what kind of things you want to be able to search for, and then if you don't want to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to go to the website, I'm going to If you want, you can give out to me now, I'll build a nice, you know, a few tick boxes and
Speaker 2: drop them in use.
Speaker 1: Wasn't like, what do you have now, wasn't that pretty much what we were going to read on?
Speaker 2: No, or what's it?
Speaker 1: Oh, that's, that's the one, that doesn't exist, that's completely cut and pasted, that doesn't
Speaker 2: exist.
Speaker 1: Nice, he doesn't know me.
Speaker 2: That's it, that's it, it's actually all these things are mixed from, you know, all these
Speaker 1: drop their menus and take boxes on it from Google on that.
Speaker 2: It's a screenshot of Google.
Speaker 1: I'm impressed.
Speaker 2: Maybe you should make it a success then.
Speaker 1: It's going to be a little difficult, more difficult.
Speaker 2: Yeah, I mean, I was going to, but the whole drop down menus and stuff.
Speaker 1: What we want to search for is not quite agreed on.
Speaker 2: We never agreed on what we want to know.
Speaker 1: be able to search for. No, it's not as it is. So yeah, do you want to, you know, just get
Speaker 2: together and think about the different types of search we could possibly do and then we could
Speaker 1: discuss that next meeting, which options we really want to include. That would probably involve
Speaker 2: research in the query language a bit as well to see what that can do. It would be nice to
Speaker 1: I don't know, meet up and you can sort of show us a bit, but you know already, so we don't
Speaker 2: sort of have to do all the work again, just like figuring out stuff.
Speaker 1: Oh, just like the basics.
Speaker 2: No already, what?
Speaker 1: Just like accessing the corpus and stuff.
Speaker 2: Oh.
Speaker 1: Just like I'll be answering the code and just sort of how, just to see the basics of what you've done,
Speaker 2: like just get a quick look over and just take it through a tutorial.
Speaker 1: Yeah.
Speaker 2: Yeah.
Speaker 1: You know, the class paths, all that sort of thing, just to say, okay, well, here's
Speaker 2: Yeah, everything's basically something to do that, yeah, I'm just showing you how it vibrates, the code, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah I'm thinking so, some like that, and then if I have a classic one, I'll do it.
Speaker 1: Yeah, pick your time.
Speaker 2: Yeah.
Speaker 1: All right.
Speaker 2: Um, yeah.
Speaker 1: I mean, one day might be good.
Speaker 2: Yeah.
Speaker 1: One day.
Speaker 2: One day.
Speaker 1: Yeah.
Speaker 2: Yeah, this one.
Speaker 1: Just.
Speaker 2: Anytime.
Speaker 1: Not yesterday.
Speaker 2: Not if noon or two or four.
Speaker 1: No.
Speaker 2: In between those.
Speaker 1: Yeah.
Speaker 2: One, two, three.
Speaker 1: Three.
Speaker 2: Look.
Speaker 1: Actually.
Speaker 2: Yeah.
Speaker 1: Awesome.
Speaker 2: Three.
Speaker 1: Three.
Speaker 2: Yeah, that's an option too.
Speaker 1: Yeah.
Speaker 2: Okay.
Speaker 1: Three, good day.
Speaker 2: But we have.
Speaker 1: What do you, what do you, for?
Speaker 2: Like 330.
Speaker 1: I just, yeah.
Speaker 2: What does that mean?
Speaker 1: That's a zero.
Speaker 2: Three in the, in the computer room in here.
Speaker 1: And then we can just close to him there though.
Speaker 2: If you can't, can you get in front though?
Speaker 1: Oh, we haven't got a KD.
Speaker 2: Can none of you get in?
Speaker 1: We can get in front though.
Speaker 2: Through though.
Speaker 1: There's computer rooms in here, the MSC computer.
Speaker 2: I found that yet.
Speaker 1: It's in here.
Speaker 2: Who took her?
Speaker 1: Well, if you find me, I'll show you where.
Speaker 2: I'll let us all in there.
Speaker 1: We can look at that.
Speaker 2: We can look at now afterwards.
Speaker 1: Yeah, yeah, yeah.
Speaker 2: You did need to have a key for it.
Speaker 1: That's the thing.
Speaker 2: It's been a lot of the world, but.
Speaker 1: Yeah, somebody else was asking Steven about that.
Speaker 2: Whether we can get in there, whether he's going to give us access.
Speaker 1: Into work.
Speaker 2: The computer.
Speaker 1: Okay.
Speaker 2: Yeah.
Speaker 1: It's only got this crap.
Speaker 2: It's only got that four or five computer.
Speaker 1: But it would do quite a bit for our job.
Speaker 2: because it can also, it has not very of not many many people in it, right?
Speaker 1: Is there a printer in there too?
Speaker 2: Yes, printer in there.
Speaker 1: And there's a fight scope here.
Speaker 2: With the code on it.
Speaker 1: Yeah, yeah.
Speaker 2: It's good.
Speaker 1: Well, I'm just going to cover it.
Speaker 2: I've heard of that assignment.
Speaker 1: You've got it on my computer.
Speaker 2: Yeah, yeah.
Speaker 1: Yeah.
Speaker 2: So, what time do we say?
Speaker 1: I just think it's better to do afterwards than we have all the time.
Speaker 2: Yeah, that's all right.
Speaker 1: Yeah, that's all right.
Speaker 2: Yeah, that's all right.
Speaker 1: Yeah, okay, as long as female she doesn't go away, hopefully it's not that man's it won't let her
Speaker 2: Actually it's not even confirmed it
Speaker 1: What she doesn't even know what she's talking about
Speaker 2: Maybe it doesn't happen at all
Speaker 1: No, it's really weak next week should we should it really well supposed to be next week
Speaker 2: It's week three next week I don't think we have a reading week that I don't know we have one class at least when we like speech perception
Speaker 1: We don't have any lectures, but I think I like all other classes though
Speaker 2: Yeah, I don't think there's not my point. I don't think there was an official one last semester
Speaker 1: I think it was just a parkour. There was that
Speaker 2: Some classes did and some classes didn't
Speaker 1: Yeah, we should have been there. I think the other judges had
Speaker 2: You know, we're up to the professor and I don't feel like you can work
Speaker 1: I think the I'll probably have one to make up for missing classes
Speaker 2: What?
Speaker 1: The I'll probably.
Speaker 2: Yeah, we will probably have.
Speaker 1: Yeah.
Speaker 2: Just be in the last week.
Speaker 1: Okay.
Speaker 2: Just be my name.
Speaker 1: Yeah.
Speaker 2: I guess that's it.
Speaker 1: What's there anything else?
Speaker 2: Do anyone know you want to like take care of this or should I take care of it?
Speaker 1: Okay. Oh wait, trust you. Yeah, I don't know if there was something. I think he basically said
Speaker 2: the same thing says in the comments. If I could read it.
Speaker 2: I think the top one, um, really want multiple windows from a single app. But most, we will probably want to go with the vault.
Speaker 1: Yeah, well, that was for this episode.
Speaker 2: Yeah, I think it's a comment so it plays it in the same as what you said.
Speaker 1: Yeah, exactly.
Speaker 2: And just the other comment about whether you want to do both speaker characterization and
Speaker 1: And now we have 7% of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course of the course But I'm now
Speaker 2: You should still hear? Yes, you are. Yeah
````

### EN2003a

````text
Speaker 2: Can you just remind me, I don't have to tick the note and okay thing until I finish writing,
Speaker 1: but it's only like go back to it, I tick okay again.
Speaker 2: Yeah, so if you're back to a page and you take it again to leave it for the second time.
Speaker 1: So, if I'm working, if I've done a page, I'm on the second page, I take it, say, I've finished that page, and I go back to it, so I can just write and then not take until I finish writing again.
Speaker 1: Yeah, so it's always often, you never have to do it before, fine, fine.
Speaker 2: I didn't believe all this stuff, it's just a main thing. And you can go on both sides as well.
Speaker 1: Okay, yeah, right. Why should we start?
Speaker 2: Well, I think the first thing, what have we got?
Speaker 1: Well, the first thing I think is we need to sort out the call for abstract, sort of the
Speaker 2: call for the titles because I think that's kind of overdue, right, yeah, so I volunteered
Speaker 1: to do that if you like, if I am, okay. So, I'll do that by, I think, was it Thursday today?
Speaker 2: I'll do that by the end of the week, can you go away?
Speaker 1: And was it your idea to stick a bit in it where you say, you know, we're inviting, like,
Speaker 2: from quite a wide audience from a gay priority to linguists?
Speaker 1: Yeah, we're going to do that, but I think we should probably send out separate calls.
Speaker 2: Okay, so we'll send one that we could mention the fact that we're inviting other people,
Speaker 1: but I think it will probably just, I mean, it probably won't matter too much to the other linguists
Speaker 2: that we're having other people there. We can mention it, but it's not going to be to a
Speaker 1: essential and we might actually just end up making them worry that they're going to lose
Speaker 2: their place or whatever. Yeah, separate causes good idea. But we do have to decide a priority
Speaker 1: thing so that's something else we can look at a little bit later down the line. So, so that's
Speaker 2: That's the one for Ling, basically, and I'll send that out.
Speaker 1: I'll do that today, or something more.
Speaker 2: Now, Claire, let's see other things.
Speaker 1: She can deal with the psychology.
Speaker 2: Psychology people probably are recognizing that's the best thing to do,
Speaker 1: she'll know which email address to use and everything else. So if one of us could
Speaker 2: email Claire, yeah, is it was that a volunteering? Yeah. Yeah, right. Yeah, we're
Speaker 1: doing it. So if Robert emails Claire and we're going to need to decide exactly
Speaker 2: what she's going to say on there. We might need to just remind her of the dates. Okay, she
Speaker 1: doesn't know. Yeah, she gets the dates right. And I know she already knows that it's just anyone
Speaker 2: doing cycling with sticks, basically. So that's fine, I'm actually kind of take care of itself,
Speaker 1: as well, if she just sends one arm around to everyone, then only the cycling links will say,
Speaker 2: it was for me. Yeah, exactly. But then there's a rest of people else and I think we need to decide
Speaker 1: whether the text for the actual call that she's going to rework something or I think she should just,
Speaker 2: I think she should just write her own, probably.
Speaker 1: I think she might be glad to see the one for the linguistics.
Speaker 2: Okay, so what we'll do, that's always question.
Speaker 1: The thing is that the main call will go out before she's got around to any way.
Speaker 2: So what we'll do is I'll copy it, I'll see see her on the...
Speaker 1: Because I can't imagine that there'd be an essential difference between it.
Speaker 2: No, there won't be, I just, the only thing I'm thinking is I want to make sure.
Speaker 1: want to make sure that it stands out as something applicable to them, that they don't go
Speaker 2: or we're just getting rubbish from, you know what I mean? Yeah. I want them to really know
Speaker 1: that it's addressed to them. And the good thing about Claire sending it is she's probably
Speaker 2: got a psych email address as well and it might look a bit more relevant to them.
Speaker 1: What's happening anyway?
Speaker 2: They know her.
Speaker 1: Yeah, exactly.
Speaker 2: They know her, et cetera.
Speaker 1: So if we, if I've cc the original one, then you can tell her that that can be the basis
Speaker 2: for the basis for her email.
Speaker 1: Just make sure that they know it's relevant to them, et cetera.
Speaker 2: And obviously in people at S, we've also got English language now, in a way we could send out that first call to them just as part of the same email because I think they're more likely to think it was relevant to them.
Speaker 1: I don't really know. I don't really know what you think about that. But I think we definitely should open it up to English language.
Speaker 2: I think particularly at the moment because they're really trying to sort of, yeah,
Speaker 1: merges into a one subject area. Even though it should be meaningless because we're all
Speaker 2: part of the school, I think that it does actually make a difference. So, I think we should
Speaker 1: invite them, but then we've still got the problem of a priority issue. So, you know,
Speaker 2: probably what I was thinking is certainly second and third year's absolutely need to
Speaker 1: be a top priority but then there's a kind of awkward question of where we put first
Speaker 2: years because they don't need to if they want to should they have priority. This is a
Speaker 1: kind of lower point but it kind of crosses over with deciding what we're going to do
Speaker 2: Well, do we have an idea of how many people are going to actually have a whole thing?
Speaker 1: Because I don't think it seems to me quite obviously.
Speaker 2: We're just doing track the number of second and third year students.
Speaker 1: Everything else is just I would favour doing it just on a first come first serve.
Speaker 2: Yeah.
Speaker 1: Okay.
Speaker 2: All right. Well, let's send out the course on this possible, see what reactions we get and then. Okay.
Speaker 1: But I mean, like, see, so you have me in with on summaries. We're going to do this thing for, um,
Speaker 2: I can't even remember. Was it two or three days? It's three days. Okay. And so how many, how many
Speaker 1: posters and talks? Right, actually. They were 20, 20 minute talks with 10 minute
Speaker 1: question time okay and you can run two in a row but probably I'm not three out of three two surgery but you think two in a row or three in a row could you
Speaker 2: turn it around and that's narrow in it yeah and then give it a 20 minute break
Speaker 1: perhaps yeah I mean the thing is every time we have a break there's a question
Speaker 2: whether we actually serve coffee and biscuits and things because that's a kind of
Speaker 1: logging thing to do.
Speaker 2: Therefore, go for a say, I'm thinking now, sloth off, what on a half hour each, so three,
Speaker 1: like just each, that will be three per day, times three, will be 27.
Speaker 2: So are you saying have say three sessions in a row and then do that twice in the morning
Speaker 1: in twice in the afternoon, so because of the morning plays in the afternoon.
Speaker 2: Oh, so just have an hour and a half in the morning, yeah. I mean, or twice in the morning
Speaker 1: once in the afternoon. I mean, would six hours a day be pushing it? Not necessarily,
Speaker 2: because I mean, the good thing is, would you get that many people wanting to give talks?
Speaker 1: Well, I suppose what we can do is think about the structure now and say, right, what's
Speaker 2: the maximum we can do. So I think that's about as much as we could do to have an hour and a
Speaker 1: half, then have a coffee break, then have an hour and a half, then have lunch, hour and a half
Speaker 2: coffee break, hour and a half. And so that would be 18 hours of talks, overall wouldn't it. But
Speaker 1: what do we say? So it's 1236 talks, is that right? Maximum 36.
Speaker 2: Okay, let's just put this down.
Speaker 1: How many seconds a third year?
Speaker 2: Um, students are there.
Speaker 2: Well, I could look, I've got that, there's the list, isn't there, postgraduate, that I maintain in linguistics. There are probably about 30 on there, right, okay? But, a good
Speaker 1: number of them are first years and I don't know, I mean just to get an idea, you planning
Speaker 2: talking. No, are you planning well, no, and I'm probably not. So there's a good chance that almost
Speaker 1: none of the first is going to volunteer. So if we had say 20 linguistics and even then, I mean,
Speaker 2: no, quite a few people who were abroad and who won't bother to turn up or can't make it or whatever.
Speaker 1: So, you know, it might be that we only get say 15 and you might, and then we could be left with 15 blocks for the rest of PPLS.
Speaker 2: So, at least we know that we've got an absolute limit of about 36 talks.
Speaker 1: yeah. Yeah. We're also going to be having posters out me and I should imagine that most
Speaker 2: people would rather do a poster than get a poster. And that's what the coffee breaks will
Speaker 1: before, and maybe lunch times, but coffee breaks are probably more like, or are going to be
Speaker 2: a better time because people will hang around, whereas people will likely to go off somewhere
Speaker 1: for lunch, aren't they?
Speaker 2: Yeah, but wouldn't we want to actually just dedicate an afternoon or a morning up to being
Speaker 1: a post-decession?
Speaker 2: Yeah.
Speaker 1: That's what I was about to say, post-decession is a good idea, because just the people
Speaker 2: presenting the posters are there and can say something about it. Actually, there's
Speaker 1: always a problem again than the people who are presenting the posters still get
Speaker 2: around to go and look at others. But people kind of like generally sort of sort
Speaker 1: them out and sort that out themselves. I mean, it's the thing about posters,
Speaker 2: unless you kind of say, you know, if your name is in the first half of the hour for
Speaker 1: that you can move and the other ones can't.
Speaker 2: So how long should a poster session be?
Speaker 1: How long will people want to mill around for looking at?
Speaker 2: I'd make it a whole morning or a whole afternoon.
Speaker 1: I mean, just because, like, one's that I've been to as well,
Speaker 2: people tend to kind of come and go from them.
Speaker 1: I mean, I'd say a whole, either a whole morning or a whole afternoon,
Speaker 2: at least but that's just I mean just based on the ones that I've been to. So that means we could have 30 talks
Speaker 1: plus one AM or PM of posters. And we could probably get quite a few in there, at least 6 anyway, at least 6.
Speaker 1: at least six posters, right in the session like how many can you have going on at once? Well that's just kind of dictated by the size of the space.
Speaker 2: I mean, would we have placed the boards or is it just going to be posted on the walls?
Speaker 1: Like, do we have anything else?
Speaker 2: I should have found this out.
Speaker 1: Are you guys second years of first year?
Speaker 2: First year.
Speaker 1: So none of us have been to this before.
Speaker 2: No.
Speaker 1: I've been to Durham postgraduate conference,
Speaker 2: and I mean every conference I've ever been to
Speaker 1: the posters of all's been in the coffee break,
Speaker 2: which is why.
Speaker 1: Probably because it's normally their limited on space.
Speaker 2: Actually, we have a message here from myths about the poster session.
Speaker 1: Yeah, poster session wasn't reduced in 1999 as part
Speaker 2: of the main conference.
Speaker 1: In 2000, it was held separately in October.
Speaker 2: The intention was to use it as a way
Speaker 1: to introduce incoming postgraduate students
Speaker 2: to the department's research culture.
Speaker 1: However, I did not pursue this idea the following year because the comments I received from
Speaker 2: students in 2000 were generally discouraging.
Speaker 1: On the other hand, I later learned that some students did find the October post-ecession
Speaker 2: quite useful experience.
Speaker 1: My suggestion therefore is to re-exemple the idea of post-ecession altogether and find a better
Speaker 2: way to implement it if there seems to be enough interest in it.
Speaker 1: Well, I think keeping it along the side of the conference is possibly one way of
Speaker 2: My last sentence, one possibility is to put it back in the main conference and let people choose between the people presentation and oppose
Speaker 1: Yeah, I think that's definitely the idea
Speaker 2: I can imagine it would seem a bit random just have like a post-session and just have a post-session
Speaker 1: What would it be at the beginning it so I suppose is it normally second years do it like just after they've come back for this
Speaker 2: Oh, you mean, um, I'm the October thing. That's what it would be. I think I thought a well, it seems to me that he was saying that everyone would do it because
Speaker 1: it's goal was to give the new intake. Yeah, but I don't think he means that it would be
Speaker 2: the first years who have only just arrived would do post. No, no, no, no, no, no, no, no, no. Yeah.
Speaker 1: Okay, so at least, but anyone who's right might do. Yeah, exactly. Yeah, I might do. I'm still a little bit
Speaker 2: out for that. So that's good anyway. So we've got an idea, I think there's 30
Speaker 1: talks and say 6, 10 posts is whatever we can manage to fit in the room. So we need to
Speaker 2: look at where we're going to hold it. We could have it in B9, but there's things
Speaker 1: all over the wall, there are those pictures that run all the way around, so can we take
Speaker 2: the pictures down, can we use being nine for the posters?
Speaker 1: Well, if generally they use poster boards, if there are some poster boards that we can get
Speaker 2: hold off, then that's okay, so poster boards and what I'll do, all the email myths about
Speaker 1: Right into the call that we are considering the idea of having a poster session, so people
Speaker 2: can indicate what they prefer to give a poster or a talk, but the ultimate decision is on
Speaker 1: our side because we have to see how it doesn't work out with the poster session.
Speaker 2: How does it work out with the top?
Speaker 1: What we'll do is, we can just say, if you want to do a talk, then just say so.
Speaker 2: And if you want to do a poster, then say you want to do a poster,
Speaker 1: and we can add to a base it around that.
Speaker 2: And if we get absolutely tons of people wanting to do posters,
Speaker 1: and we don't think there's, you know, everyone's kind of done.
Speaker 2: It's a cop out.
Speaker 1: Then we might have to sort of say to them, well,
Speaker 2: you know, would you consider doing a talk instead?
Speaker 1: Yeah, because, particularly the second and third years,
Speaker 2: because we need more talks and just, you know, do it like that.
Speaker 1: Yep.
Speaker 2: We could even say something like, you know, first year's might want to give a post or something like that
Speaker 1: because I don't know, maybe that's about I did. Just through a general suggestion at them.
Speaker 2: Let's see what happens, okay.
Speaker 1: Okay, so we got some sort of idea of the structure and how many talks we're going to be able to have.
Speaker 2: Well, the maximum. I mean, I guess that will evolve when we get a response from the people.
Speaker 1: Okay, that's fine, isn't it?
Speaker 2: So, I've, okay, so English language, we'll put on the main call and I'll just, I'll just kind of market it as the
Speaker 1: thing we're fixing with this language or something like that, I think.
Speaker 2: And is there the other main group then philosophy, yes, and informatics, we've got lots of
Speaker 1: things to come out as well.
Speaker 2: So I had a look at whether they do philosophy of language and logic and stuff here, and
Speaker 1: they kind of do.
Speaker 2: There's about three or four full-time members of staff that list philosophy of language
Speaker 1: as a major interest.
Speaker 2: So chances are they're going to have some PhD students that are interested.
Speaker 1: So do we think we should invite them?
Speaker 2: I think I'd be surprised if we got sort of four out of them.
Speaker 1: I think that would be still amazing if we did.
Speaker 2: So I think it's probably worth it.
Speaker 1: I don't think we're going to get inundated with requests.
Speaker 2: So I think it's worth asking them.
Speaker 1: That's an investment.
Speaker 2: Yeah.
Speaker 1: Interesting informatics would.
Speaker 2: I mean, I think informatics are definitely worth asking.
Speaker 1: There's CSTR and HCRC, I mean, I'm thinking that the informatics potentially is quite
Speaker 2: a big response.
Speaker 1: Yes.
Speaker 2: It is.
Speaker 1: It might be interesting stuff coming in, which something recently about, I think somebody
Speaker 2: master's project to look in how far English is actually or in how far English is a shaping
Speaker 1: influence on programming languages. All right, cool.
Speaker 2: Yeah, what do you want to ask them and put some kind of like provider in to make it
Speaker 2: specific to preemptively weed out the numbers, or should we just say to you, well, you know how I speak about that language and it would be nice to do it. The thing is, we can't afford to bias it towards any particular kind of linguistics in a sense, because it's such a, because of the way our department is, then we're supposed to sort of embrace all kinds.
Speaker 1: In fact, even by inviting people from informatics and from or maybe from philosophy and things,
Speaker 2: it might bias it in a particular direction, but I don't know, it's probably not too bad.
Speaker 1: I think that between philosophy and informatics and psychology, you've probably got quite
Speaker 2: or bread there anyway. The one thing is the only kind of people doing anything
Speaker 1: like applied linguistics are the applied linguists themselves and people in
Speaker 2: sociology with an interest in language and I don't think we'll be inviting them.
Speaker 1: But I don't think that's too bad because the first thing is there's a good
Speaker 2: reason for inviting everyone in PPLS because we are in one school and then the
Speaker 1: the fact that we also invite people from informatics. I suppose it's just that we do have
Speaker 2: pretty strong ties with them. I don't really want to be too offended. I hope not, you know.
Speaker 1: So yeah, so what kind of provides that can we put on? I mean, we could we could just say outright
Speaker 2: anyone in there, third year or anyone in their second or third year. But I don't know.
Speaker 2: Well, we can just take whatever we get and pick the best between us, which is, yeah, yeah. So you're most straightforward, yeah, just say it's just in the general thing, saying the
Speaker 1: linguistics department's having some conference and we're doing fine.
Speaker 2: So just from my text.
Speaker 1: You're going to email Claire, so who wants to send something out to inform our six?
Speaker 2: Right, yeah, that's fine. Yeah. All right, and if I get in touch with philosophy as well. Yeah, sure.
Speaker 1: So...
Speaker 2: Yeah, so what you want to say is anyone who wants to give a talk on logic or philosophy language,
Speaker 1: but put a warning that if it's logic, then there's a good chance that no one will understand or not that many.
Speaker 2: I mean maybe if you just put yeah just put philosophy of language that's that's probably
Speaker 1: good yeah I mean we're just all and you send them a thing same thing with another part
Speaker 2: of course it is having a postgraduate thing so if you're a philosophy student with you
Speaker 1: know your work has got an interest in language yeah yeah that's yeah that's what we do
Speaker 2: yeah I think the random ones we need to say that's right so you've got to work out
Speaker 1: What I'm going to do is the king who's just sending them your call, the papers and changing
Speaker 2: it slightly to say yes and less few students, yeah that's fine, that's fine, that's
Speaker 1: what you want to do, as long as it's clear from the subject bar that it's relevant to them
Speaker 2: and that it says somewhere that for philosophy students we're in an interesting language
Speaker 1: and that's it and then between us we'll have to have another meeting and I mean at the same
Speaker 2: time is we're sorting through all the other titles and deciding how to divide up the
Speaker 1: sessions. Someone suggested to me that it's actually better to have talks on a similar
Speaker 2: topic spread out as much as possible which to me just seemed absolutely crazy and the
Speaker 1: reason she gave me was something to do with taking out like a whole day or a whole
Speaker 2: after and you would be quite difficult. But I think that balance against the fact that most
Speaker 1: people want to be able to say, well, look, I can have just this one day off as opposed to what
Speaker 2: I need an hour over three days. You could end up having to take three afternoons or three
Speaker 1: mornings or whatever off. So I think in general, and also for the sake of the lecturers.
Speaker 2: I think a lot of the time Simon Kirby's already said to me that anyone, any of his students,
Speaker 1: he wants to be on the first day on the Wednesday. Right. And that's because I
Speaker 2: shifted it. I basically had it on Monday to say Wednesday to begin with. And then
Speaker 1: it moved down twice to Wednesday, Thursday, Friday. So Wednesday is the only day left
Speaker 2: that he can make. Oh, I see right, he won't be there because he'd say he can make it. Okay.
Speaker 1: Yeah. So and the other thing is when we get some calls say we have, for instance,
Speaker 2: three people supervised by Bob Black, then it might be that then we are going to have to
Speaker 2: contact Bob and say Bob, these three of your students are going to be talking, presumably you want to be there, so can you give us a time that would be good for you and then we can
Speaker 1: put them in a block at one time because he says yeah okay Thursday afternoon I've got completely
Speaker 2: free and so I think we do need to stick everyone together, particularly if they've got the same
Speaker 1: supervisor and it's also good if talks are on the same topic for a whole morning or a whole afternoon
Speaker 2: because then people would come along and go oh this morning it's all on phonology or the
Speaker 1: this morning, it's more on the blinding wrist and then okay, as much as possible anyway.
Speaker 2: And that's so far, it's just a general statement of interest, what we intend to do, what we actually get to do with the later, what we have this stuff.
Speaker 1: Yeah. Now, if I'm going to send out this call, we need a deadline for titles.
Speaker 2: So what should we say something like, because we need a deadline for titles and a deadline for abstracts.
Speaker 1: So let's set the latest deadline that the sort of abstracts deadline first.
Speaker 2: Because we need to have a meeting and that's going to be when all the real work starts.
Speaker 1: So, what's the absolute latest, I mean, maybe the end of two weeks ahead, end of March,
Speaker 2: end of March might be okay. I'm going away for two weeks on the fourth of April,
Speaker 1: and then I'm coming back just in time for the conference. So any organizing, at least
Speaker 2: stuff where I need to be, we need to meet physically. It has to be done before that. Yeah, and that will be a way,
Speaker 1: probably until Easter. So this actually means we have the week directly after Easter between
Speaker 2: my coming back and you're leaving. I tell you one thing, it's starting on the Wednesday and the first
Speaker 1: day back is Tuesday. I think I'm coming back. I'm trying to get this right. Hope for
Speaker 2: I'll be back in time that we'll be able to do something the day before because I think I'm going to be back
Speaker 1: Might even have to come in the evening, but that's not the end of the world, but we might have to set
Speaker 2: somethings up like maybe just get the chairs organised or whatever we might actually have to go into the rooms and get things ready
Speaker 1: and
Speaker 2: there's going to be other things like
Speaker 1: getting the technology ready so
Speaker 2: not only is there a pressure to have
Speaker 1: Talks that are on a similar topic together, but also if people need the same kind of computer set up
Speaker 2: It's good to have them together, so we don't have to keep changing it. So
Speaker 1: Because I think it was said Rick has already offered to do whatever
Speaker 2: We need him to do, but he just needs to know in advance what people need so that he can be there and get it ready for them
Speaker 1: So I think when things do you think people are actually going to need well
Speaker 1: Well hopefully most people will either have something like PowerPoint or they'll just have PDF slides or something. Hopefully no one will have anything too specialised.
Speaker 2: And my experience with what you usually should have is some kind of, what's it, overhead?
Speaker 1: Yeah, I think it will be more, in some cases we might, if it's really tough, we might
Speaker 2: be in need of a, of some sound system, I don't know if you did, it hasn't got all of that.
Speaker 1: Yeah, it's got a lot in there, but I think it does take a little bit of, I mean, I think
Speaker 2: sometimes maybe people need to be in lean, rather than wind those, so booting them out.
Speaker 1: Yeah, it's sometimes an issue, I think.
Speaker 2: But I think what we should say is when I put out this call, I'll put both deadlines and I think
Speaker 1: I'll say that when you send in your abstract, you need to mention it any technology you intend to use.
Speaker 2: So at least if we have all the information.
Speaker 1: Yeah?
Speaker 2: Yep.
Speaker 1: So deadlines.
Speaker 2: Okay, so let's think about this. If we gave them a whole month or just over a month,
Speaker 1: then that would be okay, wouldn't it? Because we've still got...
Speaker 2: I don't know, it wouldn't be okay at all.
Speaker 1: If we gave him the whole month that it gives us hardening of time.
Speaker 2: So, if we gave them, say, till mid-marked, that would be good.
Speaker 1: So, give them something like, give them something like 10 days,
Speaker 2: or whatever, to get the title in.
Speaker 1: And then give them a week on top of that, to get the actual abstract done.
Speaker 2: And the abstract doesn't have to be much.
Speaker 1: It's probably only half the side of A4 or something, isn't it?
Speaker 2: just enough that we can see whether it's interesting or what kind of area it fits into. That's all we're
Speaker 1: reading it. See, ideally, I would like to have given them a bit longer, but I think that'll be
Speaker 2: an ugly anymore. Okay. So unfortunately, I don't have a calendar. It's a little bit of a way.
Speaker 2: You're going to send that band crazy. That's too.
Speaker 1: No, I think it's okay when you're not working on it.
Speaker 2: So...
Speaker 1: So...
Speaker 2: I don't know, it's 28 this.
Speaker 1: this month, isn't it?
Speaker 2: Yeah, so if we have it like a Monday, Monday, the 14th, it'd probably be quite good for the final deadline, and then if I send it out tomorrow we'll say something like the
Speaker 2: or maybe the fourth would be good, so give it a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a little bit of a to get back with the title, say get back with the title by the 7th, or do we need to be a weekend?
Speaker 1: Yeah, that would be a weekend anyway, but you can give them 10 days to, you can give them 10 days to get the title.
Speaker 2: Yeah, yeah. It depends which way round you want to do it. So what's going to take them longer, actually, to decide what they're going to do and send the title.
Speaker 1: Or is it going to be on the basis of the title? Do they want more time to write the abstract?
Speaker 2: I think if they're really serious to be a bit late with the title might not be
Speaker 1: bad because it will help them to, so given the sevens. Yeah. Yeah. Okay. So, so Monday the
Speaker 2: seven is the title and this presumably will apply across the board. Yeah. And
Speaker 1: Monday the 14th for the abstract and we've got that we've got an email address
Speaker 2: to send those to you, or was it? Well, we kind of have. We were given...
Speaker 1: Gachi, access to the account. They only think he's accessing the account. They can send it
Speaker 2: to PGC at Ling. Yeah, as long as we can get the... Yeah. I'll take what I'll do then. I'll go and see
Speaker 1: mic today and get the password and everything because we possibly have it but I'll just
Speaker 2: sort that out with it because if we're going to tell everyone to email PGC then we have to
Speaker 1: make pretty sure that we can actually access the account and then it's operational and stuff
Speaker 2: because so far I've just been using my own email address but it would be better. It's quite easy
Speaker 1: to send from an email address because you can send from any email address you like it's just the
Speaker 2: the fact that when they reply to it, you need to be able to access it. So I already tried
Speaker 1: it once, and I'm sure they gave us a password, and I even, I will ask it. We've got it
Speaker 2: to all. So does it? I mean, you may already know, but the thing is, if you want to send
Speaker 1: this call for abstract, you know, when you do the philosophy and the thing you want, then
Speaker 2: if you want to send from PGC, then you might already know, but you can go, if you did
Speaker 1: it from WebMail, you can just create a new account for yourself and where it says it actually
Speaker 2: has a send from address and you can just put PGC and just do it that way or depending
Speaker 1: on your normally male client, you might be able to do it, but it doesn't matter too much.
Speaker 2: The other thing you could do is just fill in the reply to addresses, PGC, depending on
Speaker 1: what you want to do, but that's what I'll do, I'll send it from PGC so if anyone replies
Speaker 2: it will just go to that account and any of us can access it at any time, presumably you
Speaker 1: can access this up from workmail or, you know, or I map or whatever, should I take care
Speaker 2: of the web page?
Speaker 1: Yeah, if you want to create a webpage and just copy my email into it or something and anything else you might want to do.
Speaker 2: Yeah, and then later on we can put the program in.
Speaker 1: Yeah.
Speaker 2: Cool.
Speaker 1: Okay, all right, yeah, I'll tell my, is it five, is it not twice, two or three minutes
Speaker 2: or two, you've got so much to it, two of them, all right, okay, so very quickly then, can
Speaker 1: we arrange a new time to have a meeting. Do you think we need to, how long do you think
Speaker 2: until we need to meet again? We've got enough to be getting on with. You probably have
Speaker 1: of the way. Yeah, I mean, that's just, um, so, I mean, maybe, I mean, ideally I suppose it will
Speaker 2: meet again here, so we can arrange with Melissa and we'll just send that an email. Okay. Yeah,
Speaker 1: in about that would be cool. Okay, so, um, I mean, I won't get in touch with or I won't send anything
Speaker 2: to plus few new metrics till I've got your email. Yeah, I've just sent a slide, a modified version
Speaker 1: But I'll try and get a good address to send it to you.
Speaker 2: So that was a note and I'm okay.
Speaker 1: I think later as soon as the call is out.
Speaker 2: Because then we have the call thing.
Speaker 1: We have that way and look at the board.
Speaker 2: Organizatory of stuff like do we know about chairs t and stuff all right?
Speaker 1: We finished okay
````

### IB4001

````text
Speaker 2: Okay. So, as you guys know, Cisco is too small. Well, the building is too small for
Speaker 1: our groups. So, we're moving to a new building. It's going to be the building across the
Speaker 2: street and we're actually moving in three weeks. But the problem is that the administration
Speaker 1: wants to know who's going to be in what office in the new building and where we're going
Speaker 2: and put things like the printer, the fax machine,
Speaker 1: all the big equipment.
Speaker 2: And the catch is that they have the final approval
Speaker 1: of where we put people and equipment.
Speaker 2: And they want to know where we're going to do
Speaker 1: all of this by November 2nd.
Speaker 2: So that means basically next Tuesday.
Speaker 1: And since we don't really have any other time,
Speaker 2: we have to make these decisions today.
Speaker 1: What we're getting is nine rooms for a maximum of 18 people,
Speaker 2: which is OK, because there's only 15 of us.
Speaker 1: And all the rooms have windows, luckily.
Speaker 2: So there's no fights with it.
Speaker 1: It gets a window in who doesn't.
Speaker 2: There's two views either of the old town or the mountains.
Speaker 1: And the rooms I very size is.
Speaker 2: There's two three people rooms.
Speaker 1: Five two person rooms, which are on the corners of the building.
Speaker 2: So you actually get windows on two walls.
Speaker 1: And two one person rooms.
Speaker 2: That's pretty much what the building looks like.
Speaker 1: And then you have the number of people per room.
Speaker 2: The courtyard, because we're on the sixth floor,
Speaker 1: you can actually go out to it.
Speaker 2: but just means that the windows look out
Speaker 1: onto open space.
Speaker 2: You can see the bathrooms, the elevators,
Speaker 1: are further down the hall.
Speaker 2: The purple bar at the bottom sort of on the right
Speaker 1: is the mailboxes.
Speaker 2: All of the windows open, you can get out onto the terrace
Speaker 1: just like we can in our normal building.
Speaker 2: And the equipment that we have to put somewhere
Speaker 1: are, like I said, the photocopier,
Speaker 2: which is really big, the fax machine,
Speaker 1: which is not so big and a printer,
Speaker 2: which is relatively big.
Speaker 1: Each office has a white board of bulletin board
Speaker 2: and a coat rack.
Speaker 1: No cupboards like we have in the current offices.
Speaker 2: And each person gets their own chair,
Speaker 1: their own corner desk,
Speaker 2: so like the ones that we have now.
Speaker 1: A small filing cabinet with three drawers
Speaker 2: and my small I mean there about that tall.
Speaker 1: And one sort of hanging shelf.
Speaker 2: So we don't get the bookcases like we have now,
Speaker 1: just one shelf that's attached to the wall, and the people that we have to place, you can
Speaker 2: see the list there, along with their position and the project that they work on. And I guess
Speaker 1: the first question is how we want to organize people, whether we want to do it by rank
Speaker 2: or by project or, I don't know, put all the PhD students together, all the professors together,
Speaker 1: that sort of thing. So the idea is that we come up with a plan. There's another group
Speaker 2: who's going to be working on the same plan later this week, and then Andre and I have to do
Speaker 1: presentations for the University of Administrators on the second. So I have to come up with a plan,
Speaker 2: possibly if we have time of presentation, quick presentation with arguments for why we think our
Speaker 1: plan works best. Okay, all right, so anyone have any ideas or I guess, do we know if
Speaker 2: there will be a lot of people coming across the whole in terms of security stuff if we can,
Speaker 1: I mean, my idea is to put the photography on the facts in the whole. Yeah, um, I think it's
Speaker 2: The security is sort of the same as it is in the current building, so as long as the things are physically attached to the wall so they can't be removed, then it should be okay to leave them in the hall.
Speaker 1: It's just a question of whether you're printing the sensitive documents or whatever.
Speaker 2: So we only get one printer for 15 people?
Speaker 2: Well, we get one sort of networked printer, and then I think some of us have personal printers.
Speaker 1: You know, things Susan has a personal printer, just Ella has one maybe.
Speaker 2: Yeah.
Speaker 1: I can't remember who else.
Speaker 2: Yeah, but no one else gets their own printer.
Speaker 1: In terms of equipment, it's sort of the same thing as we have now.
Speaker 2: So, what I'd propose is that we sort of discuss various concepts without getting into specifics and then go off and think about it over lunch and then come back later in the day with sort of more specific proposals as to exactly where to put people.
Speaker 1: Does that work? Oh, and on the map, the little half circular, more quarter circles or doors, which I'm assuming you figured out for just in case.
Speaker 2: And there's just the one room that actually has two doors going into it, the three-person room on the right.
Speaker 1: Yeah.
Speaker 2: And do we need a room like a reading room?
Speaker 1: Yes, a lot of people were saying that they wanted to have a reading room.
Speaker 2: That's a good idea.
Speaker 1: So we should leave a space for that.
Speaker 2: And we can't, because like I said, maximum 18 people in those rooms, and there's only 15 of us.
Speaker 1: And I don't know if you noticed, but two of us are only here half the time.
Speaker 2: half the time, so Martin David, or half the time at the EPFL and half the time in Geneva.
Speaker 1: So sort of keep that in mind, I guess when you're doing the actual planning.
Speaker 2: So first split we can do is between administration and researcher, it's completely different
Speaker 1: work.
Speaker 2: So we can deal with administration and decide something for administration and then the other.
Speaker 1: Yeah.
Speaker 2: But, Jisal is really the only.
Speaker 1: Yeah.
Speaker 2: But at least deal with that particular situation and then see with the other.
Speaker 1: Because I was thinking, Jisal is quite, I mean, Jisal has worked.
Speaker 2: is quite noisy because it's secretaries so yeah a lot of phone call and stuff like that.
Speaker 1: And she's always moving around.
Speaker 2: So you want share our face with Gisola unless you are 50% and not the 50% Gisola is working.
Speaker 1: Yeah.
Speaker 2: Which is another condition.
Speaker 1: Which I don't know if we can assume that there isn't going to be any overlap between them.
Speaker 2: I don't know, maybe we can decide that Jesus likes having one of the one person room.
Speaker 1: Yeah, I would suggest that too, yeah.
Speaker 2: Maybe coming in.
Speaker 1: Yeah, are there that are maybe put her in a two-person room with the equipment,
Speaker 2: or like with the photocopter, or maybe not the photocopter, but the printer?
Speaker 1: Yeah, but at least the thing we know that Jesus is going to be alone.
Speaker 2: Yeah, yeah.
Speaker 1: always equipment but not with a hundred percent staff and staff worker. Okay so it's a
Speaker 2: one person room but we don't know how big they are or it's hard to tell. I mean
Speaker 1: Jisella has this funny typing. Yeah. I mean the rooms aren't tiny if you look at the facts.
Speaker 2: So probably she should get the facts right. Yeah yeah that makes sense.
Speaker 1: to put the facts in there.
Speaker 2: And then I think the main discussion we should have is if we want to make group of
Speaker 1: amongst the same project or amongst the same title.
Speaker 2: Yeah, a professor asks us to answer.
Speaker 1: Or, yeah, a couple of professor and assistant.
Speaker 2: Or, yeah.
Speaker 2: That's more conceptual question than a practical question. Well the third option is just completely mix everyone up, which some people say is better
Speaker 1: sort of for group environments so that you're not stuck only with the people who are working
Speaker 2: on your project.
Speaker 1: So if you share an office with someone who's on a completely different project, you find
Speaker 2: out about that project but you also sort of interact with other people on a more regular
Speaker 1: but still I find it's quite easy if you are with people who work in the same
Speaker 2: project in the same way because you have the meetings or people come and ask you
Speaker 1: discuss things maybe I don't know if it's for the people who start working
Speaker 2: same project. Yeah but we will have this reading room. Yeah that's to which
Speaker 1: gets. We will be dedicated for reading and for studying or can we have meetings
Speaker 2: that I can reserve it for meetings, but who fed?
Speaker 1: I think it's not a question of preserving it,
Speaker 2: because there's other rooms at the university
Speaker 1: that you can reserve for a meeting.
Speaker 2: But if it's empty, then sure, you can use it for a meeting.
Speaker 1: There's nothing wrong with that.
Speaker 2: But I think if someone's already reading in there,
Speaker 1: it's not fair to go and kick them out,
Speaker 2: just because you want to have a meeting.
Speaker 1: Well, the problem is you have to go across the building
Speaker 2: and it adds some overhead every time you want to have some short meeting.
Speaker 1: and discuss some issues, maybe we shouldn't call it.
Speaker 2: But if you're having a short meeting, you don't really make an appointment for it.
Speaker 1: You just kind of go to someone's office and go down for a coffee or whatever.
Speaker 2: Because there's still the cafeteria that you can use for informal.
Speaker 1: Yeah, the other thing we should take into account is if you receive student or not.
Speaker 1: Because, yeah, Marian and I interact a lot with students and we have reception hours and stuff like that. So it means you get time where a lot of people come along and talk and...
Speaker 2: And the other Marian does too.
Speaker 1: Yeah, so maybe it's just really nice to have to share on a face with somebody like us, have a lot of social life and...
Speaker 2: Well, but then you either share offices with each other, which doesn't really solve the problem
Speaker 1: problem, because chances are you're not going to have office hours at the exact same time.
Speaker 2: So you're still going to have, like, unless you get individual offices, I don't know if
Speaker 1: there's an easy way to find a solution for that, because even if each of you share
Speaker 2: with the professor than it's the same thing for the professor but it is something to keep in mind.
Speaker 1: Unless you end up sharing an office with someone where your schedules completely don't overlap
Speaker 2: and then you schedule office hours when the other person isn't there. Some people come in around
Speaker 1: alive and some people come in around eight. Yeah, but that's something we can't reasonably assume
Speaker 2: Like that.
Speaker 1: No.
Speaker 2: Make plans with that, because...
Speaker 1: No, but you sort of see people's patterns.
Speaker 2: Yeah.
Speaker 1: Even if it's not always like that.
Speaker 2: I mean, if it's like that, 80% of the time, then...
Speaker 1: And but you're right, we can't make assumptions too much.
Speaker 2: people would like to see the office organised by by rank like professors and students.
Speaker 1: I don't know.
Speaker 2: I think.
Speaker 1: Well, it's up to us how we do it.
Speaker 2: I can see benefits of both.
Speaker 1: Yeah.
Speaker 2: One point I can say by experience.
Speaker 1: It's really hard to share an office with three people because it makes much more
Speaker 2: Now he's that only being two in an office.
Speaker 1: Yeah, plus the computers.
Speaker 2: Let the computers.
Speaker 1: So when we all know what it's like that five computers in your office.
Speaker 2: Yeah.
Speaker 1: So it might be a good idea to first exclude one of the three person room to be the reading room.
Speaker 2: And not to be necessary.
Speaker 1: A room with three people.
Speaker 2: They're working work.
Speaker 1: Yeah, but if there are people coming in,
Speaker 2: I mean, we have these people working for two months who come in the summer time or something.
Speaker 1: I think we should reserve a little bit space for them to, so...
Speaker 2: Yeah, that's a good point because if we take the three-person room out as a reading room,
Speaker 1: it's quite...
Speaker 2: Then everyone has an office, right, because it's maximum 18.
Speaker 1: So take away three spaces and you're down to your 15.
Speaker 2: And you're right, if we do have a stage year or whoever comes in, then we have no word.
Speaker 1: Well, we can put them in the reading room, but that kind of defeats the purpose.
Speaker 2: So, the other solution is to say, okay, we use the three-person room,
Speaker 1: but only with two-person each time, and leave a spare space for the changes in the matter.
Speaker 2: Yeah.
Speaker 1: But avoiding having three-person full-time in the same room.
Speaker 2: It could be a good idea, I think.
Speaker 1: Or again, find people who don't work in the same hours.
Speaker 2: Yeah.
Speaker 1: I just completely solve the problem.
Speaker 2: So, for the reading room, we will have a two-person room.
Speaker 1: Yeah, I think so.
Speaker 2: Everybody agrees on that too?
Speaker 1: One-person will be too small anyways.
Speaker 2: How about the room?
Speaker 1: The one that's the bottom?
Speaker 2: Yeah, the bottom and the middle.
Speaker 1: Yeah.
Speaker 2: mountains yeah it has three windows so I think it's two well which there's three
Speaker 1: two person rooms the middle one has two windows yeah which is fine and still a big
Speaker 2: room big black stripe is the windows oh that is seen one between the big okay yeah
Speaker 1: sorry should have explained but whatever the the other one which has only one
Speaker 2: windows but in the courtyard it may be more quiet. Yeah but then you get to get a lot of light
Speaker 1: for reading. We have electricity so I hope. Really?
Speaker 2: Needs a question I mean it's quite noisy outside with the streets and
Speaker 1: on the sixth floor I don't know. Yeah we are on the sixth floor. I know I like the idea of
Speaker 2: looking out over. Yeah, it's a relaxing room. Well, that's the whole point, right? It's
Speaker 1: just somewhere to get out of your office and go and do some new things else for a while,
Speaker 2: whether you're reading or just kind of staring off into space. You can look outside of the window
Speaker 1: if you have a quick meeting room. So with that one of the room in the corner, so you have three
Speaker 2: windows, it's even better. Yeah, we could do that one. But you have less wall to put shelves and
Speaker 1: If you intend the reading room being more, the library all.
Speaker 2: We have some shelves, like cabinet type shelves for the reading room, but it's not really
Speaker 1: intended to be a library, I mean, we have an empty library downstairs, but the other
Speaker 2: ideas to take, because right now we all have bookshelves, so what idea might be to take sort
Speaker 1: of the books that aren't frequently used by people, but them all into that room, so it
Speaker 2: becomes a sort of kind of, yeah, small library, but not like a library, no, no, no, just
Speaker 1: no, just go and borrow your colleague's books, so are we all agree about these two person
Speaker 2: rooms, which one, I don't know, I don't know, I don't know, I don't know, I don't
Speaker 1: I think the middle one.
Speaker 2: The middle one.
Speaker 1: Yeah.
Speaker 2: It's also sort of central to the layout.
Speaker 1: So everyone sort of has more or less the same distance to.
Speaker 2: It's not that it makes that much of a difference.
Speaker 1: Mm-hmm.
Speaker 2: But why not?
Speaker 1: So we can exclude this one to make enough of this.
Speaker 2: Yeah.
Speaker 1: Actually what I can do is.
Speaker 2: Oh, it may be right on the board.
Speaker 1: Yeah.
Speaker 2: I don't know.
Speaker 1: actually it's a good idea. Just put it up. So we have the map and so this really isn't
Speaker 2: two scale but oh well um that's really not to scale alright good enough um so we've got
Speaker 2: And I'll just there, there's two, and one, three, yep, yeah, oh, so, okay, so this is that and this becomes the reading room, right? Is that a mountain? Yes, okay. And the Jisela? Yes, we decided also the administration stuff.
Speaker 1: So we exclude the thing we are quite sure and then we discuss there.
Speaker 2: I was thinking of maybe we should assign Gizella into this three person office because we will probably place the printer next to the mailboxes.
Speaker 1: And we could have Gizella and the 250% people sharing the three person room.
Speaker 2: That's really noisy to be in the same office.
Speaker 1: the administration. But if Gizelle worked 50% and they work 50%.
Speaker 2: Yeah, that just imply you expect people to come when Gizelle is not working. That's true.
Speaker 1: And that's not really fair if you. Yeah. Well, I mean, so we can put Gizelle in the two
Speaker 2: people room, which is near the mailbox.
Speaker 1: Yeah, we could. I don't know.
Speaker 1: I mean, I don't know how noisy she is. You always have the phone ringing, don't you have even when she doesn't have her own
Speaker 2: printer?
Speaker 1: Yes, yes, she does.
Speaker 2: Yeah, but that's a good point from Nicos to say that she needs to be near the mailbox
Speaker 1: and the printer.
Speaker 2: Well, if you put her in the photography and this room here, it's relatively close.
Speaker 1: Except the door is not really convenient for convenient chair.
Speaker 2: But I think if the main, how can I put that?
Speaker 1: If the main reason to choose this last place
Speaker 2: is the proximity of the mailbox,
Speaker 1: It should be a two people room and not three people room.
Speaker 2: Okay.
Speaker 1: It's fine with me.
Speaker 2: Otherwise, we have one people room and...
Speaker 1: I don't know how much the proximity to the mailbox matters,
Speaker 2: because usually when she's here and she picks up the mail,
Speaker 1: she actually brings it to your office.
Speaker 2: Yeah, it's more the administration that uses her mail office.
Speaker 1: This is the place of the photography.
Speaker 2: Yeah.
Speaker 1: And the place where we all pass kind of.
Speaker 2: Yeah.
Speaker 1: That's true.
Speaker 2: Because if we put the photography near the mailbox and it seems to be the only place where
Speaker 1: there is room for that.
Speaker 2: Yeah.
Speaker 1: And let you put it into an office which is just annoying, I think.
Speaker 2: Yeah.
Speaker 1: I think if you put it into Giselle's office, it's going to be, and it's to begin.
Speaker 2: Yeah.
Speaker 1: Okay, we should try this down.
Speaker 2: Do we agree that the photocopier and the network printer goes next to the mailbox?
Speaker 1: Yeah, that's good.
Speaker 2: And then we can...
Speaker 1: ...for the moment which is aligned this corner room.
Speaker 2: If you agree.
Speaker 1: I don't know.
Speaker 2: Yeah.
Speaker 1: But at the beginning we said that we were going to...
Speaker 2: that we were going to give her one of the one person rooms.
Speaker 1: Yeah.
Speaker 2: But there were this option of putting in the Lanier, the photography.
Speaker 1: Yeah.
Speaker 2: I mean, she's sharing enough, it's right now.
Speaker 1: And has anybody heard of any complaints that she's allowed?
Speaker 2: I mean, she's sharing enough.
Speaker 1: I mean, we put some fresh airs in there.
Speaker 2: In Gisela's office, because there is a spare room.
Speaker 1: And they're not really in a position to comply.
Speaker 2: That's quite, I mean, that's quite important to keep a spare room
Speaker 1: in Gisela's office, if we need more staff.
Speaker 2: But I wouldn't work in Gisela's office.
Speaker 1: I think it's just a question of work conditions.
Speaker 2: like if you're a stagier and you're only coming in for two months, then you can put up with it.
Speaker 1: But if you're there, you know, for example, for the fall of the year.
Speaker 2: So like there is no room in the cupboard for any people except Gisela because she got lots of people
Speaker 1: and lives and lives and stuff like that. So it's really she needs, she needs space, space.
Speaker 2: Yeah, yeah. But we can reserve, so if you reserve a two-people room, we can put
Speaker 2: the trainees. Yeah, they're in the same room. Yeah. Okay, so do they let the south west of this? Yeah. Yeah, the corner. Are you sure it's southwest? I believe if this map is...
Speaker 1: South west, if that's north. Okay, the map is... South west for us. No, no, no. Well, I'm assuming that's
Speaker 2: That's what you meant, right?
Speaker 1: Yeah.
Speaker 2: That's what I mean.
Speaker 1: That's what I mean.
Speaker 2: That's what I mean.
Speaker 1: That's what I mean.
Speaker 2: That's what I mean.
Speaker 1: That's what I mean.
Speaker 2: That's what I mean.
Speaker 1: That's what I mean.
Speaker 2: That's what I mean.
Speaker 1: That's what I mean.
Speaker 2: That's what I mean.
Speaker 1: That's what I mean.
Speaker 2: That's what I mean.
Speaker 1: That's what I mean.
Speaker 2: That's what I mean.
Speaker 1: That's what I mean.
Speaker 2: That's what I mean.
Speaker 1: That's what I mean.
Speaker 2: That's what I mean.
Speaker 1: That's what I mean.
Speaker 2: That's what I mean.
Speaker 1: That's what I mean.
Speaker 2: That's what I mean.
Speaker 1: That's what I mean.
Speaker 2: That's what I mean.
Speaker 1: That's what I mean.
Speaker 2: That's what I mean.
Speaker 1: I'm sad, this guy told me, so I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good, I'm so good So it just means that the 3 piece room, which is in the opposite of the north east, is the more sunny one.
Speaker 2: That's one.
Speaker 1: Let's say that.
Speaker 2: It's the one you have now, you both.
Speaker 1: It's the oven.
Speaker 2: Well, there's a lot of stuff.
Speaker 1: You get the sunset and no.
Speaker 2: And it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really warm and it's really Okay, good. So, how many rooms and how many places do we have?
Speaker 1: So, we have reserved to change it on here as well.
Speaker 2: That's jazala.
Speaker 1: Yeah, plus one plays a place, but really the last place to be used.
Speaker 2: Plus facts.
Speaker 1: Yeah.
Speaker 2: Mm-hmm.
Speaker 1: And then this is the reading room.
Speaker 2: Okay.
Speaker 1: Oops.
Speaker 2: Um...
Speaker 2: So that leaves us with what we get two, three, four, four, 14 places, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people, 14 people So I'm going to take Juzala off of that list as well, I'll put her in gray, I guess.
Speaker 1: Can we group people by their name?
Speaker 2: I don't know.
Speaker 1: I don't know.
Speaker 2: I don't know.
Speaker 1: So it's going to be Marianne's house.
Speaker 2: Is there anybody who's not happy with you?
Speaker 1: who's not happy with the current situation, so we could try to just keep the same arrangement
Speaker 2: just on the new building.
Speaker 1: Yeah, that's good.
Speaker 2: That's boring.
Speaker 1: That's boring.
Speaker 2: That can be a good idea.
Speaker 1: But do we?
Speaker 2: Can we?
Speaker 1: Can we?
Speaker 2: Can we?
Speaker 1: Because there is no.
Speaker 2: No.
Speaker 1: No.
Speaker 2: Because that made.
Speaker 1: We have one extra one-person office and two-three-person offices, yeah.
Speaker 2: Plus we have the two people who aren't there now.
Speaker 1: Yeah.
Speaker 2: to more. You can keep some of the people together that are together now, but not everyone
Speaker 1: definitely. Okay, so let's start then top to bottom, Maggie. Well, why don't we take a
Speaker 2: break and go off and think about it? Yeah. And then I think we want to have more concrete ideas.
Speaker 1: Yeah. Okay, we can come back and finish it because if we just sit here and discuss it's going to take
Speaker 2: a long time, we're going to start arguing and get cranky in. Okay. So let's have a break. Save
Speaker 1: your fight. Yeah. You have an XB? Yep. That's nice. Okay. So how long it's going?
Speaker 2: Uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh, uh-huh,
````

### IN1009

````text
Speaker 2: C'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon Ok, ok, j'ai l'impression que c'est une question de...
Speaker 1: Oui.
Speaker 2: Donc, vous avez parlé de toutes les questions?
Speaker 1: Oui.
Speaker 2: Ok.
Speaker 1: Et l'établissement de tous les gens nous sommes...
Speaker 2: Oui.
Speaker 1: Avec la gestion.
Speaker 2: Et...
Speaker 1: C'est-à-dire que tout le monde se fait par les gens.
Speaker 2: C'est bon.
Speaker 1: Alors les questions que je n'ai pas dit, je n'ai pas dit que je n'ai pas besoin de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion C'est le modèle de la personne.
Speaker 2: C'est le piche, non?
Speaker 1: Oui, piche à la place.
Speaker 2: Non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non, non non, non non, non non, non non, non non, non non, non non, non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non non Je pense que c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, C'est une fréquence, mais c'est une personne, et c'est parce que vous transformez de l'homme.
Speaker 1: Oui, vous nous avez compréhéééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééééé C'est une formation équiverant que ce n'est pas possible.
Speaker 2: Vous ne pouvez pas compliquer ce modeling.
Speaker 1: Mais ce n'est pas le plus important.
Speaker 2: Non, c'est-à-dire que ce n'est pas le plus important.
Speaker 1: C'est-à-dire que ce n'est pas le plus important.
Speaker 2: C'est pas le plus important, c'est-à-dire que ce n'est pas le plus important.
Speaker 1: C'est-à-dire que ce n'est pas le plus important.
Speaker 2: Et vous avez des piches et vous avez l'information
Speaker 1: avec un très dynamique.
Speaker 2: Oui, le point de piches est aussi possibilité.
Speaker 1: OK.
Speaker 2: En tout cas, j'ai eu le point de pique.
Speaker 1: Et c'est une personne.
Speaker 2: Et c'est une très grande personne.
Speaker 1: Dependez en émotion.
Speaker 2: C'est aussi intéressant pour vous de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l'attention de l Je vous laisse le décision de finir.
Speaker 1: Je vous laisse le décision, peut-être comme ça.
Speaker 2: Si le person ne se trouve,
Speaker 1: je pense que c'est peut-être le plus compliqué.
Speaker 2: C'est une personne qui va le faire dans le moment.
Speaker 1: C'est le plus différent.
Speaker 2: Vous ne need to build statistiques et modèles
Speaker 1: de le person identité sur ces majors.
Speaker 2: C'est quand même un humain de l'émanagement.
Speaker 1: Je ne sais pas si tu es un familier avec ça.
Speaker 2: C'est pas un PCM, c'est pas un texte, mais c'est un texte, mais c'est tout le monde complète.
Speaker 1: Oui.
Speaker 2: Je ne sais pas si tu veux que tu es un cancer.
Speaker 1: Donc, je ne sais pas si tu es un familier.
Speaker 2: Je ne sais pas si tu es un cancer.
Speaker 2: Ok, donc tu as pu s'accueillir. J'ai pu s'accueillir.
Speaker 1: J'ai pu s'accueillir.
Speaker 2: J'ai pu s'accueillir.
Speaker 1: J'ai pu s'accueillir.
Speaker 2: J'ai pu s'accueillir.
Speaker 1: J'ai pu s'accueillir.
Speaker 2: J'ai pu s'accueillir.
Speaker 1: J'ai pu s'accueillir.
Speaker 2: J'ai pu s'accueillir.
Speaker 1: J'ai pu s'accueillir.
Speaker 2: J'ai pu s'accueillir.
Speaker 1: J'ai pu s'accueillir.
Speaker 2: J'ai pu s'accueillir.
Speaker 1: J'ai pu s'accueillir.
Speaker 2: J'ai pu s'accueillir.
Speaker 1: J'ai pu s'accueillir.
Speaker 2: J'ai pu s'accueillir.
Speaker 1: J'ai pu s'accueillir.
Speaker 2: J'ai pu s'accueillir.
Speaker 1: J'ai pu s'accueillir.
Speaker 2: J'ai pu s'accueillir.
Speaker 1: J'ai pu s'accueillir.
Speaker 2: J'ai pu s'accueillir.
Speaker 1: J'ai pu s'accueillir.
Speaker 2: J'ai pu s'accueillir.
Speaker 1: J'ai pu s'accueillir.
Speaker 2: Alla, c'est ce qu'il y a, c'est des différentes mesures que nous devons évaluer de l'identité de la personne qui est.
Speaker 2: Donc, avec l'occasion, tout ce que vous pouvez faire est d'extractes, segments de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l comme ici, on doit être enough, parce que c'est pas la même chose.
Speaker 1: C'est-à-dire qu'il y a un peu de temps que ce soit une chose qui est très faible.
Speaker 2: Oui, mais nous sommes à la place où nous ne devons pas être plus faible.
Speaker 1: Donc, quand on est dans le moment de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de Patence, parce que, si tu sais que c'est au match de personne, j'espère qu'on n'a pas eu de 5-10 minutes.
Speaker 2: Je ne sais pas si l'on lui fait, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde, c'est tout le monde et vous pensez que un autre site de votre projecte est de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la fin de la from from the location no from the vis majeuse piche et c'est-à-dire
Speaker 1: c'est une belle, c'est-à-dire
Speaker 2: vous avez une spectre?
Speaker 1: oui, c'est-à-dire
Speaker 2: ok
Speaker 1: donc je vous souhaite pour l'occasion et le jour où vous pouvez
Speaker 2: le petit petit petit petit petit
Speaker 1: Et puis dans la nexte level, je pense que vous pouvez le grouper sur le site.
Speaker 2: Je pense que j'ai eu enough d'être en train de faire ce que je vais faire.
Speaker 1: Donc je vais faire une manière de faire des pratiques utilisables en tout cas.
Speaker 1: Quand est-ce que vous êtes en train de finir sur 5 ou 6 mètres? Approximately.
Speaker 2: Les russes sont toujours plus extensibles.
Speaker 1: Je ne sais pas.
Speaker 2: Je ne sais pas.
Speaker 1: Je vous sais que vous allez faire une séparation.
Speaker 1: Mais je ne sais pas, mais même que nous n'avons pas intéressé que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas que nous n'avons pas Oui, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c'est vrai, c' vrai, c'est vrai, c'est vrai, c' vrai, c' vrai, c'est vrai, c' vrai, c' vrai, c'est vrai, c' vrai, c' vrai, c' vrai, c'est vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' vrai, c' Je ne sais pas si vous avez besoin d'exemple dans le même temps.
Speaker 2: Je ne sais pas si j'ai eu des conditions de la situation.
Speaker 1: Non, je ne sais pas, je ne sais pas.
Speaker 2: Oui.
Speaker 1: Oui, je ne sais pas.
Speaker 2: Oui, je ne sais pas.
Speaker 1: Donc, c'est le type de thing que l'on a présenté dans les séparations.
Speaker 2: C'est tout le monde, c'est tout le monde.
Speaker 2: C'est très important que l'on fiche, c'est très important que l'on fiche. Oui, tout le monde m'a dit, si l'on a vu, c'est qu'il y a l'extracte des fiches de la piche et de la piche.
Speaker 1: Il y a un sujet simple, un peu plus de personnes, vous m'avez à faire de faire des séparations.
Speaker 2: Parce que l'on fiche, c'est tout le même temps.
Speaker 1: C'est plus important que l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'interdit de l'inter Oui, c'est aussi que tu as extraqué le contexte.
Speaker 2: Oui, parce qu'il y a des words que j'espère qu'on peut dire,
Speaker 1: c'est ce qu'on peut dire, c'est un greu, c'est un contexte.
Speaker 2: Oui, c'est un contexte.
Speaker 1: Oui, c'est un contexte, c'est un contexte.
Speaker 2: Ce n'est pas pas un projecteur.
Speaker 1: Non mais je pense que quand vous avez besoin de faire un personneur.
Speaker 2: Oui.
Speaker 1: Est-ce qu'il y a un personneur?
Speaker 2: C'est un petit peu un petit peu, c'est un petit peu, c'est un petit peu, c'est un petit peu, c'est un petit peu, c'est un petit peu, c'est un petit peu, c'est un petit peu, c'est un petit peu, c'est un petit peu, c'est un petit peu, c'est un petit peu, c'est un petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit petit Ok, donc je vous donne avec ce que vous avez aimé pour vous présenter les questions.
Speaker 1: Oui, j'espère que si vous n'avez pas besoin de 3 papers.
Speaker 2: Ah, sure.
Speaker 1: Non, je pense que c'est plutôt que de signer.
Speaker 2: Le link, c'est pas simple.
Speaker 1: 3 papers, c'est pas vrai.
Speaker 2: C'est ce qu'on a dit, c'est le secteur de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l'occasion de l' Quand tu es un système de travail dans différents conditions,
Speaker 1: la catheterie a l'alibrarie,
Speaker 2: le environnement va être très différent.
Speaker 1: A single fixe vers le value, ça va être un problème.
Speaker 2: Oui, c'est une fois que nous nous sommes using un type de calibration.
Speaker 1: Oui, c'est toujours.
Speaker 2: Donc, vous pouvez faire d'automatique.
Speaker 1: Ce n'est pas une chose.
Speaker 2: Oui.
Speaker 1: Je ne sais pas si j'ai rien à faire, mais...
Speaker 2: Oui, mais en fait, vous avez à voir en front de la microphone,
Speaker 1: et vous pouvez dire que les gens qui se puissent, et les gens qui se puissent.
Speaker 2: Ok, c'est juste subtracter le level que vous capte dans les microphones.
Speaker 1: Donc, vous avez un autre type,
Speaker 2: que vous avez été très très intéressant pour la farce-ingre-channel-carrie de version.
Speaker 1: Et je vous ai un code online.
Speaker 2: Ok, donc...
Speaker 1: pour cette partie de l'art.
Speaker 2: La première chose, je vous sais,
Speaker 1: le clustering
Speaker 2: de la clustering de différentes locations à perte.
Speaker 1: que vous pouvez le faire plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus et si je suis très heureux, je suis juste très heureux pour tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout le monde, tout C'est vrai que vous avez besoin de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de la process de C'est vrai que c'est un très important, mais c'est un très important.
Speaker 2: Pour la firste application, nous allons nous faire avec nos prototypes.
Speaker 1: Je ne vais pas faire plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus de plus Donc, j'ai l'impression d'être un peu plus long, mais vous pouvez juste brieffler l'eau.
Speaker 2: OK.
Speaker 1: On peut se servir en plus.
Speaker 2: Vous pouvez le faire, mais c'est une fin de fin.
Speaker 1: Non.
Speaker 2: C'est ce que vous avez.
Speaker 1: Il y a.
Speaker 2: J'ai l'impression d'avoir plein de temps.
Speaker 1: J'ai l'impression d'avoir plein de temps.
Speaker 2: J'ai l'impression d'avoir plein de temps.
Speaker 1: J'ai l'impression d'avoir plein de temps.
Speaker 2: Oui, c'est qu'on peut dire, mais...
Speaker 1: Non, c'est pas vrai que j'étais en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d'être en train d C'est l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l'âge de l On ne va pas le faire ça.
Speaker 2: Ok, on va le faire.
Speaker 1: Et on va le faire.
Speaker 2: Ma chiepe est très très bien.
Speaker 1: Et on va le faire ici.
Speaker 2: C'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine, c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mécanine c'est une mé Je suis décevoir, c'est un qui est rendu à l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l'intérieur de l C'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon, c'est bon
````

## Recommendations

1. **Replace two-label alternation with persistent diarization.** Use a real diarization model or correctly parse Whisper turn markers, retain timestamps in stored segments, and support more than two speakers. Do not publish participant-specific insights until speaker assignments are checked.
2. **Use a stronger and language-aware ASR path.** Whisper Tiny missed words badly and catastrophically misdetected language on IN1009. Route using known language where available, add language-confidence checks, and reject/review suspicious outputs such as extreme repetition or transcript/reference-length anomalies. Benchmark larger Whisper models/faster-whisper or an explicitly configured Whisper.cpp model on this same corpus.
3. **Make the executed ASR match configuration and documentation.** The active Python code uses HF Whisper Tiny, while README/model docs describe Whisper.cpp `small.en-tdrz`. Choose one actual path, align the config/docs, and package ffmpeg in the runtime rather than relying on an environment alias.
4. **Improve MoM extraction and evidence grounding.** Require each decision/action to cite a supporting transcript span; distinguish proposal, discussion, decision, and completed work. Keep due dates unspecified unless spoken. Never infer due dates such as `2022-01-01` or attach owners from alternating chunk IDs.
5. **Validate generated JSON and output length.** Use constrained schema output or bounded repair/retry. Check required types and empty/placeholder content, detect truncation before accepting a MoM, and avoid treating agenda topics as decisions. The 700-token limit truncated one of five long outputs.
6. **Add an evaluation suite with diverse conditions.** This AMI subset gives references and topics but only one close-talk headset-mix condition. Add consented phone/room recordings, noise, compression, overlap, accents/languages, shorter and longer durations, and reference transcripts/MoMs. Keep held-out meetings for evaluation. Report macro and micro WER, DER with a documented scorer, field-level extraction precision/recall, schema success, unsupported-claim rate, latency, and model revisions.
7. **Add a human verification gate.** Surface ASR confidence/repetition warnings, let organizers correct transcripts/speakers, and mark low-confidence dates/owners as unassigned pending review.

## Limitations and attribution

This is a five-meeting sample, not an exhaustive benchmark. The ASR runtime needed a temporary local ffmpeg alias; the active Python path was not changed. Qwen generation used an Ollama Q4_K_M quantization of the same 1.5B model family because the configured full-precision local path was not suitable for the available RAM. Four meetings have no AMI gold abstractive MoM; their MoM scores are reviewer-rated against the human transcript. All five corpus files use the same Mix-Headset condition, so noisy/far-field robustness remains unmeasured. AMI data is CC BY 4.0; cite Jean Carletta et al., “The AMI Meeting Corpus: A Pre-announcement,” MLMI 2005, and retain corpus attribution when redistributing excerpts.

