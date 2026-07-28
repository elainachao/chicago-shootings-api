from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import json
import os

app = Flask(__name__)
CORS(app)  # required so map artifact can fetch from this domain

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
            '/incidents':      'GET ?date=YYYY-MM-DD&year=YYYY',
            '/boundaries':     'GET — ward and district GeoJSON',
            '/victim-search':  'GET ?block=&date=YYYY-MM-DD — DuckDuckGo snippet search',
            '/health':         'GET — check loaded data',
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


@app.route('/boundaries')
def boundaries():
    """Serves ward and district GeoJSON from local files."""
    result = {}
    ward_path     = os.path.join(DATA_DIR, 'ward_boundaries.json')
    district_path = os.path.join(DATA_DIR, 'police_districts.json')
    if os.path.exists(ward_path):
        with open(ward_path) as f:
            result['wards'] = json.load(f)
    if os.path.exists(district_path):
        with open(district_path) as f:
            result['districts'] = json.load(f)
    if not result:
        return jsonify({'error': 'Boundary files not found'}), 404
    return jsonify(result)


@app.route('/victim-search')
def victim_search():
    block    = request.args.get('block', '').strip()
    date     = request.args.get('date', '').strip()
    city     = 'Chicago'

    import urllib.request, urllib.parse, re

    queries = [
        f'{date} shooting victim {block} {city}',
        f'{city} shooting {block} {date[:7]}',
        f'{city} {block} shooting victim',
    ]

    snippets = []
    headers  = {'User-Agent': 'Mozilla/5.0'}

    for q in queries:
        try:
            url = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(q)
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            # Pull text from result snippets
            found = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', html)
            for f in found[:5]:
                clean = re.sub(r'<[^>]+>', '', f).strip()
                if clean and city.lower() in clean.lower():
                    snippets.append(clean)
        except Exception as e:
            print(f'victim-search error: {e}')

    return jsonify({
        'date':     date,
        'block':    block,
        'queries':  queries,
        'snippets': snippets[:10]
    })
