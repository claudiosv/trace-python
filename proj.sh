#!/bin/bash
#find $1 -maxdepth  1 -type d -print0 | while read -d '' -r dir; do
#    files=$(find "$dir" -iname "*test*.java" -type f | wc -l);
#    basename=$(basename "$dir")
#    printf "%s,%s,%d\n" "$basename" "$dir" "$files"
#done
#find $1 -maxdepth 2 -type d -print0 | while read -d '' -r dir; do
#    files=$(find "$dir" -iname "*test*.java" -type f | wc -l);
#    basename=$(basename "$dir")
#    printf "%s,%s,%d\n" "$basename" "$dir" "$files"
#done
#find $1 -mindepth 1 -maxdepth 1 -type d -print0 | while read -d '' -r dir; do
#    files=$(find "$dir" -name "dump-1.zip" -size +33c -type f | wc -l);
#    basename=$(basename "$dir")
#    printf "%s,%s,%d\n" "$basename" "$dir" "$files"
#done
find $1 -maxdepth  1 -type d -print0 | while read -d '' -r dir; do
    files=$(find "$dir" -iname "*test*.java" -type f | wc -l);
    basename=$(basename "$dir");
    test_cases_raw=$(find "$dir" -iname "*test*.java" -type f | xargs -I% grep -i -o @Test "%" | sort | uniq -c | sort -nr | awk '{s+=$1} END {print s}');#> ${basename}_counts.txt);
    #test_cases=$(cat ${basename}_counts.txt | awk '{s+=$1} END {print s}');
    #printf "Basename: %s\nDir: %s\nTest suites: %d\nTest cases:%d\n-----------\n" "$basename" "$dir" "$files" "$test_cases"
    printf "%s,%d,%d\n" "$basename" "$files" "$test_cases_raw"
done

