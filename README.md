# SmartMOM Bot

SmartMOM Bot is a professional meeting-intelligence workspace that turns consented meeting recordings into reviewable minutes, decisions, action items, participant insights, and PDF exports.

## Highlights

- Secure Organizer and Participant roles with JWT authentication
- Upload or record meeting audio directly in the workspace
- AI transcription and structured minutes generation with OpenAI
- Editable agenda, decisions, discussion notes, and action items
- Meeting participant access control and feedback capture
- PDF export for finalized meeting minutes
- Responsive React interface with a production Nginx reverse proxy

## Architecture

| Service | Responsibility |
| --- | --- |
| `web` | React production build served through Nginx |
| `api` | Express API, authentication, file handling, AI processing, PDF generation |
| `database` | PostgreSQL 16 persistent application database |
| `nginx` | Included inside the `web` container; serves the SPA and proxies `/api` |

## Quick start with Docker

1. Copy `.env.example` to `.env`.
2. Set strong values for `POSTGRES_PASSWORD` and `JWT_SECRET`.
3. Add `OPENAI_API_KEY` to enable transcription and AI analysis.
4. Start the application:

```bash
docker compose up --build -d
```

Open `http://localhost:8080`.

To stop the stack while retaining database and uploaded-audio volumes:

```bash
docker compose down
```

## Local development

```bash
npm install
npm run dev:full
```

The frontend runs on Vite's displayed local URL and proxies API requests to port `3001`. When `DATABASE_URL` is not set, the API uses persistent embedded PGlite storage under `.data/` for local development.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `POSTGRES_DB` | PostgreSQL database name for Docker |
| `POSTGRES_USER` | PostgreSQL user for Docker |
| `POSTGRES_PASSWORD` | PostgreSQL password for Docker |
| `JWT_SECRET` | Long random value used to sign sessions |
| `OPENAI_API_KEY` | Enables audio transcription and AI minutes generation |
| `OPENAI_TRANSCRIPTION_MODEL` | Defaults to `gpt-4o-transcribe-diarize` |
| `OPENAI_SUMMARY_MODEL` | Defaults to `gpt-5-mini` |
| `DATABASE_URL` | PostgreSQL connection string for non-Docker deployments |
| `CLIENT_ORIGIN` | Browser origin allowed by the API |

## Production notes

- Never commit `.env`, audio uploads, or database files.
- Use HTTPS and a secrets manager for deployed environments.
- Use encrypted object storage instead of local volumes when scaling across instances.
- Obtain participant consent before recording and define retention and deletion policies.
- AI-generated minutes are review drafts: users should verify decisions, owners, and due dates before export.

## Scripts

| Command | Description |
| --- | --- |
| `npm run dev` | Start the Vite frontend |
| `npm run server` | Start the Express API |
| `npm run dev:full` | Start frontend and API together |
| `npm run build` | Create the production frontend build |
| `npm run lint` | Run static linting |
