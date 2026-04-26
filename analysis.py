# -*- coding: utf-8 -*-
import pandas as pd
import random
import pyphen
from kokosznicka import Kokosznicka
from araxne import Araxne
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
            dirty = Kokosznicka.hyphenate(word)
            clean = czyszczenie(dirty, zmiany)
            syllables = clean.split('-')  # Podziel słowo na sylaby
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
    df['wykluczenie'] = 0
    df['zestrój'] = 0
    df['człon'] = 0
    df['kolor'] = 0

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
    ' z ': ' z~', 'Z ': 'Z~', ' k ': ' k~', '—': '', '–': '', 'ň': 'n',
    'CZ': 'Cz', 'SZ': 'Sz', 'DZ': 'Dz', 'RZ': 'Rz', 'CH': 'Ch',
    'DŻ': 'Dż', 'DŹ': 'Dź', 'DZI': 'Dzi', '„': '', '“': ''
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
#for line_num, group in df.groupby("Line number"):
#    df.loc[df["Line number"] == line_num, "wykluczenie"] = False

# ------------------------------------------------------------------
# ANTY-EPITROCHAZM
# ------------------------------------------------------------------
atona = {'się', 'bym', 'byś', 'by', 'i', 'a', 'o'}

for line in df['Line number'].unique():
    # Wydzielanie syalb z obecnego wersu i resetowanie indeksu
    line_df = df[df['Line number'] == line].reset_index()

    # Przechodzenie przez sylaby w wersie.
    for i, row in line_df.iterrows():
        # Przetwarzanie tylko wtedy, kiedy nie są w atonach.
        if row['Syllablecount'] == 1 and row['Word'].lower() not in atona:
            # Ładowanie obecnej cioężkości
            new_stressrank = int(row['Stressrank'])

            # Deklarowanie poprzednich i następnych wartości
            prev_stress = None
            next_stress = None

            # Jeśli to nie jest pierwsza sylaba w wersie, załaduj ciężkość poprzedniej
            if i > 0:
                prev_stress = int(line_df.loc[i - 1, 'Stressrank'])
            # Jeśli to nie jest ostatnia sylaba w wersie, załaduj ciężkość następnej
            if i < len(line_df) - 1:
                next_stress = int(line_df.loc[i + 1, 'Stressrank'])

            # Zasada dla pierwszych sylab w wersie
            if i == 0 and next_stress is not None:
                if next_stress == 3:
                    new_stressrank -= 1
                elif next_stress == 0:
                    new_stressrank += 1

            # Zasady dla sylab z sąsiadującymi sylabami z obu stron.
            if prev_stress is not None and next_stress is not None:
                # Obniż o 1, jeśli sąsiadujące mają ciężkość 2 lub wyższą.
                if prev_stress >= 2 and next_stress >= 2:
                    new_stressrank -= 1
                # Obniż o 1, jeśli poprzednia ma ciężkość 0, a następna 2 lub więcej.
                if prev_stress == 0 and next_stress >= 2:
                    new_stressrank -= 1
                # Podbij o 1, jeśli poprzednia ma ciężkość 2 lub więcej, a następna 0.
                if prev_stress >= 2 and next_stress == 0:
                    new_stressrank -= 1
                # Podbij o 1, jeśli obie sylaby sąsiadujące mają ciężkość 0.
                if prev_stress == 0 and next_stress == 0:
                    new_stressrank += 1

            # Aktualizacja oryginalnego df'a.
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
# not propar and not oksytona_prefiksowane and word.lower() in oksytona and [TEN WERS PSUJE WSZYSTKO]
                if df.at[first_idx, 'Stressrank'] < 2:
                    df.at[first_idx, 'Stressrank'] = 2
                else:
                    df.at[second_idx, 'Stressrank'] = 0
                    

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

# Utworzenie identyfikatora porządku słowa w linii
# Flaga nowego słowa
df['is_new_word'] = (df['Line number'] != df['Line number'].shift()) | (df['Word'] != df['Word'].shift())
# Numer słowa w obrębie tekstu (globalnie), przyda się do grupowania
df['WordIdx'] = df['is_new_word'].cumsum()

# Mapowanie poprzedzającego słowa z tej samej linii
# Tworzenie słownika
prev_word = {}
# Grupowanie wg linii, aby ustalić peryferia słowo
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

# Wybieramy słowa o 4+ sylabach, dla których zestrój == 0
# Lista WordIdx spełniających warunek
long_zero = []
for widx, group in df.groupby('WordIdx'):
    if group['Syllablecount'].iloc[0] >= 4 and (group['zestrój'] == 0).all():
        long_zero.append(widx)

for widx in long_zero:
    group = df[df['WordIdx'] == widx]
    # Indeksy w oryginalnym df
    idxs = group.index.tolist()
    # Pierwsza sylaba od początku: Syllable Position == Syllablecount
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

df_valid = df.copy()

# Numerowanie w każdej oryginalnej linii od 1
df_valid['syll_line_idx'] = df_valid.groupby('Line number').cumcount() + 1

# Zbieranie par sylab, między którymi jest podział między słowami
line_splits = {}
all_splits = []

for line_num, group in df_valid.groupby('Line number'):
    splits = []
    line_length = len(group)
    # Iterujemy po kolejnych sylabach w danej linii
    for i in range(len(group) - 1):
        curr = group.iloc[i]
        nxt  = group.iloc[i + 1]
        # jeśli sylaby należą do różnych słów, robimy podział
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
    most_common = counter.most_common(4)  # najpopularniejsze 4
    max_count = most_common[0][1]
    top_splits = [split for split, count in most_common if count == max_count]
    split = ", ".join(top_splits)
else:
    split = "brak"

# Teraz wybieramy najbardziej "wypośrodkowany" z najczęstszych
best = []

for it in top_splits:
  tabl = it.split("+")
  diff = abs(int(tabl[0]) - int(tabl[-1]))
  resu = (it, diff)
  best.append(resu)

win = ('0+0', line_length)

for i in best:
  if i[1] <= win[1]:
    win = i

winner = win[0]

# ---------------------------------------------------------------------
# SYNAFIA
# ---------------------------------------------------------------------

def create_synafia(df):
    # Grupujedy dataframe'a wg numeru wersu
    grouped = df.groupby("Line number")

    # Pusta lista na wiersze późniejszej tabeli synafia_test
    synafia_rows = []

    # Iterujemy przez każdą grupę (każdy wers)
    for line_number, group in grouped:
            # Bierzemy ciężkośc dla każdej sylaby
        stressrank_values = group["Stressrank"].tolist()
            # Dodajemy ciężkości do jednego wiersza
        synafia_rows.append(stressrank_values)

    # Wynajdujemy maksymalną długość wersu, aby wypełnić krótsze
    max_syllables = max(len(row) for row in synafia_rows)

    # Wypełniamy krótsze zerami
    padded_rows = [row + [0] * (max_syllables - len(row)) for row in synafia_rows]

    # I tworzymy z tego df'a
    synafia_test = pd.DataFrame(padded_rows)

    # Zmieniamy indeksowanie kolumn od 1
    synafia_test.columns = range(1, synafia_test.shape[1] + 1)

    # Dodaktowy wiersz na końcu do sumowania powyższych ciężkości
    synafia_test.loc["Sum"] = synafia_test.sum()

    return synafia_test

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


funcs = [trochej, jamb, daktyl, amfibrach, niemetryczny]
results = [(f.__name__, f(synafia_test)[1]) for f in funcs]
sorted_results = sorted(results, key=lambda x: abs(x[1]))

# Najlepsze metrum
best = sorted_results[0][0]

# Lista wszystkich metrów od najbliższego 0, z wynikami w nawiasach
other = [f"{name}({res})" for name, res in sorted_results]

# SYNAFIA: PARAMETRY
# Oblicz liczbę sylab w każdej linii
line_syll = df.groupby('Line number').size()

# Najczęstsza liczba sylab
mode_syll = line_syll.mode().iloc[0]

# Ustalamy rodzaj opierając się na metrach i odchyleniu od najczęstszej liczby sylab
if best != "niemetryczny":
    rodzaj = 'sylabotoniczny'
elif (line_syll.subtract(mode_syll).abs() == 0).all():
    rodzaj = 'izosylabiczny'
elif (line_syll.subtract(mode_syll).abs() <= 1).all():
    rodzaj = 'sylabiczny względny'
else:
    rodzaj = 'zróżnicowany, toniczny lub wolny'

# Ustal zgłoskowiec
zgłoskowiec = mode_syll if rodzaj in ['izosylabiczny', 'sylabiczny względny', 'sylabotoniczny'] else None

# ------------------------------------------------------------------------
# UZUPEŁNIAMY SYNAFIĘ
# ------------------------------------------------------------------------
# Funkcja zwracająca wzorzec na podstawie nazwy funkcji
binary_feet = {
    'trochej':    [1, 0],
    'jamb':       [0, 1],
    'amfibrach':  [0, 1, 0],
    'daktyl':     [1, 0, 0],
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

    # Dla każdej linii powtórz stopę aż do liczby sylab
    for line_no, group in df.groupby('Line number'):
        n_syl = len(group)
        # rozwiń wzorzec dokładnie do n_syl
        pattern_line = (foot * ((n_syl // len(foot)) + 1))[:n_syl]
        # przypisz po kolei 1/0 do tych wierszy
        df.loc[group.index, 'synafia'] = pattern_line

# ------------------------------------------------------------------------
# ARAXNE
# ------------------------------------------------------------------------
import random


def generate_hex_code():
    """Generates a random 6-character hex color code."""
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

def color_similar_last_words(df):
    """
    Assigns independent random colors to last words, then iterates forward.
    If a future word matches, it inherits the current word's color.
    """
    # Wybieramy ostatnie słowo i przyporządkujemy losowy kolor
    lines_info = []
    
    for line_num in df['Line number'].unique():
        line_indices = df[df['Line number'] == line_num].index
        last_word = df.loc[line_indices[-1], 'Word']
        
        last_word_idxs = []
        for idx in reversed(line_indices):
            if df.loc[idx, 'Word'] == last_word:
                last_word_idxs.insert(0, idx)
            else:
                break
                
        lines_info.append({
            'line_num': line_num,
            'word': last_word,
            'indices': last_word_idxs,
            'color': "#FFFFFF"
        })

    # Iterujemy do przodu, szukamy rymów
    for i in range(len(lines_info)):
        word1_info = lines_info[i]
        
        # Patrzymy max 4 wersy do przodu
        for j in range(i + 1, min(i + 5, len(lines_info))):
            word2_info = lines_info[j]
            
            score = Araxne.compare(word1_info['word'], word2_info['word'])
            
            # 75% zgodności wg Araxne – uznajemy za rym
            if score > 75.00:
                if word1_info['color'] == '#FFFFFF':
                    word1_info['color'] = generate_hex_code()
                # Nadpisujemy kolor, dzięki czemu możemy zrobić łańcuch rymów
                word2_info['color'] = word1_info['color']
                
                break

    # Wpisujemy kolory do df'a
    for info in lines_info:
        df.loc[info['indices'], 'kolor'] = info['color']
        
    return df

df = color_similar_last_words(df)

# ------------------------------------------------------------------------
# ŁADNA TABLEKA
# ------------------------------------------------------------------------

wyniki_rows = []

# grupujemy po numerze linii
for line_number, group in df.groupby('Line number'):
    # wyrzuamy grupę do list
    sylaby       = group['Syllable'].tolist()
    stressy      = group['Stressrank'].astype(int).tolist()
    synafie      = group['synafia'].astype(int).tolist()
    wykluczenia  = group['wykluczenie'].tolist() 
    max_cols     = len(sylaby)
    excluded     = any(wykluczenia)
    line_color = group['kolor'].iloc[-1]

    # obliczamy symbole według reguł (na tym etapie zamienione, bo jest problem z kodowaniem)
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
            symbole.append("–")

    # funkcja do zbudowania słownika jednej “wierszowej” tabeli
    def make_row(row_type, data_list):
        row = {'Linijka': line_number, 'Type': row_type}
        for idx, val in enumerate(data_list, start=1):
            row[f'{idx}'] = val
        for idx in range(len(data_list)+1, max_cols+1): # Pad with empty strings
            row[f'{idx}'] = ''
        row['excluded'] = excluded
        row['kolor'] = line_color
        return row

    # dodajemy cztery wiersze:
    wyniki_rows.append(make_row('symbol',  symbole))
    wyniki_rows.append(make_row('sylaba',  sylaby))
    wyniki_rows.append(make_row('stress',  list(map(str, stressy))))
    wyniki_rows.append(make_row('synafia', list(map(str, synafie))))

# tworzymy finalny DataFrame
wyniki_df = pd.DataFrame(wyniki_rows)


def wypisz_metryczny_wzor(best_metrum: str, synafia_test_df: pd.DataFrame) -> str:
    n_cols = 0
    if "Sum" in synafia_test_df.index:
        n_cols = len(synafia_test_df.loc["Sum"])
    elif not synafia_test_df.empty:
        n_cols = synafia_test_df.shape[1]
    
    if n_cols == 0: # Jeśli nie uda się obliczyć n_cols
        return "Nie można wygenerować wzorca (brak kolumn)"

    # Upewniamy się, że szczyt, niz i srednia będą dostępne globalnie
    global szczyt, niz, srednia

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

wzorzec_tekstowy = wypisz_metryczny_wzor(best, synafia_test)

print(f"###RODZAJ:{rodzaj}")
print(f"###ZGLOSKOWIEC:{zgłoskowiec}")
print(f"###ŚREDNIÓWKA:{winner}")
print(f"###METRUM:{best}")
print(f"###WZORZEC_METRYCZNY:{wzorzec_tekstowy}")
print(f"###INNEMETRA:{other}")
print(f"###SZCZYT:{szczyt}")

print(wyniki_df.to_csv(index=False, lineterminator='\n'))