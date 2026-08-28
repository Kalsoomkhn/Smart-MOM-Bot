# SmartMOM Bot — AI Model Comparison

**Project:** SmartMOM Bot  
**Document purpose:** Compare the models used or considered at each AI-processing stage and justify the current selections.  
**Last updated:** 26 August 2026

## 1. Executive summary

SmartMOM uses two main AI-processing stages. Audio transcription and speaker-turn segmentation run locally with the free `ggml-small.en-tdrz` Whisper model through `whisper.cpp`. Meeting analysis uses `gpt-5-mini` when an OpenAI API key is configured. Without an OpenAI key, the analysis stage returns deterministic demonstration data; this fallback is application logic and not a machine-learning model.

| Stage | Current selection | Runs where | API key | Direct usage cost |
| --- | --- | --- | --- | --- |
| Audio preparation | FFmpeg conversion | Local machine/server | No | Free |
| Speech transcription | Whisper `small.en-tdrz` in GGML format | Local machine/server | No | Free |
| Speaker processing | Tinydiarize speaker-turn detection from the same model | Local machine/server | No | Free |
| Agenda and discussion extraction | `gpt-5-mini` | OpenAI API | Yes | Usage-based |
| Decision and action-item extraction | `gpt-5-mini` | OpenAI API | Yes | Usage-based |
| Sentiment and engagement analysis | `gpt-5-mini` | OpenAI API | Yes | Usage-based |
| Analysis fallback | Deterministic JavaScript demo rules | Local server | No | Free |

## 2. Stage 1 — Audio preparation

The uploaded MP3, WAV, M4A, MP4, OGG, or WebM file is converted by FFmpeg into 16 kHz, mono, 16-bit PCM WAV. This is signal preprocessing rather than an AI model. It ensures that the local Whisper executable receives a consistent input format.

| Option | Advantages | Limitations | Decision |
| --- | --- | --- | --- |
| FFmpeg | Free, mature, supports many audio formats, reliable conversion | Adds a binary dependency | **Selected** |
| Browser-only conversion | Processing stays in the browser | Inconsistent codec support and greater frontend complexity | Not selected |
| Cloud media-conversion service | Scalable and managed | Network, privacy, account, and cost requirements | Not selected |

## 3. Stage 2 — Speech transcription

### Current model: Whisper `small.en-tdrz`

The project uses `ggml-small.en-tdrz.bin` with `whisper.cpp`. The model runs on the project machine, so meeting audio is not sent to an external transcription API. The model is English-specific and includes support for experimental speaker-turn detection.

| Candidate | Deployment | Relative resource requirement | Accuracy expectation | Main advantage | Main limitation | Suitability for SmartMOM |
| --- | --- | --- | --- | --- | --- | --- |
| Whisper `tiny.en` | Local | Very low | Lowest among listed Whisper sizes | Fast on weak CPUs | More transcription errors | Useful only for very weak hardware |
| Whisper `base.en` | Local | Low | Better than tiny | Good speed/size balance | No integrated tinydiarize model in this implementation | Possible transcription-only alternative |
| **Whisper `small.en-tdrz`** | **Local** | **Moderate** | **Good for clear English meetings** | **Free transcription and turn detection in one model** | English-only; turn detection is experimental | **Selected for the FYP** |
| Whisper `medium.en` | Local | High | Usually stronger than small on difficult audio | Better recognition potential | Slower and requires much more memory/disk | Better for powerful machines, but lacks the selected integrated workflow |
| Whisper `large-v3`/Turbo | Local | Very high | Strong multilingual recognition | Better language coverage and robustness | Heavy CPU/GPU and storage requirements | Not ideal for an ordinary FYP laptop |
| `faster-whisper` | Local Python service | Depends on model | Same Whisper family with optimized inference | Fast batched/GPU inference | Requires Python and a more complex service | Strong future upgrade |
| OpenAI `gpt-4o-transcribe-diarize` | Cloud API | Minimal local hardware | Managed transcription and diarization | Simple API and stronger managed workflow | Paid API key, network, and external audio processing | Original implementation; removed as the default |

### Selection rationale

`small.en-tdrz` was selected because it provides the best practical compromise for the current project: no paid API, manageable model size, CPU operation, adequate English transcription, and speaker-turn detection through one local executable. The application source also includes a repeatable Windows setup script and a Docker build configuration.

## 4. Stage 3 — Speaker diarization

Speaker diarization answers “who spoke when.” The current implementation more precisely performs **speaker-turn segmentation**: tinydiarize marks places where the speaker appears to change, and SmartMOM assigns alternating labels (`Speaker 1`, `Speaker 2`). It does not compute persistent voice identities and should not be treated as robust multi-speaker identity clustering.

| Candidate | What it provides | Cost/access | Strengths | Limitations | Decision |
| --- | --- | --- | --- | --- | --- |
| **Whisper tinydiarize** | Speaker-change markers integrated with transcription | Free, local, no account | Lightweight and easy to deploy with `whisper.cpp` | Experimental; best suited to two-person alternating speech; weak for overlap and three or more speakers | **Selected for the current FYP** |
| `pyannote.audio community-1` | Speaker segmentation, clustering, speaker embeddings, and optional speaker-count constraints | Open-source/local after model access and download | Proper multi-speaker diarization and overlap-aware output | Python/PyTorch stack, heavier setup, typically requires accepting model terms and a Hugging Face token for download | Recommended future accuracy upgrade |
| WhisperX + pyannote | Whisper transcription, word alignment, and pyannote speaker assignment | Open-source/local after dependencies/model access | Word-level timing and stronger multi-speaker pipeline | More RAM/VRAM, Python, FFmpeg, alignment models, and configuration | Best future option for GPU-capable deployment |
| OpenAI diarized transcription | Managed transcript with speaker labels | Paid API | Minimal local setup | API key, usage cost, internet dependency, and external processing | Not selected because the project requires a free local path |

### Selection rationale

Tinydiarize satisfies the project’s immediate constraint—free local processing on the current Windows machine—without adding Python, PyTorch, GPU drivers, or a second large model. For a production system or meetings with more than two speakers, `pyannote.audio community-1` or WhisperX would be the more technically appropriate choice.

## 5. Stage 4 — Meeting-minutes generation

After transcription, SmartMOM sends the reviewed transcript to one structured analysis request. The model returns JSON containing the agenda, decisions, discussion points, action items, owners, due dates, overall sentiment, and participant engagement.

### Current model: `gpt-5-mini`

| Candidate | Deployment | Structured extraction | Cost | Strengths | Limitations | Suitability |
| --- | --- | --- | --- | --- | --- | --- |
| **`gpt-5-mini`** | OpenAI API | Strong when prompted for JSON | Usage-based | Good instruction following and combines several analysis tasks in one call | Requires API key and internet; output still needs human review | **Selected when an API key is available** |
| Larger frontier API model | Cloud API | Potentially stronger | Higher | Better reasoning on ambiguous meetings | Greater cost and latency than needed for routine extraction | Unnecessary for the current FYP |
| Smaller cloud model | Cloud API | Moderate | Lower | Fast and inexpensive | Higher risk of omissions or malformed extraction | Possible cost-focused alternative |
| Local Qwen/Llama-class instruct model through Ollama | Local | Depends on model and prompt | No per-request fee | Private and API-key-free after download | Requires several GB of storage/RAM; weaker hardware may be slow; JSON reliability varies | Recommended future fully offline option |
| Rule-based extraction | Local | Low | Free | Predictable and fast | Cannot reliably understand varied natural-language meetings | Suitable only as a demo fallback |

### Selection rationale

`gpt-5-mini` is retained because the user requested that the already-working analysis functionality remain unchanged. It performs agenda extraction, summarization, decisions, action items, sentiment, and engagement in one call, reducing backend complexity. A local Ollama model would be required if the whole analysis pipeline must later become independent of paid APIs.

## 6. Stage 5 — Sentiment and participant engagement

SmartMOM does not currently use a separate sentiment-classification model. `gpt-5-mini` produces the sentiment and engagement fields in the same structured response used for meeting minutes.

| Approach | Advantages | Limitations | Decision |
| --- | --- | --- | --- |
| **Use `gpt-5-mini` with transcript context** | One request; considers surrounding discussion; simple architecture | Scores are model estimates, not scientifically calibrated measurements | **Current implementation** |
| Dedicated transformer sentiment classifier | Repeatable labels and local inference | Many classifiers are trained on reviews/social media rather than meeting dialogue; speaker attribution must already be accurate | Possible research extension |
| Lexicon/rule-based sentiment | Free, transparent, and fast | Poor handling of context, negation, technical language, and neutral business discussion | Not selected |

Engagement percentages must be presented as qualitative AI-generated indicators, not objective measurements. They should not be used for employee evaluation or other high-impact decisions.

## 7. Final comparison and recommendation

| Requirement | Local Whisper + tinydiarize | WhisperX + pyannote | OpenAI-only pipeline |
| --- | --- | --- | --- |
| No paid transcription key | Yes | Yes | No |
| Works without sending audio to a cloud API | Yes | Yes | No |
| Simple Windows deployment | Best of the three | More difficult | Simple only after API setup |
| Ordinary CPU suitability | Good with the small model | Slower/heavier | Excellent because work is remote |
| Two-speaker turn separation | Basic/experimental | Stronger | Managed |
| Multi-speaker identity consistency | Weak | Stronger | Managed |
| Word-level alignment | No | Yes | Provider-dependent |
| Current project fit | **Best practical FYP choice** | Best future technical upgrade | Conflicts with the no-paid-key requirement |

### Current recommendation

Keep `small.en-tdrz` with `whisper.cpp` for the submitted FYP because it creates a real, free, locally executable transcription workflow on the available machine. Require organizer review of transcript text and speaker labels before analysis and export. If evaluation later requires accurate three-or-more-speaker diarization, upgrade only the diarization/transcription service to WhisperX plus `pyannote.audio community-1`; the React interface, Express routes, database schema, minutes analysis, feedback, and PDF export can remain unchanged.

## 8. Model locations in the codebase

| Configuration or implementation | Location |
| --- | --- |
| Transcription-provider selection | `server/ai.js` |
| Local Whisper execution and speaker-label parsing | `server/local-transcription.js` |
| Local-model Windows installer | `scripts/setup-local-whisper.ps1` |
| Docker model build and checksum validation | `Dockerfile.api` |
| Model paths and language settings | `.env.example` and `docker-compose.yml` |
| Analysis model selection | `OPENAI_SUMMARY_MODEL` in `.env`; consumed by `server/ai.js` |

## 9. References

1. ggml-org, **whisper.cpp**, including the documented experimental tinydiarize workflow: <https://github.com/ggml-org/whisper.cpp/blob/master/README.md>
2. OpenAI, **API model documentation**: <https://platform.openai.com/docs/models>
3. Bain et al., **WhisperX: Time-Accurate Speech Transcription of Long-Form Audio** and implementation: <https://github.com/m-bain/whisperX>
4. pyannote, **pyannote.audio speaker-diarization toolkit**: <https://github.com/pyannote/pyannote-audio>

