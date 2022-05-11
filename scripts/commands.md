# Commands
find . -name classpath_X4PmlaxV -or -name paths_X4PmlaxV -or -name paths_X4PmlaxV_find -or -name paths_X4PmlaxV_strace -type f -print0 | xargs -0 rm

find /Users/claudio/projects/binarydecomp/Jackal/repos -iname "*_java.gz" -print0 | xargs -0 poetry run python trace_parse.py | aha > report.html

find /data/claudios/trace_projects/commons-io/ -iname "*_java.gz" -size +33c -printf '%s\t%p\n' | sort -n | cut -f2- | xargs poetry run python trace_parse.py | aha > report.html

ls -1 /Users/claudio/projects/binarydecomp/Jackal/repos/**/*.gz | xargs -n 1 -P 8 -I% timeout 1h poetry run python trace_parse.py %

find /data/claudios/trace_projects/commons-io/ -iname "*_java.gz" -size +2c -type f -exec ls -lh {} \;


proj=geronimo-config find /data/claudios/apache_projects/$proj/  -iname "*_java.gz" -size +2c -printf '%s\t%p\n' | sort -n | cut -f2- | xargs -P1 -I% (poetry run python scripts/trace_parse.py % show_source verbose loc | aha > reports/$proj_%.html)

find /ssd/claudios/projects/jen  -name "*java.gz" -size +3M -size -5M -printf '%s\t%p\n' | sort -n | cut -f2- | xargs -P1 -I{} sh -c "(poetry run python scripts/trace_parse.py {} show_source verbose loc | aha > reports/jenkins_\$(basename {}).html)"

find /ssd/claudios/anand_traces -name "com_google*.gz" -size +33c -printf '%s\t%p\n' | sort -nr | cut -f2- | xargs -P1 -I{} sh -c "(poetry run python scripts/trace_parse.py {} --source_path /ssd/claudios/anand_projs/guava/guava/src/ --test_path /ssd/claudios/anand_projs/guava/guava-tests/test/ --max_depth -1 | aha > reports/guava_\$(basename {}).html)"

cat /ssd/claudios/anand_traces/com_google_list.txt| cut -f2- | xargs -P8 -I{} sh -c "(poetry run python scripts/trace_parse.py {} --max_depth -1 --source_path /ssd/claudios/anand_projs/guava/guava/src/ --test_path /ssd/claudios/anand_projs/guava/guava-tests/test/ 2>1 | aha > reports/guava_\$(basename {}).html)"

find /ssd/claudios/projects/eugenp_tutorials/ -name "java*.gz" -size +33c -printf '%s\t%p\n' | sort -nr | cut -f2- | xargs -P8 -I{} sh -c "(python3.9 /ssd/claudios/trace-python/scripts/trace_parse.py {} --verbose --max_depth -1 | aha > reports/eugenp_\$(basename {}).html)"

cat /ssd/claudios/anand_traces/io_netty_list.txt| cut -f2- | xargs -P8 -I{} sh -c "(poetry run python scripts/trace_parse.py {} --source_path /ssd/claudios/anand_projs/netty/common/src/main/java/ --test_path / --max_depth -1 ssd/claudios/anand_projs/netty/common/src/test/java/ 2>1 | aha > reports/netty_\$(basename {}).html)"
set +H; pcre2grep -M  -r  "Considering: (?<class>(\w|$|/)*) (?<type>\w*)\nInstrumenting: \k<class>\nConsidering: \k<class>\\\$1 (?!\k<type>)" .

pcre2grep -M  -r  "Considering: (?<class>(\w|$|/)*) (?<type>\w*)\nInstrumenting: \k<class>\nConsidering: \k<class>.{0,30} (?!\k<type>)" .


java -jar docker-setup/orchestrator.jar one_list.txt $PWD/Outputs/ $PWD/m2/ 8 > 2022_04_03.log 2>2022_04_03.errors


find /home/claudios/projects/ -newermt yesterday -name "*java.gz" -size +33c -printf '%s\t%p\n' | sort -n | cut -f2- | xargs -P8 -I{} sh -c "(poetry run python scripts/trace_parse.py {} --max_depth -1 --show_source --verbose 2>&1 | aha > reports/\$(basename {}).html)"


find . -regextype posix-extended -regex "((Test.*\.java)|(.*Test\.java)|(.*Tests\.java)|(.*TestCase\.java))" -type f | xargs grep -i -o @Test | sort | uniq -c | sort -nr > ../hadoop_counts


# -newermt yesterday

find /data/claudios/apache_projects/ /data/claudios/trace_projects/ /data/claudios/eclipse_projects/ /data/claudios/projects/ /ssd/claudios/jenkinsci_jenkins/ -type f -name "*java.gz" -size +2c  -exec ls -lh {} \; > files_thurs1.txt

proj=projects/druid
cat $proj/errors_X4PmlaxV/error_build.txt $proj/logs_X4PmlaxV/log_build.txt | less -i
cat $proj/errors_X4PmlaxV/error_*.txt | less -i
cat $proj/logs_X4PmlaxV/log_*.txt | less -i


cat /ssd/claudios/anand_traces/io_netty_list.txt| cut -f2- | xargs -P4 -I{} sh -c "(poetry run python scripts/trace_parse.py {} --source_path /ssd/claudios/anand_projs/netty/common/src/main/java/ --test_path /ssd/claudios/anand_projs/netty/common/src/test/java/ 2>1 | aha > reports/netty_\$(basename {}).html)"

find . -name "*Test*.java" | xargs grep -i -o @Test | sort | uniq -c | sort -nr > ../hadoop_counts
cat ../hadoop_counts | awk '{s+=$1} END {print s}'


#!/bin/bash
PORT=8888
DATA=/data2/claudios/
 #  --gpus 'all,capabilities=utility' \

docker run --rm \
  --sig-proxy=false --detach-keys="ctrl-x" \
  -e RESTARTABLE=yes \
  -p ${PORT}:8888 \
  -e GRANT_SUDO=yes \
  --gpus 'all' \
  --ipc=host \
  --network=host \
  -e CHOWN_HOME=yes \
  -e CHOWN_HOME_OPTS='-R' \
  -v "${DATA}":/home/jovyan/data \
  --user "$(id -u)" --group-add users claudio/scipy-notebook:latest


curl -u claudiosv:secret https://api.github.com/search/code\?q\=org:eclipse+filename:pom.xml+path:/ | sed 's/$/.git/' | xargs git clone --depth 1

curl -u claudiosv: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 https://api.github.com/search/repositories\?sort\=stars\&orer\=desc\&q\=topic:java-tutorials

jq -r '.items[] | {html_url, description, stargazers_count}'


curl -u claudiosv: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 https://api.github.com/search/repositories\?sort\=stars\&orer\=desc\&q\=java+language:java | jq -r '.items[].full_name'


curl -u claudiosv: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 https://api.github.com/search/repositories\?sort\=stars\&orer\=desc\&q\=java+language:java | jq -r '.items[].full_name' | xargs -I% curl -u claudiosv:secret https://api.github.com/search/code\?q\=repo:%+filename:pom.xml+path:/

xq ".project.build.pluginManagement.plugins[] | .[] | select(.artifactId==\"maven-surefire-plugin\")" pom.xml | less -i

find . -name pom.xml -exec xq ".project.build.pluginManagement.plugins[]? | .[]? | select(.artifactId?==\"maven-surefire-plugin\")" {} \;


docker stop $(docker ps --filter name="(parser|test)")


java9 CollectorImprovementUnitTest

find $proj -name "mvn_*" | xargs -P8 -I{} pcre2grep -o1 -H "Instrumenting: (com/baeldung/.*((Test.*)|(.*Test)|(.*Tests)|(.*TestCase))$)" {} | sed "s/mvn_log/dump_X4PmlaxV/" | sed -E "s/\.java_.*$/\.java\/\*\_java.gz/" > /ssd/claudios/testinstrumented_eugen_dumps.txt
cat /ssd/claudios/testinstrumented_eugen_dumps.txt | xargs -I% -n1 sh -c 'ls -Sr % 1>>/ssd/claudios/resolved.txt 2>>/ssd/claudios/unresolved.txt'
cat /ssd/claudios/resolved.txt | xargs -I% -n1 ls -l % | sort -r -n -k6 | awk '{print $9}' > /ssd/claudios/eugenp_test_inst_sorted.txt

cat /ssd/claudios/eugenp_test_inst_sorted.txt| xargs -P8 -n1 -I{} sh -c "(timeout 24h -v python3.9 /ssd/claudios/trace-python/scripts/trace_parse.py --max_depth 200 {} > reports/eugenp3_\$(basename {}).txt)" 2>errors4.log


sudo find camel-kamelets maven-dist-tool geronimo-opentracing geronimo-metrics oneofour geronimo-config incubator-kyuubi packager dash-licenses empire-db microprofile-graphql -name "mvn_*" | xargs -P8 -I{} pcre2grep -o1 -H "Instrumenting: .*((Test.*)|(.*Test)|(.*Tests)|(.*TestCase))$" {} | sed "s/mvn_log/dump_X4PmlaxV/" | sed -E "s/\.java_.*$/\.java\/\*\_java.gz/" | xargs -I% -n1 sh -c 'ls -Sr % 1>>eclipse-collections_resolved.txt 2>>eclipsecollect_projs_unresolved.txt'
cat /ssd/claudios/resolved.txt | xargs -I% -n1 ls -l % | sort -r -n -k6 | awk '{print $9}' > /ssd/claudios/eugenp_test_inst_sorted.txt

find /ssd/claudios/projects -not \( -path ./eugenp_tutorials -prune \) -name "mvn_*" | xargs -P8 -I{} pcre2grep -o1 -H "Instrumenting: .*((Test.*)|(.*Test)|(.*Tests)|(.*TestCase))$" {} | sed "s/mvn_log/dump_X4PmlaxV/" | sed -E "s/\.java_.*$/\.java\/\*\_java.gz/" |  xargs -I% -n1 sh -c 'ls -Sr % 1>>/home/claudios/resolved_$(date +%Y%m%d%H%M).txt 2>>/home/claudios/unresolved_$(date +%Y%m%d%H%M).txt'

find /ssd/claudios/projects -not \( -path ./eugenp_tutorials -prune \) -name "mvn_*" | xargs -P8 -I{} pcre2grep -o1 -H "Instrumenting: .*((Test.*)|(.*Test)|(.*Tests)|(.*TestCase))$" {} | sed -E "s/mvn_log_.*$/\*\_java.gz/" | sort -u |  xargs -I% -n1 sh -c 'ls -Sr % 1>>/home/claudios/resolved_202205111816.txt 2>>/home/claudios/unresolved_202205111816.txt'

find /ssd/claudios/projects/camel-kamelets /ssd/claudios/projects/maven-dist-tool /ssd/claudios/projects/geronimo-opentracing /ssd/claudios/projects/geronimo-metrics /ssd/claudios/projects/oneofour /ssd/claudios/projects/geronimo-config /ssd/claudios/projects/incubator-kyuubi /ssd/claudios/projects/packager /ssd/claudios/projects/dash-licenses /ssd/claudios/projects/empire-db /ssd/claudios/projects/microprofile-graphql /ssd/claudios/projects/empire-db /ssd/claudios/projects/microprofile-graphql /ssd/claudios/projects/spark /ssd/claudios/projects/geronimo-txmanager /ssd/claudios/projects/capella-basic-vp /ssd/claudios/projects/cxf-fediz /ssd/claudios/projects/servicecomb-pack /ssd/claudios/projects/lyo /ssd/claudios/projects/lemminx /ssd/claudios/projects/winery /ssd/claudios/projects/openzipkin_zipkin /ssd/claudios/projects/commons-lang /ssd/claudios/projects/commons-io /ssd/claudios/projects/californium /ssd/claudios/projects/jnosql /ssd/claudios/projects/avro /ssd/claudios/projects/dirigible -name "*java.gz" -size +33c -printf '%s\t%p\n' | sort -nr | cut -f2- | xargs -P8 -n1 -I{} sh -c "(timeout -v 24h python3.9 /ssd/claudios/trace-python/scripts/trace_parse.py --max_depth 3 {} > reports/small2_\$(basename {}).txt)" 2>errors6.log

find /data/claudios/projects/eclipse-collections  -name "mvn_*" | xargs -P8 -I{} pcre2grep -o1 -H "Instrumenting: .*((Test.*)|(.*Test)|(.*Tests)|(.*TestCase))$" {} | sed -E "s/mvn_log_.*$/\*\_java.gz/" | sort -u | xargs -I% -n1 sh -c 'ls -Sr % 1>>/home/claudios/resolved_$(date +%Y%m%d%H%M).txt 2>>/home/claudios/unresolved_$(date +%Y%m%d%H%M).txt'

mkdir parse_logs
find /ssd/claudios/projects/winery /ssd/claudios/claudios/projects/openzipkin_zipkin /ssd/claudios/projects/commons-lang /ssd/claudios/projects/commons-io /ssd/claudios/projects/californium /ssd/claudios/projects/jnosql /ssd/claudios/projects/avro /ssd/claudios/projects/dirigible /ssd/claudios/projects/hono /ssd/claudios/projects/pinot /ssd/claudios/projects/dubbo /ssd/claudios/projects/rdf4j /ssd/claudios/projects/netty /ssd/claudios/projects/org.aspectj -name "*java.gz" -size +33c -printf '%s\t%p\n' | sort -nr | cut -f2- | xargs -P2 -n1 -I{} sh -c "(timeout -v 24h python3.9 /ssd/claudios/trace-python/scripts/trace_parse.py {} > parse_logs/\$(basename {}).txt)" 2>parse_logs_errors1.log

1. Look at screenshots to identify problem traces
2. Which projects were traced successfully?
3. Can we get commons and netty working again?

Automate workflow from finding successful traces to producing parquet