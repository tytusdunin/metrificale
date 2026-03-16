# -*- coding: utf-8 -*-
import pandas as pd
import pyphen
from kokosznicka import Kokosznicka
import string
import re
import json
import sys
from io import StringIO
import morfeusz2
morf = morfeusz2.Morfeusz()

# DEKLARUJEMY WSZYSTKO, CO POTRZEBNE
atona = {'się', 'bym', 'byś', 'by', 'i', 'a', 'o', 'li'}
semiortotona = {'aby', 'albo', 'ale', 'jeśli', 'oraz'}
zaimki_ortotona = {'nikt', 'nic', 'ktoś', 'coś', 'gdzieś'}

proproparoksytona = {'libyśmy', 'libyście', 'łybyśmy' 'łybyście'}
oksy_prefiksy = ("eks", "arcy", "super", "wice", "anty")

file_path = 'proparoksytona2.txt'
proparoksytona = set(line.strip() for line in open(file_path, 'r', encoding='utf-8'))

oksytona_path = 'oksytona.txt'
oksytona = set(line.strip() for line in open(oksytona_path, 'r', encoding='utf-8'))

false_path = 'false-friends.txt'
false_friends = set(line.strip() for line in open(false_path, 'r', encoding='utf-8'))

amfimakry_path = 'amfimakry.txt'
amfimakry = set(line.strip() for line in open(amfimakry_path, 'r', encoding='utf-8'))

wykrzykniki_path = 'wykrzyk.txt'
wykrzykniki = set(line.strip() for line in open(wykrzykniki_path, 'r', encoding='utf-8'))

# Inicjalizacja Pyphen dla języka polskiego
dic = pyphen.Pyphen(lang='pl')

#def split_into_syllables(word):
#    # Sylabifikacja
#    return dic.inserted(word).split('-')

def sprawdz_koniec(slowo, koncowka):
    return slowo.endswith(koncowka)

def sprawdz_poczatek(slowo, poczatek):
    return slowo.startswith(poczatek)

def oksytona_prefiksowane(word: str) -> bool:
    for p in oksy_prefiksy:
        if word.startswith(p):
            base = word[len(p):]
            # morf.analyse() zwraca listę trójek (start, end, (form, lemma, tag))
            for _, _, interp in morf.analyse(base):
                if interp[2].startswith("subst:"):
                    return True
            return False
    return False

def zestrajacz_nie(text: str) -> str:
    words = text.split()
    result = []
    i = 0
    while i < len(words):
        if words[i] == "nie" and i + 1 < len(words):
            analyses = morf.analyse(words[i + 1])
            if any(ana[2].startswith("fin:") or ana[2].startswith("praet:") or ana[2].startswith("impt:") or ana[2].startswith("inf:") for _, _, ana in analyses):
                result.append("nie" + words[i + 1])
                i += 2
                continue
        result.append(words[i])
        i += 1
    return ' '.join(result)

def anty_zestrajacz_nie(slowo):
    nie = "nie"
    if slowo.startswith(nie):
        slowo = slowo.lstrip(nie)
        analyses = morf.analyse(slowo)
        if any(ana[2].startswith("fin:") or ana[2].startswith("praet:") or ana[2].startswith("impt:") or ana[2].startswith("inf:") for _, _, ana in analyses):
            return True
    else:
        return False

def create_syllable_dataframe(text):
    # Podziel na linie
    lines = text.strip().split('\n')

    # Lista na sylaby
    syllable_data = []

    # Stressrank na linię
    stressrank_lines = []

    # Wczytanie końcówek z pliku (plik zawiera końcówki proparoksytonizujące

    # Iteruj przez kolejne linie
    for line_idx, line in enumerate(lines, start=1):
        words = line.split()  # Podziel linię na słowa
        stressrank_values = []  # Lista do przechowywania wartości stressrank dla bieżącej linii

        # Przetwarzanie słów w linii
        for word in words:
            syllables = Kokosznicka.hyphenate(word).split('-')  # Podziel słowo na sylaby
            syllable_count = len(syllables)

            # Sprawdzenie, czy słowo kończy się jedną z końcówek z pliku przy użyciu funkcji sprawdz_koniec
            proparoksytoneza_koncowkowa = any(sprawdz_koniec(word.lower(), koncowka) for koncowka in proparoksytona) and word.lower() not in false_friends
            proproparoksytoneza_koncowkowa = any(sprawdz_koniec(word.lower(), koncowka) for koncowka in proproparoksytona)

            # Przypisanie wartości stressrank według pozycji sylaby
            for syllable_idx, syllable in enumerate(syllables):
                syllable_position = syllable_count - syllable_idx  # Pozycja sylaby od końca
                if  word.lower() in amfimakry and syllable_position == 3:
                    stressrank = 3
                elif  word.lower() in amfimakry and syllable_position == 1:
                    stressrank = 3
                elif proproparoksytoneza_koncowkowa and syllable_position == 4:
                    stressrank = 3
                elif proparoksytoneza_koncowkowa and not proproparoksytoneza_koncowkowa and syllable_position == 3:
                    stressrank = 3
                elif syllable_position == syllable_count and word.lower() in semiortotona:
                    stressrank = 2
                elif syllable_position == 1 and word.lower() in semiortotona:
                    stressrank = 2
                elif syllable_position == 1 and syllable_count <= 3 and oksytona_prefiksowane(word) == True:
                    stressrank = 3
                elif syllable_position == 1 and word.lower() in oksytona:
                    stressrank = 3
                elif syllable_position == 2 and not proparoksytoneza_koncowkowa and not proproparoksytoneza_koncowkowa and word.lower() not in oksytona and word.lower() not in amfimakry and oksytona_prefiksowane(word) == False:
                    stressrank = 3
                elif syllable_count == 1 and word.lower() in zaimki_ortotona or syllable_count == 1 and word.lower() in wykrzykniki:
                    stressrank = 3
                elif syllable_count == 1 and word.lower() not in atona:
                    stressrank = 1
                else:
                    stressrank = 0
                stressrank_values.append(str(stressrank))

                syllable_data.append({
                    'Line number': line_idx,  # Numer linii (od 1)
                    'Line': line,
                    'Syllablecount': syllable_count,
                    'Word': word,
                    'Syllable': syllable,
                    'Syllable Position': syllable_position,
                    'Stressrank': stressrank
                })

        # Łączymy wartości stressrank dla całej linii
        stressrank_lines.append(''.join(stressrank_values))

    # Tworzenie DataFrame'a z zebranych danych
    df = pd.DataFrame(syllable_data, columns=['Line number', 'Line', 'Syllablecount', 'Word', 'Syllable', 'Syllable Position', 'Stressrank'])

    # Dodanie pustych kolumn
    df['synafia'] = 0
    #df['wykluczenie'] = pd.Series([False] * len(df), dtype='bool')
    df['zestrój'] = 0
    df['człon'] = 0

    # Tworzenie outputu stressrank jako ciąg znaków
    stressrank_output = '\n'.join(stressrank_lines)

    return df, stressrank_output

# Wczytanie tekstu z stdin

pretext = sys.stdin.read()

# Funkcja czyszczenia tekstu (przyimki niesylabiczne i przecinki)
def czyszczenie(text, dic):
    for i, j in dic.items():
        text = text.replace(i, j)
    return text

deinterpunktyzator = str.maketrans('', '', string.punctuation)

zmiany = {
    ' w ': ' w~', 'W ': 'W~', '…': '', '«': '', '»': '',
    ' z ': ' z~', 'Z ': 'Z~', ' k ': ' k~',
}

prepyphen_path = 'ustab-zestr.txt'
with open(prepyphen_path, 'r', encoding='utf-8') as f:
    for line in f:
        match = re.match(r"'\s*(.*?)'\s*:\s*'\s*(.*?)'\s*", line.strip())
        if match:
            old, new = match.groups()
            zmiany[old] = new

text = zestrajacz_nie(pretext)
text = pretext.translate(deinterpunktyzator)
text = czyszczenie(text, zmiany)

# Tworzenie DataFrame'a i outputu stressrank
df, stressrank_output = create_syllable_dataframe(text)

# ZOSTAWIAM NA PÓŹNIEJ - trzeba wyczyścić "wykluczenie"
for line_num, group in df.groupby("Line number"):
    df.loc[df["Line number"] == line_num, "wykluczenie"] = False

# ------------------------------------------------------------------
# ANTY-EPITROCHAZM
# ------------------------------------------------------------------
atona = {'się', 'bym', 'byś', 'by', 'i', 'a', 'o'}

for line in df['Line number'].unique():
    # Extract the syllables for the current line and reset the index
    # to keep track of the original DataFrame indices.
    line_df = df[df['Line number'] == line].reset_index()

    # Iterate over the syllables in the current line.
    for i, row in line_df.iterrows():
        # Process only one-syllable words not in the atona list.
        if row['Syllablecount'] == 1 and row['Word'].lower() not in atona:
            # Retrieve current stressrank; ensure it's an integer
            new_stressrank = int(row['Stressrank'])

            # Initialize previous and next stress values (if available)
            prev_stress = None
            next_stress = None

            # If not the first syllable in the line, get previous syllable's stressrank.
            if i > 0:
                prev_stress = int(line_df.loc[i - 1, 'Stressrank'])
            # If not the last syllable in the line, get next syllable's stressrank.
            if i < len(line_df) - 1:
                next_stress = int(line_df.loc[i + 1, 'Stressrank'])

            # Rule 1 & 2: If the one-syllable word is the first in the line.
            if i == 0 and next_stress is not None:
                if next_stress == 3:
                    new_stressrank -= 1
                elif next_stress == 0:
                    new_stressrank += 1

            # Rules that require both neighbors to be present.
            if prev_stress is not None and next_stress is not None:
                # Rule 3: Subtract 1 if both neighbors have stressrank 2 or higher.
                if prev_stress >= 2 and next_stress >= 2:
                    new_stressrank -= 1
                # Rule 4: Subtract 1 if previous is 0 and next is 2 or higher.
                if prev_stress == 0 and next_stress >= 2:
                    new_stressrank -= 1
                # Rule 5: Add 1 if previous is 2 or higher and next is 0.
                if prev_stress >= 2 and next_stress == 0:
                    new_stressrank -= 1
                # Rule 6: Add 1 if both neighbors have stressrank 0.
                if prev_stress == 0 and next_stress == 0:
                    new_stressrank += 1

            # Update the original DataFrame with the new stressrank.
            # We use the original index saved in the temporary DataFrame.
            original_index = row['index']
            df.at[original_index, 'Stressrank'] = new_stressrank


# -----------------------------------------------------------------------
# FUNKCJA DWÓJKA
# -----------------------------------------------------------------------

def dwójka(df):

    df = df.copy()
    df['zestrój'] = df.get('zestrój', 0)

    for line_num, group in df.groupby('Line number'):
        idxs = group.index.tolist()
        starts = [i for i in idxs if group.at[i, 'Syllable Position'] == group.at[i, 'Syllablecount']]
        segments = []
        for start_pos, start in enumerate(starts):
            syl_count = group.at[start, 'Syllablecount']
            end = starts[start_pos + 1] - 1 if start_pos + 1 < len(starts) else idxs[-1]
            segments.append({'start': start, 'end': end, 'syl_count': syl_count})

        last_curr_idx = None
        seq_id = 0
        for idx in range(1, len(segments)):
            prev = segments[idx - 1]
            curr = segments[idx]
            if prev['syl_count'] == 1 and curr['syl_count'] >= 3 and df.at[prev['start'], 'Word'].lower() not in atona and anty_zestrajacz_nie(df.at[curr['start'], 'Word']) == False:
                if last_curr_idx is not None and (idx - 1) == last_curr_idx + 1:
                    seq_id += 1
                else:
                    seq_id = 1
                df.loc[prev['start']:prev['end'], 'zestrój'] = seq_id
                df.loc[curr['start']:curr['end'], 'zestrój'] = seq_id
                last_curr_idx = idx
    return df

df = dwójka(df)

# DWÓJKA: WPROWADZAMY STRESSRANKI

def dwójka_popraw_stressrank(df):
    file_path = 'proparoksytona2.txt'
    proparoksytona = set(line.strip() for line in open(file_path, 'r', encoding='utf-8'))
    df = df.copy()

    for line_num, group in df.groupby('Line number'):
        idxs = group.index.tolist()
        zesty = [i for i in idxs if group.at[i, 'zestrój'] > 0]

        # Podziel na spójne odcinki
        runs = []
        for i in zesty:
            if not runs or i != runs[-1][-1] + 1:
                runs.append([i])
            else:
                runs[-1].append(i)

        for run in runs:
            first_idx = run[0]
            second_idx = run[1]
            starts = [j for j in idxs if group.at[j, 'Syllable Position'] == group.at[j, 'Syllablecount'] and j < first_idx]
            if starts:
                per_idx = starts[-1]
                word = group.at[per_idx, 'Word']
                propar = any(word.endswith(k) for k in proparoksytona)
# not propar and not oksytona_prefiksowane and word.lower() in oksytona and
                if df.at[first_idx, 'Stressrank'] < 2:
                    df.at[first_idx, 'Stressrank'] = 2
                else:
                    df.at[second_idx, 'Stressrank'] = 0
                    

            # Now iterate over the run to apply the second rule
            for k in range(1, len(run) - 1):
                prev_idx = run[k - 1]
                curr_idx = run[k]
                next_idx = run[k + 1]
                if df.at[i, 'Syllable Position'] == 1:
                    continue
                if df.at[i, 'Syllable Position'] == 2:
                    continue
                if (df.at[curr_idx, 'Stressrank'] == 0 and
                    df.at[prev_idx, 'Stressrank'] == 0 and
                    df.at[next_idx, 'Stressrank'] == 0):
                    df.at[curr_idx, 'Stressrank'] = 1

    return df

df = dwójka_popraw_stressrank(df)

# DWÓJKA: WIĘCEJ NIŻ CZTERYYYYYY

oksytona_path = 'oksytona.txt'
oksytona = set(line.strip() for line in open(oksytona_path, 'r', encoding='utf-8'))

# 1. Utworzenie identyfikatora porządku słowa w linii
# Flaga nowego słowa
df['is_new_word'] = (df['Line number'] != df['Line number'].shift()) | (df['Word'] != df['Word'].shift())
# Numer słowa w obrębie tekstu (globalnie), przyda się do grupowania
df['WordIdx'] = df['is_new_word'].cumsum()

# 2. Mapowanie poprzedzającego słowa z tej samej linii
# Tworzymy słownik {WordIdx: preceding_word}
prev_word = {}
# Grupujemy po linii, aby ustalić peryferia per słowo
for ln, group in df.groupby('Line number'):
    # Lista unikalnych słów w kolejności
    word_order = group.drop_duplicates('WordIdx')[['WordIdx', 'Word']].values.tolist()
    for i, (widx, w) in enumerate(word_order):
        if i == 0:
            prev_word[widx] = None
        else:
            prev_word[widx] = word_order[i-1][1]

# Dodajemy kolumnę peryferia
df['peryferia'] = df['WordIdx'].map(prev_word)

# 3. Wybieramy słowa o 4+ sylabach, których wszystkie zestrój == 0
# Lista WordIdx spełniających warunek
long_zero = []
for widx, group in df.groupby('WordIdx'):
    if group['Syllablecount'].iloc[0] >= 4 and (group['zestrój'] == 0).all():
        long_zero.append(widx)

# 4. Stosujemy reguły w kolejności
for widx in long_zero:
    group = df[df['WordIdx'] == widx]
    # Indeksy w oryginalnym df
    idxs = group.index.tolist()
    # 4a. Pierwsza sylaba od początku: Syllable Position == Syllablecount
    first_idx = group[group['Syllable Position'] == group['Syllablecount'].iloc[0]].index
    for i in first_idx:
        if df.at[i, 'peryferia'] not in oksytona and df.at[i, 'peryferia'] not in proparoksytona and anty_zestrajacz_nie(df.at[i, 'Word']) == False:
            df.at[i, 'Stressrank'] = 2
    # 4b. Środkowe sylaby: nie ostatnia, stres==0 oraz sąsiadujące stresy==0
    for pos in range(len(idxs)):
        i = idxs[pos]
        # pomijamy ostatnią sylabę
        if df.at[i, 'Syllable Position'] == 1:
            continue
        if df.at[i, 'Syllable Position'] == 2:
            continue
        if df.at[i, 'Stressrank'] == 0:
            # sąsiednie w kolejności ramki
            prev_i = idxs[pos-1] if pos > 0 else None
            next_i = idxs[pos+1] if pos < len(idxs)-1 else None
            if prev_i and next_i:
                if df.at[prev_i, 'Stressrank'] == 0 and df.at[next_i, 'Stressrank'] == 0:
                    df.at[i, 'Stressrank'] = 1

# Usuwamy pomocnicze kolumny, jeśli nie są już potrzebne
df.drop(columns=['is_new_word', 'WordIdx', 'peryferia'], inplace=True)

# ---------------------------------------------------------------------
# ŚREDNIÓWKA
# --------------------------------------------------------------------
from collections import Counter

# 1. Filtrujemy sylaby z wykluczenie == False, zachowując oryginalny numer linii
df_valid = df[df['wykluczenie'] == False].copy()

# 2. Numerujemy sylaby w każdej oryginalnej linii od 1
df_valid['syll_line_idx'] = df_valid.groupby('Line number').cumcount() + 1

# 3. Dla każdej oryginalnej linii zbieramy pary sylab, między którymi jest podział między słowami
line_splits = {}
all_splits = []

for line_num, group in df_valid.groupby('Line number'):
    splits = []
    line_length = len(group)
    # Iterujemy po kolejnych sylabach w danej linii
    for i in range(len(group) - 1):
        curr = group.iloc[i]
        nxt  = group.iloc[i + 1]
        # jeśli sylaby należą do różnych słów → podział
        if curr['Word'] != nxt['Word']:
            first_syll_idx = curr['syll_line_idx']
            second_syll_idx_from_end = line_length - first_syll_idx
            pair = f"{first_syll_idx}+{second_syll_idx_from_end}"
            if not pair.startswith("1+"):
                splits.append(pair)
                all_splits.append(pair)
    if splits:
        line_splits[line_num] = splits

# 5. Obliczamy najczęstsze podziały w całym tekście
if all_splits:
    counter = Counter(all_splits)
    most_common = counter.most_common(1)  # najpopularniejszy
    max_count = most_common[0][1]
    top_splits = [split for split, count in most_common if count == max_count]
    split = ", ".join(top_splits)
else:
    split = "brak"


# ---------------------------------------------------------------------
# SYNAFIA
# ---------------------------------------------------------------------

def create_synafia(df):
    # Group the DataFrame by line number to process each line separately
    grouped = df.groupby("Line number")

    # Initialize an empty list to store rows for synafia_test
    synafia_rows = []

    # Iterate through each group (each line)
    for line_number, group in grouped:
        # Tylko przetwarzaj wers, jeśli kolumna "wykluczenie" ma wartość False
        if group["wykluczenie"].iloc[0] == False:
            # Get the Stressrank values for each syllable in the line
            stressrank_values = group["Stressrank"].tolist()
            # Append the Stressrank values as a single row
            synafia_rows.append(stressrank_values)

    # Find the maximum number of syllables in any line to pad shorter lines
    max_syllables = max(len(row) for row in synafia_rows)

    # Pad all rows with zeros to make them of equal length
    padded_rows = [row + [0] * (max_syllables - len(row)) for row in synafia_rows]

    # Create a DataFrame from the padded rows
    synafia_test = pd.DataFrame(padded_rows)

    # Adjust column labels to start from 1
    synafia_test.columns = range(1, synafia_test.shape[1] + 1)

    # Add an additional row to sum the stressrank values for each syllable position
    synafia_test.loc["Sum"] = synafia_test.sum()

    return synafia_test

# Use the function to create synafia_test
synafia_test = create_synafia(df)


# SYNAFIA: METRUM
from numpy import mean

sums = synafia_test.loc["Sum"]
szczyt = sums.max()
niz    = sums.min()

oba = [szczyt, niz]
srednia = int(mean(oba))

def trochej(synafia_test: pd.DataFrame):
    n_cols = len(sums)
    # wzorzec: [szczyt, niz, szczyt, niz, ...] przycięty do n_cols
    pattern = ([srednia, niz] * ((n_cols // 2) + 1))[:n_cols]
    
    # drugi wiersz: oryginalne sumy
    sums_list = sums.tolist()
    # trzeci wiersz: różnice
    diff = [abs(s - p) for s, p in zip(sums_list, pattern)]
    
    # składamy wynikową tabelę
    tabela = pd.DataFrame(
        [pattern, sums_list, diff],
        index=["wzorzec", "sumy", "różnica"],
        columns=range(1, n_cols + 1)
    )
    
    finalny_wynik = sum(diff)
    return tabela, finalny_wynik

def jamb(synafia_test: pd.DataFrame):
    n_cols = len(sums)
    # wzorzec: [szczyt, niz, szczyt, niz, ...] przycięty do n_cols
    pattern = ([niz, srednia] * ((n_cols // 2) + 1))[:n_cols]
    
    # drugi wiersz: oryginalne sumy
    sums_list = sums.tolist()
    # trzeci wiersz: różnice
    diff = [abs(s - p) for s, p in zip(sums_list, pattern)]
    
    # składamy wynikową tabelę
    tabela = pd.DataFrame(
        [pattern, sums_list, diff],
        index=["wzorzec", "sumy", "różnica"],
        columns=range(1, n_cols + 1)
    )
    
    finalny_wynik = sum(diff)
    return tabela, finalny_wynik

def amfibrach(synafia_test: pd.DataFrame):
    n_cols = len(sums)
    # wzorzec: [szczyt, niz, szczyt, niz, ...] przycięty do n_cols
    pattern = ([niz, srednia, niz] * ((n_cols // 2) + 1))[:n_cols]
    
    # drugi wiersz: oryginalne sumy
    sums_list = sums.tolist()
    # trzeci wiersz: różnice
    diff = [abs(s - p) for s, p in zip(sums_list, pattern)]
    
    # składamy wynikową tabelę
    tabela = pd.DataFrame(
        [pattern, sums_list, diff],
        index=["wzorzec", "sumy", "różnica"],
        columns=range(1, n_cols + 1)
    )
    
    finalny_wynik = sum(diff)
    return tabela, finalny_wynik

def daktyl(synafia_test: pd.DataFrame):
    
    n_cols = len(sums)
    # wzorzec: [szczyt, niz, szczyt, niz, ...] przycięty do n_cols
    pattern = ([srednia, niz, niz] * ((n_cols // 2) + 1))[:n_cols]
    
    # drugi wiersz: oryginalne sumy
    sums_list = sums.tolist()
    # trzeci wiersz: absolutne różnice
    diff = [abs(s - p) for s, p in zip(sums_list, pattern)]
    
    # składamy wynikową tabelę
    tabela = pd.DataFrame(
        [pattern, sums_list, diff],
        index=["wzorzec", "sumy", "absolutna różnica"],
        columns=range(1, n_cols + 1)
    )
    
    finalny_wynik = sum(diff)
    return tabela, finalny_wynik

def niemetryczny(synafia_test: pd.DataFrame):
    
    n_cols = len(sums)
    # wzorzec: [szczyt, niz, szczyt, niz, ...] przycięty do n_cols
    pattern = ([srednia] * ((n_cols // 2) + 1))[:n_cols]
    
    # drugi wiersz: oryginalne sumy
    sums_list = sums.tolist()
    # trzeci wiersz: absolutne różnice
    diff = [abs(s - p) for s, p in zip(sums_list, pattern)]
    
    # składamy wynikową tabelę
    tabela = pd.DataFrame(
        [pattern, sums_list, diff],
        index=["wzorzec", "sumy", "absolutna różnica"],
        columns=range(1, n_cols + 1)
    )
    
    finalny_wynik = sum(diff)
    return tabela, finalny_wynik

# przykład użycia:
#tabela_trochej, wynik = jamb(synafia_test)
#print(tabela_trochej)
#print("Finalny wynik:", wynik)

funcs = [trochej, jamb, daktyl, amfibrach, niemetryczny]
results = [(f.__name__, f(synafia_test)[1]) for f in funcs]
sorted_results = sorted(results, key=lambda x: abs(x[1]))

# Najlepsze metrum
best = sorted_results[0][0]

# Lista wszystkich metrów od najbliższego 0, z wynikami w nawiasach
other = [f"{name}({res})" for name, res in sorted_results]

# SYNAFIA: PARAMETRY
# Oblicz liczbę sylab w każdej linii bez wykluczenia
line_syll = df[df['wykluczenie'] == False].groupby('Line number').size()

# Najczęstsza liczba sylab
mode_syll = line_syll.mode().iloc[0]

# Warunek: odchylenia maks. 1 od mody
if best != "niemetryczny":
    rodzaj = 'sylabotoniczny'
elif (line_syll.subtract(mode_syll).abs() == 0).all():
    rodzaj = 'izosylabiczny'
elif (line_syll.subtract(mode_syll).abs() <= 1).all():
    rodzaj = 'sylabiczny względny'
else:
    rodzaj = 'toniczny lub wolny'

# Ustal zgłoskowiec
zgłoskowiec = mode_syll if rodzaj in ['izosylabiczny', 'sylabiczny względny', 'sylabotoniczny'] else None

# ------------------------------------------------------------------------
# UZUPEŁNIAMY SYNAFIĘ
# ------------------------------------------------------------------------
# Funkcja zwracająca wzorzec na podstawie nazwy funkcji
binary_feet = {
    'trochej':    [1, 0],      # S-n
    'jamb':       [0, 1],      # n-S
    'amfibrach':  [0, 1, 0],   # n-S-n
    'daktyl':     [1, 0, 0],   # S-n-n
    # w niemetrycznym po prostu same “0” (nieregularne)
    'niemetryczny': None
}

foot = binary_feet.get(best)
if foot is None:
    # dla “niemetrycznego” metrum ustawiamy zawsze 0
    df['synafia'] = 0
else:
    # wyzeruj kolumnę
    df['synafia'] = 0

    # 2. Dla każdej linii powtórz stopę aż do liczby sylab
    for line_no, group in df.groupby('Line number'):
        n_syl = len(group)
        # rozwiń wzorzec dokładnie do n_syl
        pattern_line = (foot * ((n_syl // len(foot)) + 1))[:n_syl]
        # przypisz po kolei 1/0 do tych wierszy
        df.loc[group.index, 'synafia'] = pattern_line

# ------------------------------------------------------------------------
# ŁADNA TABLEKA
# ------------------------------------------------------------------------

wyniki_rows = []

# grupujemy po numerze linii
for line_number, group in df.groupby('Line number'):
    # wyrzuć grupę do list
    sylaby       = group['Syllable'].tolist()
    stressy      = group['Stressrank'].astype(int).tolist()
    synafie      = group['synafia'].astype(int).tolist()
    wykluczenia  = group['wykluczenie'].astype(bool).tolist() # Ensure boolean
    max_cols     = len(sylaby)
    excluded     = any(wykluczenia)

    # obliczamy symbole według reguł
    symbole = []
    for s, r in zip(synafie, stressy):
        suma = s + r
        if suma >= 3:
            symbole.append("&")
        elif r == 2 and s == 0 and rodzaj == 'sylabotoniczny':
            symbole.append("–")
        elif r == 2:
            symbole.append("^")
        elif s == 1 and r == 1:
            symbole.append("&")
        elif s == 0 and r == 1:
            symbole.append("–")
        elif s == 1 and r == 0:
            symbole.append("$")
        else:
            symbole.append("–") # Using hyphen-minus, ensure this is intended over an em-dash or other dash

    # funkcja do zbudowania słownika jednej “wierszowej” tabeli
    def make_row(row_type, data_list):
        row = {'Linijka': line_number, 'Type': row_type}
        for idx, val in enumerate(data_list, start=1):
            row[f'{idx}'] = val
        for idx in range(len(data_list)+1, max_cols+1): # Pad with empty strings
            row[f'{idx}'] = ''
        row['excluded'] = excluded
        return row

    # dodajemy cztery wiersze:
    wyniki_rows.append(make_row('symbol',  symbole))
    wyniki_rows.append(make_row('sylaba',  sylaby))
    wyniki_rows.append(make_row('stress',  list(map(str, stressy))))
    wyniki_rows.append(make_row('synafia', list(map(str, synafie))))

# tworzymy finalny DataFrame
wyniki_df = pd.DataFrame(wyniki_rows)


# WZÓR METRYCZNY
# Ensure synafia_test is a DataFrame and has "Sum" in its index if loc["Sum"] is used
# Example synafia_test (replace with your actual data)
# synafia_test_data = {'col1': [1,2,3], 'col2': [4,5,6]}
# synafia_test_index = ["Val1", "Val2", "Sum"]
# synafia_test = pd.DataFrame(synafia_test_data, index=synafia_test_index)


def wypisz_metryczny_wzor(best_metrum: str, synafia_test_df: pd.DataFrame) -> str:
    # This is a placeholder for n_cols if synafia_test_df is not structured as expected
    # or if 'Sum' is not in its index. Adjust as necessary.
    n_cols = 0
    if "Sum" in synafia_test_df.index:
        n_cols = len(synafia_test_df.loc["Sum"])
    elif not synafia_test_df.empty: # Fallback if "Sum" row isn't present but df has columns
        n_cols = synafia_test_df.shape[1]
    
    if n_cols == 0: # If n_cols couldn't be determined, provide a default or handle error
        return "Nie można wygenerować wzorca (brak kolumn)"

    # Ensure szczyt, niz, srednia are defined in a scope accessible here
    # These are example values, they should be defined based on your script's logic
    global szczyt, niz, srednia # If they are global variables
    # szczyt = 1
    # niz = 0
    # srednia = 0.5

    pattern_map = {
        "trochej":      ([szczyt, niz] * ((n_cols // 2) + 1))[:n_cols],
        "jamb":         ([niz, szczyt] * ((n_cols // 2) + 1))[:n_cols],
        "amfibrach":    ([niz, szczyt, niz] * ((n_cols // 3) + 1))[:n_cols],
        "daktyl":       ([szczyt, niz, niz] * ((n_cols // 3) + 1))[:n_cols],
        "niemetryczny": ([srednia] * n_cols),
    }

    if best_metrum not in pattern_map:
        return f"Nieznane metrum: {best_metrum}"
        
    pattern = pattern_map[best_metrum]

    symboliczny_wzor = ["&" if val == szczyt else "–" for val in pattern]
    wynik_string = " ".join(symboliczny_wzor)
    return wynik_string

# Przykład użycia:
# Ensure 'best' and 'synafia_test' are defined before this call
# best = "trochej" # example
wzorzec_tekstowy = wypisz_metryczny_wzor(best, synafia_test)


print(f"###RODZAJ:{rodzaj}")
print(f"###ZGLOSKOWIEC:{zgłoskowiec}")
print(f"###ŚREDNIÓWKA:{split}")
print(f"###METRUM:{best}")
print(f"###WZORZEC_METRYCZNY:{wzorzec_tekstowy}") # MODIFIED: Print the pattern
print(f"###INNEMETRA:{other}")
print(f"###SZCZYT:{szczyt}") # This 'szczyt' is the numeric value used in pattern generation

print(wyniki_df.to_csv(index=False, lineterminator='\n')) # Ensure consistent line endings