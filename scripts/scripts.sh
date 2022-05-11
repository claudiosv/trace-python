#!/bin/bash

delete_paths() {
    find "$1" -name classpath_X4PmlaxV -or -name paths_X4PmlaxV -or -name paths_X4PmlaxV_find -or -name paths_X4PmlaxV_strace -type f -print0 | xargs -0 rm
}

find_instrumented_dumps_exlc() {
    find /ssd/claudios/projects -not \( -path ./eugenp_tutorials -prune \) -name "mvn_*" -print0 |
        xargs -0 -P8 -I{} pcre2grep -o1 -H "Instrumenting: .*((Test.*)|(.*Test)|(.*Tests)|(.*TestCase))$" {} |
        sed -E "s/mvn_log_.*$/\*\_java.gz/" |
        sort -u |
        xargs -I% -n1 sh -c 'ls -Sr % 1>>/home/claudios/resolved_202205111816.txt 2>>/home/claudios/unresolved_202205111816.txt'
}

find_instrumented_dumps() {
    find /ssd/claudios/projects -name "mvn_*" -print0 |
        xargs -0 -P8 -I{} pcre2grep -o1 -H "Instrumenting: .*((Test.*)|(.*Test)|(.*Tests)|(.*TestCase))$" {} |
        sed -E "s/mvn_log_.*$/\*\_java.gz/" |
        sort -u |
        xargs -I% -n1 sh -c 'ls -Sr % 1>>/home/claudios/resolved_202205111816.txt 2>>/home/claudios/unresolved_202205111816.txt'
}

find_instrumented_dumps_and_parse() {
    find /ssd/claudios/projects -name "mvn_*" -print0 |
        xargs -0 -P8 -I{} pcre2grep -o1 -H "Instrumenting: .*((Test.*)|(.*Test)|(.*Tests)|(.*TestCase))$" {} |
        sed -E "s/mvn_log_.*$/\*\_java.gz/" |
        sort -u |
        xargs -I% -n1 sh -c 'ls -Sr % 2>>/home/claudios/unresolved_202205111816.txt' |
        parallel --progress -N1 --null "(timeout -v 24h python3.9 /ssd/claudios/trace-python/scripts/trace_parse.py {} > parse_logs/\$(basename {}).txt) 2>parse_logs/\$(basename {})_errors.log"
}

parse_dumps() {
    find /ssd/claudios/projects -name "*java.gz" -size +33c -printf '%s\t%p\n' |
        sort -nr |
        cut -f2- |
        xargs -P2 -n1 -I{} sh -c "(timeout -v 24h python3.9 /ssd/claudios/trace-python/scripts/trace_parse.py {} > parse_logs/\$(basename {}).txt)" 2>parse_logs_errors1.log
}

parse_dumps_parallel() {
    find /ssd/claudios/projects -name "*java.gz" -size +33c -printf '%s\t%p\n' |
        sort -nr |
        cut -f2- |
        parallel --progress -N1 --null "(timeout -v 24h python3.9 /ssd/claudios/trace-python/scripts/trace_parse.py {} > parse_logs/\$(basename {}).txt)" 2>parse_logs_errors1.log
}

parse_netty_dumps() {
    cut </ssd/claudios/anand_traces/io_netty_list.txt -f2- |
        xargs -P4 -I{} sh -c "(poetry run python scripts/trace_parse.py {} --source_path /ssd/claudios/anand_projs/netty/common/src/main/java/ --test_path /ssd/claudios/anand_projs/netty/common/src/test/java/ 2>1 | aha > reports/netty_\$(basename {}).html)"
}

parse_guava_dumps() {
    cut </ssd/claudios/anand_traces/com_google_list.txt -f2- | xargs -P8 -I{} sh -c "(poetry run python scripts/trace_parse.py {} --max_depth -1 --source_path /ssd/claudios/anand_projs/guava/guava/src/ --test_path /ssd/claudios/anand_projs/guava/guava-tests/test/ 2>1 | aha > reports/guava_\$(basename {}).html)"
}

sort_resolved_dumps() {
    xargs </ssd/claudios/resolved.txt -I% -n1 ls -l % |
        sort -r -n -k6 |
        awk '{print $9}' >/ssd/claudios/eugenp_test_inst_sorted.txt
}

stop_containers() {
    docker stop "$(docker ps --filter name="(parser|test)")"
}

find_surefire_poms() {
    find . -name pom.xml -exec xq ".project.build.pluginManagement.plugins[]? | .[]? | select(.artifactId?==\"maven-surefire-plugin\")" {} \;
}

find_plexus_projects() {
    find /ssd/claudios/projects -name pom.xml -exec grep -n -o1 "plexus" {} /dev/null \;
}

run_orchestrator() {
    sudo python3.9 orchestrator/Runner.py --projects "$1" --maven_cache /ssd/claudios/m2 --parallelism 8 --out /ssd/claudios/trace_output/ trace >>log_noplex.txt 2>>error_noplex.txt
}

find_projects_gh() {
    # These secrets are invalid, generate a new secret!
    curl -u claudiosv:secret https://api.github.com/search/code\?q\=org:eclipse+filename:pom.xml+path:/ | sed 's/$/.git/' | xargs git clone --depth 1
    curl -u claudiosv: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 https://api.github.com/search/repositories\?sort\=stars\&orer\=desc\&q\=topic:java-tutorials
    jq -r '.items[] | {html_url, description, stargazers_count}'

    curl -u claudiosv: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 https://api.github.com/search/repositories\?sort\=stars\&orer\=desc\&q\=java+language:java |
        jq -r '.items[].full_name'
    curl -u claudiosv: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 https://api.github.com/search/repositories\?sort\=stars\&orer\=desc\&q\=java+language:java |
        jq -r '.items[].full_name' |
        xargs -I% curl -u claudiosv:secret https://api.github.com/search/code\?q\=repo:%+filename:pom.xml+path:/
}

find_tests() {
    find "$1" -maxdepth 1 -type d -print0 | while read -d '' -r dir; do
        files=$(find "$dir" -iname "*test*.java" -type f | wc -l)
        basename=$(basename "$dir")
        printf "%s,%s,%d\n" "$basename" "$dir" "$files"
    done
}

find_tests1() {
    find "$1" -maxdepth 2 -type d -print0 | while read -d '' -r dir; do
        files=$(find "$dir" -iname "*test*.java" -type f | wc -l)
        basename=$(basename "$dir")
        printf "%s,%s,%d\n" "$basename" "$dir" "$files"
    done
}

find_dumps() {
    find "$1" -mindepth 1 -maxdepth 1 -type d -print0 | while read -d '' -r dir; do
        files=$(find "$dir" -name "dump-1.zip" -size +33c -type f | wc -l)
        basename=$(basename "$dir")
        printf "%s,%s,%d\n" "$basename" "$dir" "$files"
    done
}

find_test_cases() {
    find "$1" -maxdepth 1 -type d -print0 | while read -d '' -r dir; do
        files=$(find "$dir" -iname "*test*.java" -type f | wc -l)
        basename=$(basename "$dir")
        test_cases_raw=$(find "$dir" -iname "*test*.java" -type f -print0 | xargs -0 -I% grep -i -o @Test "%" | sort | uniq -c | sort -nr | awk '{s+=$1} END {print s}') #> ${basename}_counts.txt);
        #test_cases=$(cat ${basename}_counts.txt | awk '{s+=$1} END {print s}');
        #printf "Basename: %s\nDir: %s\nTest suites: %d\nTest cases:%d\n-----------\n" "$basename" "$dir" "$files" "$test_cases"
        printf "%s,%d,%d\n" "$basename" "$files" "$test_cases_raw"
    done
}

generate_log_report() {
    file="$1"
    echo "Dump found: $(grep -c "Dump found" "$file")"
    echo "Backlog non cont: $(grep -c "\nValueError: NOTE: backlog was not completely" "$file")"
    echo "Runnables: $(grep -c "\--------- TEST SUITE RUNNABLE ---------" "$file")"
    echo "Working on: $(grep -c "b'Working on:" "$file")"
    echo "Dump path: $(grep -c "Dump path" "$file")"
    echo "Dump not found: $(grep -c "Dump not found" "$file")"
    echo "Trace exception: $(grep -c "objects.trace.TraceException" "$file")"
    echo "Ordered not found: $(grep -c "Ordered not found" "$file")"
    echo "Intermeiate not found: $(grep -c "Intermediate not found" "$file")"
    echo "Zip exception: $(grep -c "Dump found\\\njava.util.zip.ZipException" "$file")"
    echo "OOM: $(grep -i -c "OutofMemory" "$file")"
}

generate_project_report() {
    proj="$1"
    basename=$(basename "$proj")
    echo "$basename"
    failed_txt=$(find "$proj" -name FAILED.txt | wc -l)
	printf "FAILED.txt: %d\n" "$failed_txt"

    build_fail=$(find "$proj" -name "mvn_*" -print0 | xargs -0 -P8 -I{} grep -H "BUILD FAILURE" {} | wc -l)
	print "Build failure: %d\n" "$build_fail"

    build_success=$(find "$proj" -name "mvn_*" -print0 | xargs -0 -P8 -I{} grep -H "BUILD SUCCESS" {} | wc -l)
	printf "Build success: %d\n" "$build_success"

    tests_run=$(find "$proj" -name "mvn_*" -print0 | xargs -0 -P8 -I{} grep -H -P "Tests run: ([1-9]+), Failures: 0, Errors: 0, Skipped: 0" {} | wc -l)
	printf "Tests run: %d\n" "$tests_run"

    test_sum=$(find "$proj" -name "mvn_*" -print0 | xargs -0 -P8 -I{} pcre2grep -o1 "Tests run: ([1-9]+), Failures: 0, Errors: 0, Skipped: 0" {} | awk '{s+=$1} END {print s}')
	printf "Tests run sum: %d\n" "$test_sum"

    instrumented=$(find "$proj" -name "mvn_*" -print0 | xargs -0 -P8 -I{} grep -H -P -i "Enabling instrumentation" {} | wc -l)
	printf "Enabling instrumentation: %d\n" "$instrumented"

    test_instrumented=$(find "$proj" -name "mvn_*" -print0 | xargs -0 -P8 -I{} grep -H -P -i -m1 "Instrumenting: .*Test$" {} | wc -l)
	printf "Test instrumented: %d\n" "$test_instrumented"

    gzips=$(find "$proj" -name "*java.gz" | wc -l)
	printf "Gzips produced: %d\n" "$gzips"

    files=$(find "$proj" -iname "*test*.java" -type f | wc -l)
    test_cases_raw=$(find "$proj" -iname "*test*.java" -type f -print0 | xargs -0 -I% grep -i -o @Test "%" | sort | uniq -c | sort -nr | awk '{s+=$1} END {print s}')
    printf "Test suites heuristic: %d\n" "$files"
    printf "Test cases heuristic: %d\n" "$test_cases_raw"
    echo "---------------"
}

find_class_loader_corruptions() {
    pcre2grep -M -r "Considering: (?<class>(\w|$|/)*) (?<type>\w*)\nInstrumenting: \k<class>\nConsidering: \k<class>.{0,30} (?!\k<type>)" .
    set +H
    pcre2grep -M -r "Considering: (?<class>(\w|$|/)*) (?<type>\w*)\nInstrumenting: \k<class>\nConsidering: \k<class>\\\$1 (?!\k<type>)" .
}

backup_dumps()
{
    sudo find /ssd/claudios/projects -name "*java.gz" -type f -exec sh -c 'mv $(dirname {})/dump-1.zip /data/claudios/dump_backups/$(dirname {})/dump-1.zip' \;
}

case "$1" in
  "projreport")
    for PROJ in /ssd/claudios/projects/winery /ssd/claudios/claudios/projects/openzipkin_zipkin /ssd/claudios/projects/commons-lang /ssd/claudios/projects/commons-io /ssd/claudios/projects/californium /ssd/claudios/projects/jnosql /ssd/claudios/projects/avro /ssd/claudios/projects/dirigible /ssd/claudios/projects/hono /ssd/claudios/projects/pinot /ssd/claudios/projects/dubbo /ssd/claudios/projects/rdf4j /ssd/claudios/projects/netty /ssd/claudios/projects/org.aspectj /ssd/claudios/projects/jetty.project /ssd/claudios/projects/eclipse-collections
    do
        generate_project_report $PROJ
    done
    ;;
  *)
    echo "You have failed to specify what to do correctly."
    exit 1
    ;;
esac

parallel --pipe -N1 --null echo {}