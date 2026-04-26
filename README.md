# Veritas

Multi-agent system for end-to-end legal processes.

## Server

Basic FastAPI backend skeleton with separated responsibilities:

- `routes`: one file per endpoint group, with route handlers and route-local dependency wiring
- `services`: business logic
- `data_access`: data access
- `schemas`: response models
- `main.py`: FastAPI bootstrap

### Run

```bash
cd server
pip install -r requirements.txt
uvicorn main:app --reload
```

### Route

`GET /api/v1/status`

Example response:

```json
{
  "message": "Veritas API is running"
}
```

### Telegram internal contact tool

The Veritas agent includes a `contact_internal_employee` tool, shown in the UI as
`Contact internal employee`. It sends a plain-text Telegram message to one
configured internal recipient.

Setup:

1. Create a Telegram bot with BotFather and copy the bot token.
2. Start a chat with the bot, or add the bot to the target internal chat.
3. Set these values in `.env`:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_INTERNAL_CHAT_ID=your_internal_chat_id
TELEGRAM_EXTERNAL_CHAT_ID=your_external_chat_id
```

Recipients are fixed by environment configuration; Veritas only supplies the
message text. External contact messages require user approval in the chat UI
before Telegram is called.
