# SmartMOM Bot — Free AI Model Survey and Selection

**Project:** SmartMOM Bot  
**Research date:** 28 August 2026
**Scope:** Models that can support the project's audio preparation, transcription, speaker processing, meeting-minutes extraction, sentiment analysis, and engagement indication.

## 1. Meaning of “all available models”

Hugging Face contains millions of model repositories, including duplicates, fine-tunes, conversions, and models with missing or incompatible licenses. A literal list would become obsolete immediately and would not be useful engineering evidence. This document instead covers every relevant **model family and deployment route** found across Hugging Face, official model repositories, and major hosted providers, then compares representative models that are credible for this application.

“Free” is separated into:

- **Free local/open-weight:** no per-request fee after download; electricity and hardware are still required.
- **Free hosted tier:** limited quota that may change; an account, internet, and data transfer are required.
- **Paid API:** included as a baseline, not selected as the default.

## 2. Implemented selection

| Concern | Selected implementation | License/access | Download/runtime | Why selected |
| --- | --- | --- | --- | --- |
| Audio normalization | FFmpeg | LGPL/GPL build-dependent; free local tool | Bundled npm binary | Mature codec support; deterministic preprocessing, not an AI model |
| Speech recognition | Whisper `small.en-tdrz` GGML via `whisper.cpp` | Free local weights; `whisper.cpp` MIT | About 465 MB; CPU | Existing model fits the 8 GB laptop and combines English ASR with speaker-change markers |
| Speaker processing | Whisper tinydiarize markers | Free local | Same model/inference pass | No second heavy Python service; adequate for an FYP two-speaker demo |
| Minutes, agenda, decisions, actions | `onnx-community/Qwen2.5-1.5B-Instruct`, q4 | Base model Apache-2.0; ungated | About 1.79 GB q4 ONNX; CPU | Better extraction than 0.5B while retaining 32K context, ungated download, and an 8 GB CPU fit |
| Per-speaker sentiment | `Xenova/distilbert-base-uncased-finetuned-sst-2-english`, q4 | Based on Apache-2.0 DistilBERT/SST-2 ecosystem; ungated | Lightweight quantized ONNX; CPU | Dedicated classifier is faster and more repeatable than asking the generative model |
| Engagement indicator | Share of spoken words | Deterministic local calculation | No model | Transparent and auditable; avoids presenting invented LLM percentages as measurements |

The default path is now completely local and requires no API key. The first minutes/sentiment request downloads model files into `models/huggingface`; subsequent requests work from the cache. OpenAI remains an explicitly configurable optional provider.

## 3. Separation of concerns

| Module | Single responsibility |
| --- | --- |
| `server/ai.js` | Stable orchestration facade used by HTTP routes |
| `server/ai/transcription-service.js` | Select local or OpenAI transcription provider |
| `server/local-transcription.js` | FFmpeg conversion, whisper.cpp execution, and turn-marker parsing |
| `server/ai/minutes-service.js` | Local Qwen or optional OpenAI structured minutes generation and output normalization |
| `server/ai/sentiment-service.js` | Dedicated per-speaker sentiment classification and engagement calculation |
| `server/ai/model-runtime.js` | Shared Hugging Face pipeline lifecycle and model cache |

This boundary lets a future diarization or summarization model be replaced without changing Express routes, React, authentication, storage, feedback, or PDF export.

## 4. Automatic speech recognition comparison

| Model/family | Params | Languages | Free local | Typical fit | Decision |
| --- | ---: | --- | --- | --- | --- |
| Whisper `tiny(.en)` | 39M | English or multilingual | Yes, MIT code/model | Very weak CPUs, fastest but least accurate | Alternative |
| Whisper `base(.en)` | 74M | English or multilingual | Yes | Good low-resource baseline | Alternative |
| **Whisper `small.en-tdrz`** | ~244M | English | **Yes** | English meetings plus experimental turn markers | **Selected** |
| Whisper `small` | 244M | Multilingual | Yes | Multilingual upgrade at similar size, without integrated tdrz | Recommended if Urdu/multilingual audio is required |
| Whisper `medium(.en)` | 769M | English or multilingual | Yes | Better accuracy, substantially slower on this CPU | Not selected for current hardware |
| Whisper `large-v3` | 1.55B | Multilingual | Yes | High-accuracy GPU/server deployments | Too heavy here |
| Whisper `large-v3-turbo` | 809M | 99 languages | Yes, MIT | Faster large-family multilingual inference | Strong future GPU option |
| Distil-Whisper `distil-large-v3` | ~756M | English | Yes, MIT | Faster English long-form ASR | No diarization; heavier than selected model |
| `faster-whisper` + Whisper checkpoint | Model-dependent | Model-dependent | Yes | CTranslate2 acceleration and batching | Excellent Python/GPU service option |
| WhisperX | Model-dependent | Multilingual | Yes | ASR plus word alignment and pyannote assignment | Strong but much heavier deployment |
| wav2vec2 / HuBERT fine-tunes | Usually 95M–1B | Checkpoint-specific | Usually | Domain/language-specific ASR | Requires careful checkpoint/dataset evaluation |
| NVIDIA NeMo ASR families | Varies | Model-specific | Many weights free | GPU production pipelines | Poor fit for this CPU-only laptop |
| Vosk/Kaldi models | Small to large | Many downloadable language packs | Yes, Apache-2.0 toolkit | Offline low-resource command recognition | Generally behind Whisper for conversational robustness |

Whisper's official model card lists the size ladder and describes English-only and multilingual variants. `large-v3-turbo` supports 99 languages under MIT: [Whisper large-v3-turbo model card](https://huggingface.co/openai/whisper-large-v3-turbo). The local engine is [whisper.cpp](https://github.com/ggml-org/whisper.cpp).

## 5. Speaker diarization and turn detection comparison

| Model/pipeline | True persistent speakers | Overlap handling | Access | Hardware/deployment | Decision |
| --- | --- | --- | --- | --- | --- |
| **Whisper tinydiarize** | No; change points with alternating labels | Weak | Ungated local | Lightest; same ASR pass | **Selected for current two-speaker workflow** |
| pyannote `speaker-diarization-community-1` | Yes | Yes | Free CC-BY-4.0, but gated acceptance and HF token | Python/PyTorch; heavier CPU/RAM | Best future accuracy upgrade |
| WhisperX + pyannote | Yes, assigned to aligned words | Yes | Free, pyannote gate applies | Multiple models; GPU preferred | Best full research pipeline |
| NVIDIA NeMo diarization | Yes | Pipeline-dependent | Free/open components | Complex Python/GPU stack | Production research alternative |
| SpeechBrain diarization/embeddings | Yes, pipeline assembly required | Varies | Apache-2.0 toolkit; model licenses vary | Python/PyTorch | Flexible research alternative |
| simple energy/VAD segmentation | No | No | Free | Very light | Not diarization; inadequate alone |

The selected tinydiarize path must be described honestly as **speaker-turn segmentation**, not voice identity. For three or more speakers, overlapping speech, or identity consistency, use [pyannote Community-1](https://huggingface.co/pyannote/speaker-diarization-community-1), which supports offline use after accepting its access conditions.

## 6. Minutes generation and structured extraction comparison

General summarizers can produce prose, but SmartMOM also needs agenda, decisions, owners, tasks, and due dates in valid JSON. Instruction-tuned causal models are therefore a better single-stage fit than news summarizers.

| Model | Params/context | License/access | Approximate local class | Strengths | Decision |
| --- | --- | --- | --- | --- | --- |
| Qwen2.5-0.5B-Instruct q4 ONNX | 0.49B / 32K | Apache-2.0, ungated | <1 GB weights | Runs here, but validation found an action-owner attribution error | Rejected after local quality check |
| **Qwen2.5-1.5B-Instruct q4 ONNX** | 1.54B / 32K | Apache-2.0, ungated | ~1.79 GB Q4 | Better extraction quality while retaining Transformers.js deployment | **Selected for 8 GB CPU laptop** |
| Qwen2.5-3B/7B-Instruct | 3B/7B / 32K+ | Qwen/Apache terms by size/version | ~2–5 GB Q4 | Stronger reasoning and JSON | 7B is impractical on this machine alongside the app |
| SmolLM2-1.7B-Instruct | 1.7B / 8K | Apache-2.0 | ~1–2 GB quantized | Compact, fully open, good general instruction baseline | Alternative |
| Llama 3.2 1B/3B Instruct | 1.23B/3.21B / 128K | Custom Llama 3.2 license; gated | ~1–3 GB quantized | Multilingual summarization | Not selected due gate/custom obligations |
| Gemma 3 1B IT | 1B / 32K | Gemma terms; gated on HF | ~1–2 GB | 140+ language family, summarization | Not selected due gate/custom terms |
| Phi-3.5 Mini Instruct | 3.8B / 128K | MIT, ungated | ~2–4 GB quantized | Long-document and meeting summarization capability | Stronger but too slow/heavy for default |
| Mistral 7B Instruct | 7B / version-specific | Apache-2.0 for common releases | ~4–5 GB Q4 | Strong instruction quality | Memory/latency poor on 8 GB total RAM |
| TinyLlama 1.1B Chat | 1.1B / 2K | Apache-2.0 | ~0.7 GB Q4 | Very small | Short context and weaker extraction |
| FLAN-T5 small/base | 80M/250M | Apache-2.0 | Small | Efficient instruction seq2seq | Output schema reliability and context limits weaker |
| T5-small | 60.5M | Apache-2.0 | ~242 MB FP32 | Very light text-to-text baseline | Base checkpoint is not sufficient for reliable minutes extraction |
| DistilBART CNN | ~306M | Apache-2.0 | ~1.2 GB FP32 | Mature English abstractive summarization | News-domain prose only; not structured action extraction |
| BART-large-CNN / PEGASUS | ~400M–568M | Model-specific open licenses | ~1.5–2.3 GB FP32 | Good conventional summarization | Limited input and no dependable JSON/actions |

Primary model cards: [Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct), [Transformers.js ONNX conversion](https://huggingface.co/onnx-community/Qwen2.5-0.5B-Instruct), [Llama 3.2 1B Instruct](https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct), [Gemma 3 1B IT](https://huggingface.co/google/gemma-3-1b-it), [Phi-3.5 Mini Instruct](https://huggingface.co/microsoft/Phi-3.5-mini-instruct), [T5-small](https://huggingface.co/google-t5/t5-small), and [DistilBART CNN](https://huggingface.co/sshleifer/distilbart-cnn-12-6).

## 7. Sentiment model comparison

| Model/approach | Languages/domain | License | Size class | Limitation | Decision |
| --- | --- | --- | --- | --- | --- |
| **DistilBERT SST-2 q4** | English movie-review sentiment | Apache-2.0 model family | Small ONNX | Binary only; domain differs from meetings | **Selected lightweight baseline** |
| CardiffNLP Twitter-RoBERTa latest | English social media; negative/neutral/positive | CC-BY-4.0 | ~501 MB FP32 | Social-media domain, bigger | Better three-class English alternative |
| Multilingual DistilBERT sentiment student | 12 languages; 3 classes | Apache-2.0 | ~541 MB FP32 | Urdu is not listed; training-domain limitations | Multilingual alternative |
| RoBERTa-large sentiment fine-tunes | Usually English/domain-specific | Varies | Large | Too slow/heavy; license must be checked per fine-tune | Not selected |
| zero-shot NLI (BART/MDeBERTa) | Flexible labels/languages | Varies | Medium/large | Slower and less calibrated | Research alternative |
| generative Qwen sentiment | Same context as minutes | Apache-2.0 | Reuses LLM | Less repeatable and entangles concerns | Rejected to preserve separation |
| VADER/TextBlob | English lexicon/rules | Open source | Tiny | Weak negation/context/domain behavior | Deterministic fallback only |

The chosen classifier is exposed behind its own provider module, so moving to the three-class [CardiffNLP model](https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest) or the [multilingual DistilBERT student](https://huggingface.co/lxyuan/distilbert-base-multilingual-cased-sentiments-student) does not affect minutes generation.

Sentiment is an approximate language-model classification and must not be used for employment evaluation. Neutral business speech can be misclassified by a binary SST-2 model, so the UI must retain human review.

## 8. Hosted free tiers and paid baselines

Provider quotas, eligible models, retention, and pricing change frequently. A hosted “free” tier is not equivalent to a permanently free model.

| Route | Relevant services | Benefits | Risks/constraints | Default? |
| --- | --- | --- | --- | --- |
| Hugging Face Inference Providers/free credits | Serverless models routed by HF | No local hardware | Account/token, quotas, provider availability, data leaves machine | No |
| Google AI Studio Gemini free tier | Gemini Flash-family eligibility varies | Strong long-context extraction | Quotas/terms/regions may change; cloud data path | No |
| Groq developer tier | Supported open-weight LLMs and Whisper variants | Very fast inference | Rate limits and model catalog change | No |
| OpenRouter free model routes | Rotating `:free` models | Many model choices | Availability/privacy/limits vary by upstream provider | No |
| OpenAI API | GPT and transcription models | Strong managed quality | Usage-based, API key, external processing | Optional baseline |
| Local Hugging Face/ONNX + whisper.cpp | Implemented selections | Private, offline after download, no quota | First download, CPU latency, local storage | **Yes** |

Before using any hosted free tier in production, re-check its current official pricing, privacy, retention, rate-limit, and acceptable-use pages. This project intentionally avoids depending on such a tier.

## 9. Hardware-based decision

The development computer reports approximately **8 GB system RAM** and no usable discrete GPU. The app, Node runtime, embedded/PostgreSQL database, browser, Whisper, and text model must coexist. A 7B Q4 model alone can consume most available memory after runtime overhead. Qwen2.5-0.5B was tested and rejected after it misassigned an action owner; Qwen2.5-1.5B q4 is the selected quality/resource compromise.

## 10. Operational behavior

1. FFmpeg converts uploads to mono 16 kHz PCM.
2. Whisper `small.en-tdrz` transcribes locally and emits speaker-change markers.
3. The minutes and sentiment services run independently in parallel.
4. Qwen produces structured minutes; the service validates and normalizes its JSON boundary and reconciles explicit “Name will do task” ownership evidence from the source transcript.
5. DistilBERT classifies concatenated speech per speaker.
6. Engagement is the speaker's percentage of transcript words, not an invented confidence score.
7. Organizers review transcript labels and generated minutes before saving/exporting.

Model files are cached under ignored directories and are not committed to Git. Docker uses a named `model_cache` volume, so downloaded Hugging Face weights survive container restarts.

The runtime dependency tree is checked with `npm audit`. Because model runtimes parse large external weight files, only the fixed model identifiers in configuration should be used in production; do not accept arbitrary model names from HTTP requests.

## 11. Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `TRANSCRIPTION_PROVIDER` | `local` | `local` or optional `openai` |
| `MINUTES_PROVIDER` | `local` | `local` Qwen or optional `openai` |
| `WHISPER_MODEL_PATH` | `models/ggml-small.en-tdrz.bin` | Local ASR/turn model |
| `HF_MODEL_CACHE` | `models/huggingface` | Local ONNX model cache |
| `LOCAL_MINUTES_MODEL` | `onnx-community/Qwen2.5-1.5B-Instruct` | Structured local generator |
| `LOCAL_SENTIMENT_MODEL` | `Xenova/distilbert-base-uncased-finetuned-sst-2-english` | Dedicated classifier |
| `LOCAL_MODEL_DTYPE` | `q4` | Quantized inference type |
| `LOCAL_MINUTES_MAX_TOKENS` | `700` | Output ceiling |

## 12. Final recommendation

Keep the implemented local stack for the FYP because it is free of per-request charges, demonstrably executable on the available hardware, private after download, and cleanly separated by concern. If accuracy testing identifies a weakness, upgrade one boundary at a time:

1. Replace tinydiarize with pyannote Community-1 for true multi-speaker diarization.
2. Move beyond Qwen2.5-1.5B only after measuring memory and latency on deployment hardware.
3. Replace binary SST-2 with a three-class, meeting-domain fine-tune after collecting consented labeled evaluation data.
4. Replace `small.en-tdrz` with multilingual Whisper small/turbo if Urdu or mixed-language meetings become a requirement.

No model output should bypass organizer review. Decisions, owners, deadlines, sentiment, and speaker identity are all error-prone AI-derived data.

## 13. Primary references

- [Hugging Face Transformers.js pipeline API](https://huggingface.co/docs/transformers.js/en/pipelines)
- [Hugging Face server-side Node.js inference guide](https://huggingface.co/docs/transformers.js/main/en/tutorials/node)
- [whisper.cpp official repository](https://github.com/ggml-org/whisper.cpp)
- [Whisper large-v3-turbo model card](https://huggingface.co/openai/whisper-large-v3-turbo)
- [pyannote Community-1 model card](https://huggingface.co/pyannote/speaker-diarization-community-1)
- [WhisperX official repository](https://github.com/m-bain/whisperX)
- [Qwen2.5-0.5B-Instruct model card](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct)
- [Qwen2.5-1.5B-Instruct GGUF repository](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF)
- [Llama 3.2 1B Instruct model card](https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct)
- [Gemma 3 1B IT model card](https://huggingface.co/google/gemma-3-1b-it)
- [Phi-3.5 Mini Instruct model card](https://huggingface.co/microsoft/Phi-3.5-mini-instruct)
- [CardiffNLP sentiment model card](https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest)
- [Multilingual DistilBERT sentiment model card](https://huggingface.co/lxyuan/distilbert-base-multilingual-cased-sentiments-student)
