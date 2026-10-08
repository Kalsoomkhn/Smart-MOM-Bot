# Colab STT and diarization benchmark

This experiment compares `openai/whisper-base` and
`openai/whisper-large-v3-turbo` for speech-to-text, then evaluates
`nvidia/diar_sortformer_4spk-v1` for speaker diarization.

## Protocol

- Dataset: the same five AMI Mix-Headset recordings used in the baseline report.
- STT scope: complete recordings, forced English transcription.
- STT metrics: normalized WER, runtime, real-time factor, hypothesis/reference
  word counts, and peak allocated GPU memory.
- Diarization scope: the first five minutes of every recording.
- Diarization metrics: DER with a 0.25-second collar and overlap included,
  runtime, real-time factor, and peak allocated GPU memory.
- Failures are retained as rows instead of silently dropping meetings.

The five-minute Sortformer scope is deliberate. NVIDIA documents a maximum of
four speakers and reports an approximately 12-minute maximum even on an A6000
48 GB GPU. Full 18–37 minute meetings are therefore not a fair default for a
typical Colab T4/L4 runtime. Production use would require windowing plus speaker
identity stitching, which is a separate experiment.

## Run in Colab

1. Open `SmartMOM_STT_Diarization_Colab.ipynb` in Google Colab.
2. Select **Runtime → Change runtime type → GPU**.
3. Set `REPO_URL` in the setup cell to the Git URL containing this branch.
4. Run all cells. A Hugging Face token may be requested for Sortformer.
5. Download `smartmom-results.zip` and place the extracted files under
   `experiments/results/colab/<run-date>/`.

The notebook installs dependencies in two stages and restarts the runtime after
NeMo installation when Colab requires it. If Turbo runs out of memory, reduce
the pipeline batch size from 8 to 4; do not change it for only one meeting.

## Outputs

- `results.csv` and `results.json`: one row per model and meeting.
- `environment.json`: GPU, CUDA, PyTorch, Python, and platform details.
- `transcripts/`: raw Whisper hypotheses.
- `rttm/`: Sortformer speaker segments.
- `clips/`: exact diarization excerpts used for scoring.

Do not add benchmark claims to the evaluation report until `results.json` and
`environment.json` have been retained. Model downloads and AMI audio remain
untracked.
