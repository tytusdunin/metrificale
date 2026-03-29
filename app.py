from flask import Flask, render_template, request, jsonify
import subprocess
import pandas as pd
from io import StringIO
from datetime import datetime
import os 

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json.get('text', '')

    start_time = datetime.now()

    process_env = os.environ.copy()
    process_env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        ['python', 'analysis.py'],
        input = data,
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        env=process_env
    )
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    if result.returncode != 0:
        print(f"Error during analysis script execution:\nSTDERR:\n{result.stderr}\nSTDOUT:\n{result.stdout}")
        error_html = f"<p>Wystąpił błąd podczas analizy. Szczegóły:</p><pre>{result.stderr}</pre>"
        return jsonify({'html': error_html}), 500

    stdout = result.stdout

    # Symbole do oznaczania sylab akcentowanych i nieakcentowanych (zmieniamy na reprezentacyjne)
    stdout = stdout.replace('&', '⨩')
    stdout = stdout.replace('^', '⨫')
    stdout = stdout.replace('$', '∸')

    # Wybieramy wartości z analizy
    rodzaj = ''
    zglo = ''
    średniówka = ''
    metrum = ''
    wzorzec_metryczny = ''
    innemetra = ''
    szczyt = ''

    # Use a set for lines already processed to avoid issues if markers are somehow duplicated
    processed_markers = set() 
    
    # Lista do csv-ki
    csv_lines = []

    for line in stdout.splitlines():
        if line.startswith('###RODZAJ:') and 'RODZAJ' not in processed_markers:
            rodzaj = line.replace('###RODZAJ:', '').strip()
            processed_markers.add('RODZAJ')
        elif line.startswith('###ZGLOSKOWIEC:') and 'ZGLOSKOWIEC' not in processed_markers:
            zglo = line.replace('###ZGLOSKOWIEC:', '').strip()
            processed_markers.add('ZGLOSKOWIEC')
        elif line.startswith('###ŚREDNIÓWKA:') and 'ŚREDNIÓWKA' not in processed_markers:
            średniówka = line.replace('###ŚREDNIÓWKA:', '').strip()
            processed_markers.add('ŚREDNIÓWKA')
        elif line.startswith('###METRUM:') and 'METRUM' not in processed_markers:
            metrum = line.replace('###METRUM:', '').strip()
            processed_markers.add('METRUM')
        elif line.startswith('###WZORZEC_METRYCZNY:') and 'WZORZEC_METRYCZNY' not in processed_markers:
            wzorzec_metryczny = line.replace('###WZORZEC_METRYCZNY:', '').strip()
            processed_markers.add('WZORZEC_METRYCZNY')
        elif line.startswith('###INNEMETRA:') and 'INNEMETRA' not in processed_markers:
            innemetra = line.replace('###INNEMETRA:', '').strip()
            processed_markers.add('INNEMETRA')
        elif line.startswith('###SZCZYT:') and 'SZCZYT' not in processed_markers:
            szczyt = line.replace('###SZCZYT:', '').strip()
            processed_markers.add('SZCZYT')
        elif not line.startswith('###'):
            csv_lines.append(line)

    clean_stdout_csv = '\n'.join(csv_lines)

    if not clean_stdout_csv.strip(): # Sprawdzamy, czy csv-ka jest pusta
        return jsonify({'html': '<p>Brak danych tabelarycznych do wyświetlenia.</p>'})

    try:
        df = pd.read_csv(StringIO(clean_stdout_csv))
    except pd.errors.EmptyDataError:
        return jsonify({'html': '<p>Otrzymano puste dane CSV do przetworzenia.</p>'})
    except Exception as e:
        print(f"Error parsing CSV: {e}\nCSV Data:\n{clean_stdout_csv}") # Zapisujemy do debuggingu
        return jsonify({'html': f'<p>Błąd podczas przetwarzania danych tabeli: {e}</p>'}), 500

    if df.empty:
        table_html = "<p>Analiza nie zwróciła danych do tabeli.</p>"
    else:
        # Sprawszamy, czy są kolumny, do stylowania (STARA FUNKCJA, JESZCZE DO PYPHENA)
        if 'excluded' not in df.columns or 'Type' not in df.columns:
            missing_cols = [col for col in ['excluded', 'Type'] if col not in df.columns]
            print(f"Warning: Missing critical columns for styling: {missing_cols}")
            if 'excluded' not in df.columns: df['excluded'] = False 
            if 'Type' not in df.columns: df['Type'] = 'unknown' 

        excluded_flags = df['excluded'].astype(bool)
        type_flags     = df['Type']

        display_df = df.drop(columns=['Linijka', 'Type', 'excluded'], errors='ignore')

        def _style_row(styled_row): # styled_row is a Series from the DataFrame being styled
          style_properties = []

          is_excluded_row = False
          current_row_type = ''

          # Safely access flags using the row's original index (styled_row.name)
          if styled_row.name in excluded_flags.index:
              is_excluded_row = excluded_flags.loc[styled_row.name]
          
          if styled_row.name in type_flags.index:
              current_row_type = type_flags.loc[styled_row.name]
            

          hex_code = styled_row['kolor']
          style_properties.append(f'background-color: {hex_code}66')

          if is_excluded_row:
              style_properties.append('color: red')
              style_properties.append('background-color: #ffcccc') # Jasnoczerowne tło
          
          # Dodajemy style w zależności od rodzaju wiersza
          if current_row_type == 'sylaba':
              style_properties.append('font-weight: bold')
              style_properties.append('font-size: 1.1em')
          if current_row_type == 'symbol':
              style_properties.append('font-size: 2.1em')
          elif current_row_type == 'synafia':
              # --- STYL DO SYNAFII ---
              style_properties.append('padding-bottom: 30px')
          
          final_style_string = '; '.join(style_properties)
          
          # Aplikujemy do wszystkich komórek w wierszu
          return [final_style_string] * len(styled_row) if final_style_string else [''] * len(styled_row)


        styled = (
            display_df
            .style
            .hide(['kolor'], axis=1)
            .apply(_style_row, axis=1)
            .set_table_attributes('class="table table-striped"')
            .set_table_styles([
                {'selector': 'th, td', 'props': [('text-align', 'center')]} # Center all cells
            ])
            .format(na_rep='') # NoneType jako puste
        )
        table_html = styled.to_html(index=False)

    html_parts = [
        f'<h2>Wynik analizy</h2>',
        f'<p><strong>Rodzaj wiersza:</strong> {rodzaj}</p>',
        f'<p><strong>Długość:</strong> {zglo}-zgłoskowiec</p>',
        f'<p><strong>Średniówka:</strong> {średniówka}</p>',
        f'<p><strong>Metrum:</strong> {metrum}</p>',
        #f'<p><strong>Inne rozważane metra:</strong> {innemetra}</p>', (DEBUG)
        #f'<p><strong>Wartość "szczytu" (dla wzorca):</strong> {szczyt}</p>', (DEBUG)
        f'<h1 style="text-align: center;">{wzorzec_metryczny}</h1>',
        '<hr style="border-top: 1px solid grey;">',
        table_html,
        f'<p><i>Metrificale nie obsługuje obecnie wierszy tonicznych i metrów logaedycznych.</i></p>',
        f'<p><strong>Czas analizy:</strong> {duration:.2f} sekund</p>' # TUTAJ CZAS ANALIZY
    ]
    return jsonify({'html': '\n'.join(html_parts)})

if __name__ == '__main__':
    app.run(debug=True)