from flask import Flask, jsonify, request
import pandas as pd
import os

app = Flask(__name__)

BASE     = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, 'data')

FILES = {
    '2024': [
        'chicago_shootings_enriched_2024.csv',
    ],
    '2025': [
        'chicago_shootings_enriched_2025_part1.csv',
        'chicago_shootings_enriched_2025_part2.csv',
        'chicago_shootings_enriched_2025_part3.csv',
    ],
    '2026': [
        'chicago_shootings_enriched_2026_part1.csv',
        'chicago_shootings_enriched_2026_part2.csv',
        'chicago_shootings_enriched_2026_part3.csv',
        'chicago_shootings_enriched_2026_part4.csv',
    ],
}

# Load and cache all CSVs at cold start
DATA = {}
for year, filenames in FILES.items():
    dfs = []
    for fname in filenames:
        path = os.path.join(DATA_DIR, fname)
        if os.path.exists(path):
            dfs.append(pd.read_csv(path, dtype=str))
        else:
            print(f'WARNING: {path} not found')
    if dfs:
        df = pd.concat(dfs, ignore_index=True)
        # Normalize date to YYYY-MM-DD for reliable matching
        df['date_only'] = pd.to_datetime(
            df['date'], errors='coerce'
        ).dt.strftime('%Y-%m-%d')
        DATA[year] = df
        print(f'Loaded {year}: {len(df)} rows')


@app.route('/')
def index():
    return jsonify({
        'name':      'Chicago Gun Violence API',
        'endpoints': {
            '/incidents': 'GET ?date=YYYY-MM-DD&year=YYYY',
            '/health':    'GET — check loaded data',
        }
    })


@app.route('/health')
def health():
    return jsonify({
        'status':      'ok',
        'years':       list(DATA.keys()),
        'row_counts':  {y: len(df) for y, df in DATA.items()},
        'date_ranges': {
            y: {
                'newest': df['date_only'].max(),
                'oldest': df['date_only'].min(),
            }
            for y, df in DATA.items()
        }
    })


@app.route('/incidents')
def incidents():
    date = request.args.get('date', '').strip()   # YYYY-MM-DD
    year = request.args.get('year', '').strip()   # 2024 / 2025 / 2026

    # Validate inputs
    if not date:
        return jsonify({'error': 'date parameter required (YYYY-MM-DD)'}), 400
    if not year:
        return jsonify({'error': 'year parameter required (2024/2025/2026)'}), 400
    if year not in DATA:
        return jsonify({'error': f'No data loaded for year {year}'}), 404

    df      = DATA[year]
    matches = df[df['date_only'] == date].copy()

    if matches.empty:
        return jsonify({
            'date':      date,
            'year':      year,
            'count':     0,
            'incidents': [],
            'message':   f'No incidents found for {date} in {year}',
        })

    # Return only the columns the agent uses
    want = ['case_number', 'date', 'time', 'block',
            'latitude', 'longitude', 'ward', 'fatal']
    cols = [c for c in want if c in matches.columns]

    records = (
        matches[cols]
        .fillna('')
        .to_dict(orient='records')
    )

    return jsonify({
        'date':      date,
        'year':      year,
        'count':     len(records),
        'incidents': records,
    })
