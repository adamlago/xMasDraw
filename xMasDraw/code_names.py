#!/usr/bin/env python3
"""
Assign unique random IDs (1..N) to names and save to CSV.

Defaults:
  - input: names.txt (one name per line)
  - output: id_names.csv
  - header: id,name   (id is first column)
  - output order: same as input order
  - randomness: non-reproducible by default (uses OS entropy). Pass --seed to reproduce.

Usage examples:
  python assign_ids.py
  python assign_ids.py --input mynames.txt --output id_names.csv
  python assign_ids.py --seed 42    # reproducible
"""

import argparse
import csv
import random
import sys

def read_names(path):
    names = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            name = line.strip()
            if name:
                names.append(name)
    return names

def write_csv(path, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'name'])
        writer.writerows(rows)

def main():
    parser = argparse.ArgumentParser(description="Assign unique random IDs (1..N) to names and write CSV with header 'id,name'.")
    parser.add_argument('--input', '-i', default='names.txt', help='Input text file with one name per line (default: names.txt)')
    parser.add_argument('--output', '-o', default='id_names.csv', help='Output CSV file (default: id_names.csv)')
    parser.add_argument('--seed', type=int, default=None, help='Optional integer seed for reproducible output (if omitted: non-reproducible)')
    args = parser.parse_args()

    try:
        names = read_names(args.input)
    except FileNotFoundError:
        print(f"Error: input file '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)

    if not names:
        print("Error: no names found in the input file.", file=sys.stderr)
        sys.exit(1)

    n = len(names)

    # Default: non-reproducible RNG using OS entropy (SystemRandom).
    rng = random.SystemRandom() if args.seed is None else random.Random(args.seed)

    # Generate a random permutation of 1..N (unique ids) and pair with names in input order
    ids = rng.sample(range(1, n + 1), k=n)
    rows = [(i, name) for i, name in zip(ids, names)]

    write_csv(args.output, rows)
    print(f"Wrote {len(rows)} rows to {args.output} (unique ids 1..{n}, seed={'None' if args.seed is None else args.seed})")

if __name__ == '__main__':
    main()
