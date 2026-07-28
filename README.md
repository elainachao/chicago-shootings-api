# chicago-shootings-api

Flask API serving enriched Chicago gun violence shooting incident data (2024–2026), deployable to Vercel.

## Endpoints

- `GET /health` — status and row counts per year.
- `GET /incidents?date=YYYY-MM-DD&year=YYYY` — incidents matching the given date and year.

## Structure

```
api/
  index.py       # Flask app (Vercel serverless entrypoint)
  data/          # Enriched CSV data files
requirements.txt
vercel.json
```

## Local development

```bash
pip install -r requirements.txt
python api/index.py
```

Serves on `http://0.0.0.0:5001`.

## Deploy to Vercel

```bash
vercel deploy
```
