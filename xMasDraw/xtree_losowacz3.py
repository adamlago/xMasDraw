#!/usr/bin/env python3
# Written by ChatGPT (OpenAI Assistant)
# -*- coding: utf-8 -*-

"""
Combined ASCII tree + Secret Santa (losowacz) in one script.

This version:
- reads participants from a CSV with header (two columns). Header is NOT printed next to the trunk.
- prints the tree with participant names next to the trunk
- asks (Polish): "CZY WSZYSCY SĄ POD CHOINKĄ" (Tak/Nie)
  - If "Tak": counts down 5→0, performs draw in-process, writes output files
  - After files are ready, clears the screen and prints the tree again with ID pairs (giver_id -> receiver_id) next to the trunk
  - The ID pairs are shuffled before being placed next to the trunk
  - If "Nie": exits
Usage example:
  python tree_and_losowacz.py participants.csv --method sattolo --seed 42
"""
from __future__ import annotations
import argparse
import csv
from csv import Sniffer
import math
import os
import random
import sys
import time
from typing import List, Dict, Any, Optional

# ANSI helpers
ANSI = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "green": "\033[32m",
    "red": "\033[31m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "brown": "\033[38;5;94m",
    "bright_yellow": "\033[93m",
}

def colorize(s: str, name: str, use_color: bool) -> str:
    if not use_color:
        return s
    return f"{ANSI.get(name, '')}{s}{ANSI['reset']}"

def style_text(s: str, bold: bool, use_ansi: bool) -> str:
    if not use_ansi or not bold:
        return s
    return f"{ANSI['bold']}{s}{ANSI['reset']}"

def clear_screen():
    """Cross-platform terminal clear."""
    if os.name == "nt":
        os.system("cls")
    else:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

# -------------------------
# CSV reading (for both display and drawing)
# -------------------------
def parse_col_arg(arg: Optional[str]) -> Optional[Any]:
    if arg is None:
        return None
    if isinstance(arg, str) and arg.isdigit():
        return int(arg)
    return arg

def read_people_csv(filename: str, id_col=0, name_col=1) -> List[Dict[str,str]]:
    """Read people from CSV. id_col/name_col can be int indices or column names (strings)."""
    with open(filename, newline='', encoding='utf-8') as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            has_header = Sniffer().has_header(sample)
        except Exception:
            has_header = False

        people: List[Dict[str,str]] = []
        if has_header:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            def col_to_key(col):
                if isinstance(col, int):
                    if col < 0 or col >= len(fieldnames):
                        raise ValueError(f"Index kolumny ({col}) poza zakresem pól nagłówka.")
                    return fieldnames[col]
                return col
            id_key = col_to_key(id_col)
            name_key = col_to_key(name_col)
            for lineno, row in enumerate(reader, start=2):
                pid = (row.get(id_key) or "").strip()
                pname = (row.get(name_key) or "").strip()
                if not pid and not pname:
                    continue
                people.append({'id': pid, 'name': pname})
        else:
            reader = csv.reader(f)
            if not isinstance(id_col, int) or not isinstance(name_col, int):
                raise ValueError("Plik CSV bez nagłówka — id/name muszą być podane jako indeksy kolumn (0-based).")
            for lineno, row in enumerate(reader, start=1):
                if not row or all(not x.strip() for x in row):
                    continue
                if id_col >= len(row) or name_col >= len(row):
                    raise ValueError(f"Wiersz {lineno} ma za mało kolumn.")
                pid = row[id_col].strip()
                pname = row[name_col].strip()
                people.append({'id': pid, 'name': pname})
    return people

# -------------------------
# Tree rendering
# -------------------------
def make_tree_lines_with_name_columns(size: int,
                                     names: List[str],
                                     cols: int,
                                     ornament_rate: float,
                                     use_color: bool,
                                     bold_names: bool,
                                     sep_spaces: int,
                                     name_sep: str,
                                     seed: Optional[int] = None) -> List[str]:
    if seed is not None:
        random.seed(seed)

    foliage_width = 2 * size - 1
    trunk_width = max(1, size // 3)
    default_trunk_height = max(1, size // 4)
    name_rows = math.ceil(len(names) / cols) if names else 0
    trunk_height = max(default_trunk_height, name_rows)
    trunk_piece = colorize("█" * trunk_width, "brown", use_color)

    lines: List[str] = []
    star = colorize("*", "bright_yellow", use_color)
    left = (foliage_width - 1) // 2
    lines.append(" " * left + star + " " * sep_spaces)

    for i in range(size):
        width = 2 * i + 1
        row_elems: List[str] = []
        for _ in range(width):
            if random.random() < ornament_rate:
                ornament_char = random.choice(["o", "O", "@", "%", "0"])
                color = random.choice(["red", "yellow", "blue", "magenta"])
                row_elems.append(colorize(ornament_char, color, use_color))
            else:
                row_elems.append(colorize("^", "green", use_color))
        left = (foliage_width - width) // 2
        lines.append(" " * left + "".join(row_elems) + " " * sep_spaces)

    for tr in range(trunk_height):
        left = (foliage_width - trunk_width) // 2
        base = " " * left + trunk_piece + " " * sep_spaces
        start_idx = tr * cols
        row_names = names[start_idx:start_idx + cols]
        if row_names:
            styled_names = name_sep.join(style_text(n, bold_names, use_color) for n in row_names)
            base += styled_names
        lines.append(base)

    return lines

# -------------------------
# Secret Santa (losowacz) functions
# -------------------------
def sattolo_shuffle(items: List[Dict[str,str]]) -> List[Dict[str,str]]:
    items = items[:]
    n = len(items)
    for i in range(n-1, 0, -1):
        j = random.randrange(0, i)  # 0..i-1
        items[i], items[j] = items[j], items[i]
    return items

def rejection_derangement(items: List[Dict[str,str]]) -> List[Dict[str,str]]:
    n = len(items)
    if n <= 1:
        raise ValueError("Derangement niemożliwy dla n <= 1")
    original = items[:]
    while True:
        perm = items[:]
        random.shuffle(perm)
        if all(a['id'] != b['id'] for a, b in zip(original, perm)):
            return perm

def make_pairs(people: List[Dict[str,str]], method: str = 'sattolo') -> List[Dict[str,str]]:
    if len(people) <= 1:
        raise ValueError("Potrzebne co najmniej 2 osoby.")
    if method == 'sattolo':
        receivers = sattolo_shuffle(people)
    elif method == 'rejection':
        receivers = rejection_derangement(people)
    else:
        raise ValueError("Nieznana metoda. Użyj 'sattolo' lub 'rejection'.")
    pairs: List[Dict[str,str]] = []
    for giver, receiver in zip(people, receivers):
        if giver['id'] == receiver['id']:
            raise RuntimeError("Wylosowano osobę dającą sobie prezent — algorytm zawiódł.")
        pairs.append({
            'giver_id': giver['id'],
            'giver_name': giver['name'],
            'receiver_id': receiver['id'],
            'receiver_name': receiver['name']
        })
    return pairs

def write_full_csv(pairs: List[Dict[str,str]], filename: str) -> None:
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['giver_id','giver_name','receiver_id','receiver_name'])
        writer.writeheader()
        for p in pairs:
            writer.writerow(p)

def write_ids_csv(pairs: List[Dict[str,str]], filename: str) -> None:
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['giver_id','receiver_id'])
        for p in pairs:
            writer.writerow([p['giver_id'], p['receiver_id']])

# -------------------------
# UI helpers
# -------------------------
def prompt_yes_no(prompt: str) -> bool:
    """Ask user a yes/no question in Polish; return True for Tak, False for Nie."""
    while True:
        try:
            ans = input(prompt + " (Tak/Nie): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        if not ans:
            continue
        if ans in ("tak", "t", "yes", "y", "1"):
            return True
        if ans in ("nie", "n", "no", "0"):
            return False
        print("Proszę wpisać 'Tak' lub 'Nie'.")

def countdown(seconds: int):
    """Countdown showing each number on its own line."""
    print("LOSOWANIE ZA:")
    for s in range(seconds, -1, -1):
        print(s)
        time.sleep(1)

# -------------------------
# Main combined program
# -------------------------
def main(argv):
    parser = argparse.ArgumentParser(description="ASCII tree + embedded losowacz (Secret Santa).")
    # Tree/display options
    parser.add_argument("input", help="Input CSV with header (two columns). Header will not be printed.")
    parser.add_argument("--size", type=int, default=8, help="Tree foliage rows (default 8)")
    parser.add_argument("--ornament-rate", type=float, default=0.12, help="Probability for ornaments (0-1)")
    parser.add_argument("--cols", type=int, default=2, help="Names per trunk row (default 2)")
    parser.add_argument("--name-sep", type=str, default="  ", help="Separator between names on same row")
    parser.add_argument("--sep", type=int, default=3, help="Spaces between trunk and names (default 3)")
    parser.add_argument("--delay", type=float, default=0.0, help="Seconds to wait after printing each line (default 0.0)")
    parser.add_argument("--clear", type=str, choices=["each", "start", "none"], default="start",
                        help="When to clear screen: each/start/none (default start)")
    parser.add_argument("--no-color", dest="color", action="store_false", help="Disable ANSI colors (also disables bold if requested)")
    parser.add_argument("--no-bold", dest="bold", action="store_false", help="Disable bolding of names")
    parser.add_argument("--show-id", action="store_true", help="Show 'id - name' when printing names next to the trunk")
    # Losowacz options
    parser.add_argument("-f", "--full-out", default="pairs_full.csv", help="Full output filename (default pairs_full.csv)")
    parser.add_argument("-n", "--nums-out", default="pairs_ids.csv", help="IDs-only output filename (default pairs_ids.csv)")
    parser.add_argument("--id-col", default="0", help="ID column (index 0-based or header name). Default 0.")
    parser.add_argument("--name-col", default="1", help="Name column (index 0-based or header name). Default 1.")
    parser.add_argument("-m", "--method", choices=['sattolo','rejection'], default='sattolo', help="Drawing method (default sattolo)")
    parser.add_argument("--seed", type=int, help="Random seed (optional, will affect both display ornaments and drawing if provided)")
    args = parser.parse_args(argv)

    # Seed affects both tree ornaments and the draw
    if args.seed is not None:
        random.seed(args.seed)

    # Read participants from CSV (this will skip the header automatically)
    id_col = parse_col_arg(args.id_col)
    name_col = parse_col_arg(args.name_col)
    try:
        people_for_draw = read_people_csv(args.input, id_col=id_col, name_col=name_col)
    except Exception as e:
        print("Błąd przy wczytywaniu pliku CSV:", e, file=sys.stderr)
        # Fallback: try to read raw lines for display only (but drawing will fail later)
        people_for_draw = []

    # Build names for initial display from parsed people (this excludes the header)
    names_for_display: List[str] = []
    if people_for_draw:
        for p in people_for_draw:
            if args.show_id:
                names_for_display.append(f"{p['id']} - {p['name']}")
            else:
                names_for_display.append(p['name'])
    else:
        # If CSV reading failed, fallback to showing raw file lines (tolerant parsing)
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                raw_lines = f.readlines()
        except Exception:
            raw_lines = []
        # simple tolerant parsing (do not treat first line specially here)
        for raw in raw_lines:
            line = raw.strip()
            if not line:
                continue
            # try to split common formats
            if ',' in line:
                parts = [p.strip() for p in line.split(',', 1)]
                if len(parts) >= 2:
                    idp, namep = parts[0], parts[1]
                    names_for_display.append(f"{idp} - {namep}" if args.show_id else namep)
                    continue
            if '\t' in line:
                parts = [p.strip() for p in line.split('\t', 1)]
                if len(parts) >= 2:
                    idp, namep = parts[0], parts[1]
                    names_for_display.append(f"{idp} - {namep}" if args.show_id else namep)
                    continue
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                idp, namep = parts[0].strip(), parts[1].strip()
                names_for_display.append(f"{idp} - {namep}" if args.show_id else namep)
                continue
            names_for_display.append(line)

    # Render and display initial tree with participant names
    size = max(3, min(60, args.size))
    ornament_rate = max(0.0, min(1.0, args.ornament_rate))
    cols = max(1, args.cols)
    sep_spaces = max(1, args.sep)
    delay = max(0.0, args.delay)
    clear_mode = args.clear

    tree_lines = make_tree_lines_with_name_columns(size=size,
                                                  names=names_for_display,
                                                  cols=cols,
                                                  ornament_rate=ornament_rate,
                                                  use_color=args.color,
                                                  bold_names=args.bold,
                                                  sep_spaces=sep_spaces,
                                                  name_sep=args.name_sep,
                                                  seed=args.seed)

    if clear_mode == "start":
        clear_screen()

    for ln in tree_lines:
        if clear_mode == "each":
            clear_screen()
        print(ln, flush=True)
        if delay:
            time.sleep(delay)

    # After printing tree, prompt user in Polish
    all_under_tree = prompt_yes_no("CZY WSZYSCY SĄ POD CHOINKĄ")
    if not all_under_tree:
        print("Program zakończony (Nie wybrano losowania).")
        return

    # If Tak: countdown then perform the draw in-process
    countdown(5)

    # Ensure we have valid people_for_draw for the actual drawing
    if not people_for_draw:
        try:
            people_for_draw = read_people_csv(args.input, id_col=id_col, name_col=name_col)
        except Exception as e:
            print("Błąd przy wczytywaniu pliku CSV (ponownie):", e, file=sys.stderr)
            sys.exit(1)

    if len(people_for_draw) < 2:
        print("Musisz podać co najmniej 2 osoby.", file=sys.stderr)
        sys.exit(1)

    # Reseed before actual draw if seed was provided (for reproducibility)
    if args.seed is not None:
        random.seed(args.seed)

    try:
        pairs = make_pairs(people_for_draw, method=args.method)
    except Exception as e:
        print("Błąd podczas losowania:", e, file=sys.stderr)
        sys.exit(1)

    # Write output files
    try:
        write_full_csv(pairs, args.full_out)
        write_ids_csv(pairs, args.nums_out)
        print(f"Wyniki zapisane do:\n - pełny: {args.full_out}\n - tylko numery: {args.nums_out}")
    except Exception as e:
        print("Błąd przy zapisie plików:", e, file=sys.stderr)
        sys.exit(1)

    # After files are ready: prepare ID pair strings for display, shuffle them, and print the tree again
    pair_strings: List[str] = []
    for p in pairs:
        giver = p.get('giver_id', '') or p.get('giver_name', '')
        receiver = p.get('receiver_id', '') or p.get('receiver_name', '')
        pair_strings.append(f"{giver} -> {receiver}")

    # Shuffle the pair strings before final display
    random.shuffle(pair_strings)

    # Render final tree lines with shuffled ID pairs next to trunk
    final_tree_lines = make_tree_lines_with_name_columns(size=size,
                                                        names=pair_strings,
                                                        cols=cols,
                                                        ornament_rate=ornament_rate,
                                                        use_color=args.color,
                                                        bold_names=args.bold,
                                                        sep_spaces=sep_spaces,
                                                        name_sep=args.name_sep,
                                                        seed=args.seed)

    # Clear screen once before final display to show results clearly
    clear_screen()
    # Optional header
    print("WYNIKI LOSOWANIA (ID pary obok pnia, kolejność losowa):\n")
    for ln in final_tree_lines:
        print(ln, flush=True)
        if delay:
            time.sleep(delay)

if __name__ == "__main__":
    main(sys.argv[1:])
