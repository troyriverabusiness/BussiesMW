# BussiesMW

Multi Agent system for E2E legal processes (in BMW)

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
  "message": "Server is running"
}
```
