# Veritas

Veritas is a multi-agent legal automation platform for end-to-end case work. It helps lawyers and legal departments coordinate intake, case analysis, document work, internal escalation, client-facing communication, and workflow execution from one workspace.

The business goal is practical: help real legal teams scale the number of matters they can handle without increasing headcount at the same rate. By automating repeatable legal operations and routing work to specialized agents, Veritas can reduce the amount of work outsourced to external providers, saving cost while keeping more context and control inside the team.

## Multi-Agent Legal Automation

Veritas is designed as a multi-agent system rather than a single chatbot. Each agent or tool has a bounded role in the legal workflow, such as answering case questions, retrieving case data, generating documents, contacting internal employees, or preparing external communications for approval.

This architecture supports E2E lawyer and legal department assistance:

- Case workspace support for matter context, notes, chat, and document activity.
- Server-side orchestration for legal cases, chat, traces, documents, and agent tools.
- Human approval gates for sensitive external actions.
- Integrations with Supabase for case data, OpenAI for reasoning, and Telegram for internal or external contact flows.

## Project Structure

- `client`: Angular application for the legal workspace and dashboard.
- `server`: FastAPI API for case orchestration, agent chat, tools, documents, traces, and integrations.
- `server/routes`: API endpoint groups.
- `server/services`: business logic and agent orchestration.
- `server/data_access`: external clients and persistence access.
- `server/schemas`: response and request models.

## Setup

Create a local environment file from the example:

```bash
cp .env.example .env
```

Configure the required values:

```bash
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
OPENAI_API_KEY=...
OPENAI_CHAT_MODEL=gpt-5.5
TELEGRAM_BOT_TOKEN=...
TELEGRAM_INTERNAL_CHAT_ID=...
TELEGRAM_EXTERNAL_CHAT_ID=...
```

## Run The Server

The server uses Python and `uv`.

```bash
cd server
uv sync
uv run uvicorn main:app --reload
```

Health check:

```bash
curl http://localhost:8000/api/v1/status
```

Expected response:

```json
{
  "message": "Veritas API is running"
}
```

## Run The Client

```bash
cd client
npm install
npm start
```

The Angular app runs locally at `http://localhost:4200` and talks to the FastAPI server through the configured API routes.

## Telegram Contact Tool

The Veritas agent includes a `contact_internal_employee` tool, shown in the UI as `Contact internal employee`. It sends a plain-text Telegram message to one configured internal recipient.

To configure it:

1. Create a Telegram bot with BotFather and copy the bot token.
2. Start a chat with the bot, or add the bot to the target internal chat.
3. Set `TELEGRAM_BOT_TOKEN`, `TELEGRAM_INTERNAL_CHAT_ID`, and `TELEGRAM_EXTERNAL_CHAT_ID` in `.env`.

Recipients are fixed by environment configuration. Veritas supplies the message text, and external contact messages require user approval in the chat UI before Telegram is called.
