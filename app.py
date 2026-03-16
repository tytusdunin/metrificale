from flask import Flask, render_template, request, jsonify
import subprocess
import pandas as pd
from io import StringIO
from datetime import datetime
import os # Not strictly used in the provided snippet but often useful

app = Flask(__name__)

# Ensure output folder exists (if you were writing output files, not relevant here)
# OUTPUT_TXT = 'input.txt' # This is input, not output folder

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json.get('text', '')
    # Consider validating 'data' here
    
    # Use a temporary file or pass data via stdin if it can be large,
    # but for typical text analysis, writing to 'input.txt' is fine.
    #with open('input.txt', 'w', encoding='utf-8') as f:
    #   f.write(data)

    start_time = datetime.now()
    # Ensure 'analysis.py' is the correct script name. User mentioned 'analisys.py' but code used 'analysis.py'.
    # Added errors='replace' for robustness in decoding.
    # In app.py
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
        # Log the error for server-side debugging
        print(f"Error during analysis script execution:\nSTDERR:\n{result.stderr}\nSTDOUT:\n{result.stdout}")
        # Provide a user-friendly error
        error_html = f"<p>Wystąpił błąd podczas analizy. Szczegóły:</p><pre>{result.stderr}</pre>"
        return jsonify({'html': error_html}), 500

    stdout = result.stdout


    # symbole do oznaczania sylab akcentowanych i nieakcentowanych
    stdout = stdout.replace('&', '⨩')
    stdout = stdout.replace('^', '⨫')
    stdout = stdout.replace('$', '∸')

    # Extract special values
    rodzaj = ''
    zglo = ''
    średniówka = '' # Initialize all variables
    metrum = ''
    wzorzec_metryczny = '' # New variable for the symbolic pattern
    innemetra = ''
    szczyt = ''

    # Use a set for lines already processed to avoid issues if markers are somehow duplicated
    processed_markers = set() 
    
    # Prepare a list for CSV lines
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
        elif line.startswith('###WZORZEC_METRYCZNY:') and 'WZORZEC_METRYCZNY' not in processed_markers: # Parse the new line
            wzorzec_metryczny = line.replace('###WZORZEC_METRYCZNY:', '').strip()
            processed_markers.add('WZORZEC_METRYCZNY')
        elif line.startswith('###INNEMETRA:') and 'INNEMETRA' not in processed_markers:
            innemetra = line.replace('###INNEMETRA:', '').strip()
            processed_markers.add('INNEMETRA')
        elif line.startswith('###SZCZYT:') and 'SZCZYT' not in processed_markers:
            szczyt = line.replace('###SZCZYT:', '').strip()
            processed_markers.add('SZCZYT')
        elif not line.startswith('###'):
            csv_lines.append(line) # Collect CSV lines

    clean_stdout_csv = '\n'.join(csv_lines)

    if not clean_stdout_csv.strip(): # Check if CSV data is empty
        return jsonify({'html': '<p>Brak danych tabelarycznych do wyświetlenia.</p>'})

    try:
        df = pd.read_csv(StringIO(clean_stdout_csv))
    except pd.errors.EmptyDataError:
        return jsonify({'html': '<p>Otrzymano puste dane CSV do przetworzenia.</p>'})
    except Exception as e:
        print(f"Error parsing CSV: {e}\nCSV Data:\n{clean_stdout_csv}") # Log for debugging
        return jsonify({'html': f'<p>Błąd podczas przetwarzania danych tabeli: {e}</p>'}), 500

    if df.empty:
        table_html = "<p>Analiza nie zwróciła danych do tabeli.</p>"
    else:
        # Ensure required columns for styling exist
        if 'excluded' not in df.columns or 'Type' not in df.columns:
            # Handle missing critical columns, perhaps by returning an error or simpler table
            missing_cols = [col for col in ['excluded', 'Type'] if col not in df.columns]
            print(f"Warning: Missing critical columns for styling: {missing_cols}")
            # Fallback: render table without these styles or with default styling
            # For now, we'll proceed, but styling might fail or be incomplete.
            # A robust solution might involve conditional styling.
            if 'excluded' not in df.columns: df['excluded'] = False # Add default if missing
            if 'Type' not in df.columns: df['Type'] = 'unknown' # Add default if missing


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

          # Apply styles for excluded rows
          if is_excluded_row:
              style_properties.append('color: red')
              style_properties.append('background-color: #ffcccc') # Light red background
          
          # Apply styles based on row type
          if current_row_type == 'sylaba':
              style_properties.append('font-weight: bold')
              style_properties.append('font-size: 1.1em')
          if current_row_type == 'symbol':
              style_properties.append('font-size: 2.1em')
          elif current_row_type == 'synafia':
              # --- THIS IS THE ADDED STYLE FOR SYNAFIA ROWS ---
              style_properties.append('padding-bottom: 30px') # Adjust "15px" as needed (e.g., "1em", "20px")
              # Optional: Add a subtle line too for more separation
              # style_properties.append('border-bottom: 1px solid #ddd') 
              # ----------------------------------------------------
          
          final_style_string = '; '.join(style_properties)
          
          # Apply the combined style string to all cells in the current row
          return [final_style_string] * len(styled_row) if final_style_string else [''] * len(styled_row)


        styled = (
            display_df
            .style
            .apply(_style_row, axis=1)
            .set_table_attributes('class="table table-striped"')
            .set_table_styles([
                {'selector': 'th, td', 'props': [('text-align', 'center')]} # Center all cells
            ])
            .format(na_rep='') # Render NaNs as empty strings
        )
        table_html = styled.to_html(index=False)

    html_parts = [
        f'<h2>Wynik analizy</h2>',
        f'<p><strong>Rodzaj wiersza:</strong> {rodzaj}</p>',
        f'<p><strong>Długość:</strong> {zglo}-zgłoskowiec</p>',
        f'<p><strong>Średniówka:</strong> {średniówka}</p>',
        f'<p><strong>Metrum:</strong> {metrum}</p>', # Display metrum with its symbolic pattern
        #f'<p><strong>Inne rozważane metra:</strong> {innemetra}</p>',
        #f'<p><strong>Wartość "szczytu" (dla wzorca):</strong> {szczyt}</p>',
        f'<h1 style="text-align: center;">{wzorzec_metryczny}</h1>',
        '<hr style="border-top: 1px solid grey;">',
        table_html,
        f'<p><i>Metrificale nie obsługuje obecnie wierszy tonicznych i metrów logaedycznych.</i></p>',
        f'<p><strong>Czas analizy:</strong> {duration:.2f} sekund</p>' # Formatted duration
    ]
    return jsonify({'html': '\n'.join(html_parts)})

if __name__ == '__main__':
    app.run(debug=True)