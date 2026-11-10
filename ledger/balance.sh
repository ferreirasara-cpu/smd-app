#!/usr/bin/env bash
set -euo pipefail
# Prints the balance of each account in a transactions CSV.
file="${LEDGER_FILE:-data/transactions.csv}"
echo "Balances in $file"
awk -F, 'NR > 1 { s[$2] += $5 } END { for (a in s) printf "%-10s %10.2f\n", a, s[a] }' "$file" | sort
