from flask import Flask, jsonify, request
import pandas as pd
import os

app = Flask(__name__)

# Directory containing the enriched CSV data files
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# Load all CSVs at startup
DATA = {}
FILES = {
    '2024': ['chicago_shootings_enriched_2024.csv'],
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

for year, files in FILES.items():
    dfs = []
    for f in files:
        path = os.path.join(DATA_DIR, f)
        if os.path.exists(path):
            dfs.append(pd.read_csv(path))
    if dfs:
        DATA[year] = pd.concat(dfs, ignore_index=True)

@app.route('/incidents')
def incidents():
    date = request.args.get('date')   # YYYY-MM-DD
    year = request.args.get('year')   # 2024/2025/2026

    if not date or not year:
        return jsonify({'error': 'date and year required'}), 400

    if year not in DATA:
        return jsonify({'error': f'No data for year {year}'}), 404

    df = DATA[year]

    # Normalize date column — handle both date-only and datetime formats
    df['date_only'] = pd.to_datetime(
        df['date'], errors='coerce'
    ).dt.strftime('%Y-%m-%d')

    matches = df[df['date_only'] == date]

    if matches.empty:
        return jsonify({
            'date': date,
            'count': 0,
            'incidents': [],
            'message': f'No incidents found for {date}'
        })

    # Return only the columns the agent needs
    cols = ['case_number', 'date', 'time', 'block',
            'latitude', 'longitude', 'ward', 'fatal']
    cols = [c for c in cols if c in matches.columns]

    return jsonify({
        'date': date,
        'count': len(matches),
        'incidents': matches[cols].to_dict(orient='records')
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'years_loaded': list(DATA.keys()),
        'row_counts': {y: len(df) for y, df in DATA.items()}
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
