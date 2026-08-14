#!/bin/sh

TARGET="${1:-https://ostara.work}"
REQUESTS="${2:-100}"

echo "Klasker Scanner benchmark"
echo "Target:    $TARGET"
echo "Requests:  $REQUESTS"
echo "Started:   $(date)"
echo

START=$(date +%s)

i=1
while [ "$i" -le "$REQUESTS" ]; do
    /usr/local/bin/python3 src/scanner.py "$TARGET" \
        > "bench/result_${i}.json" \
        2> "bench/error_${i}.log"

    i=$((i + 1))
done

END=$(date +%s)
ELAPSED=$((END - START))

echo
echo "Finished:  $(date)"
echo "Elapsed:   ${ELAPSED}s"

if [ "$ELAPSED" -gt 0 ]; then
    echo "Requests/s: $((REQUESTS / ELAPSED))"
fi
