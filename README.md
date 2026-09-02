# SmartMOM Bot

SmartMOM Bot is a professional meeting-intelligence workspace that turns consented meeting recordings into reviewable minutes, decisions, action items, participant insights, and PDF exports.

## Highlights

- Secure Organizer and Participant roles with JWT authentication
- Upload or record meeting audio directly in the workspace
- Free local Whisper transcription with speaker-turn segmentation
- Free local structured minutes generation with quantized Qwen2.5
- Dedicated local DistilBERT sentiment analysis and transparent speaking-share engagement
- Editable agenda, decisions, discussion notes, and action items
- Meeting participant access control and feedback capture
- PDF export for finalized meeting minutes
- Responsive React interface with a production Nginx reverse proxy

## Architecture

| Service | Responsibility |
| --- | --- |
| `web` | React production build served through Nginx |
| `api` | Python/FastAPI API, authentication, file handling, AI processing, PDF generation |
| `database` | PostgreSQL 16 persistent application database |
| `nginx` | Included inside the `web` container; serves the SPA and proxies `/api` |

## Quick start with Docker

1. Copy `.env.example` to `.env`.
2. Set strong values for `POSTGRES_PASSWORD` and `JWT_SECRET`.
3. `OPENAI_API_KEY` is optional; the default AI workflow does not need it.
4. Start the application (the API image packages Whisper; Qwen and DistilBERT download into a persistent model volume on first analysis):

```bash
docker compose up --build -d
```

Open `http://localhost:8080`.

To stop the stack while retaining database and uploaded-audio volumes:

```bash
docker compose down
```

## Demo and testing

The application seeds demo users and demo meeting records automatically when the API starts.

| Role | Email | Password |
| --- | --- | --- |
| Organizer | `admin@smartmom.test` | `Admin@12345` |
| Participant | `participant@smartmom.test` | `Participant@12345` |

Dummy spoken audio files are included in `dummy-audio/` for manual upload testing:

- `fyp-progress-review.wav`
- `client-standup.wav`
- `short-action-items.wav`

Manual workflow:

1. Sign in as the demo Organizer.
2. Upload one of the dummy audio files with **New meeting** or **Upload**.
3. Click **Transcribe**.
4. Click **Analyze**.
5. Review the generated minutes, insights, participant access, feedback, and PDF export.

Audio transcription, minutes extraction, and sentiment analysis run locally and do not need an API key. The first analysis downloads the quantized Qwen and DistilBERT model files; later runs use the local cache.

## Local development

On 64-bit Windows, install the local Whisper executable and free model once:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-local-whisper.ps1
```

The Whisper model is about 465 MB. It is stored under `models/`, while the executable is stored under `tools/`; both are intentionally ignored by Git. Then start the app:

```bash
npm install
npm run dev:full
```

Install Python 3.12, then create a virtual environment and install the backend dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

The frontend runs on Vite's displayed local URL and proxies API requests to port `3001`. When `DATABASE_URL` is not set, the API uses persistent SQLite storage under `.data/` for local development. Docker uses PostgreSQL. The Python backend is organized under `backend/app` into API adapters, services, repositories, database models, schemas, and core configuration.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `POSTGRES_DB` | PostgreSQL database name for Docker |
| `POSTGRES_USER` | PostgreSQL user for Docker |
| `POSTGRES_PASSWORD` | PostgreSQL password for Docker |
| `JWT_SECRET` | Long random value used to sign sessions |
| `OPENAI_API_KEY` | Optional; only needed when an OpenAI provider is explicitly selected |
| `TRANSCRIPTION_PROVIDER` | Defaults to `local`; set to `openai` only to use OpenAI transcription |
| `MINUTES_PROVIDER` | Defaults to `local`; set to `openai` only to use OpenAI minutes generation |
| `WHISPER_CPP_PATH` | Path to the local `whisper-cli` executable |
| `WHISPER_MODEL_PATH` | Path to the free `ggml-small.en-tdrz.bin` model |
| `WHISPER_LANGUAGE` | Local transcription language; the included tinydiarize model supports English |
| `HF_HOME` | Persistent cache for local Hugging Face model weights |
| `LOCAL_MINUTES_MODEL` | Defaults to `onnx-community/Qwen2.5-1.5B-Instruct` |
| `LOCAL_SENTIMENT_MODEL` | Defaults to the DistilBERT SST-2 Transformers.js model |
| `OPENAI_TRANSCRIPTION_MODEL` | Used only when `TRANSCRIPTION_PROVIDER=openai` |
| `OPENAI_SUMMARY_MODEL` | Defaults to `gpt-5-mini` |
| `DATABASE_URL` | PostgreSQL connection string for non-Docker deployments |
| `CLIENT_ORIGIN` | Browser origin allowed by the API |

## Production notes

- Never commit `.env`, audio uploads, or database files.
- Use HTTPS and a secrets manager for deployed environments.
- Use encrypted object storage instead of local volumes when scaling across instances.
- Obtain participant consent before recording and define retention and deletion policies.
- AI-generated minutes are review drafts: users should verify decisions, owners, and due dates before export.
- Whisper tinydiarize speaker segmentation is experimental. It detects speaker turns and the app labels alternating turns as Speaker 1 and Speaker 2; users should verify speaker labels, especially for meetings with more than two participants.

## Scripts

| Command | Description |
| --- | --- |
| `npm run dev` | Start the Vite frontend |
| `npm run server` | Start the Python FastAPI server |
| `npm run dev:full` | Start frontend and API together |
| `npm run build` | Create the production frontend build |
| `npm run lint` | Run static linting |
| `npm test` | Run the Python backend tests |
