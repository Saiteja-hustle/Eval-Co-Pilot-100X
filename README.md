# Eval-Co-Pilot-100X
Repo for the tool that finds bugs in ai apps before getting shipped

## Stage 0: Setup

### Run locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000/api/hello — it should return `{"status": "ok"}`.

### Environment variables

Copy `.env.example` to `.env` and fill in real values (never commit `.env`):

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

These aren't used yet — they're placeholders for a later stage.
