# Commands
find . -name classpath_X4PmlaxV -or -name paths_X4PmlaxV -or -name paths_X4PmlaxV_find -or -name paths_X4PmlaxV_strace -type f -print0 | xargs -0 rm

find /Users/claudio/projects/binarydecomp/Jackal/repos -iname "*_java.gz" -print0 | xargs -0 poetry run python trace_parse.py | aha > report.html

find /data/claudios/trace_projects/commons-io/ -iname "*_java.gz" -size +2c -printf '%s\t%p\n' | sort -n | cut -f2- | xargs poetry run python trace_parse.py | aha > report.html

ls -1 /Users/claudio/projects/binarydecomp/Jackal/repos/**/*.gz | xargs -n 1 -P 8 -I% timeout 1h poetry run python trace_parse.py %

find /data/claudios/trace_projects/commons-io/ -iname "*_java.gz" -size +2c -type f -exec ls -lh {} \;


proj=geronimo-config find /data/claudios/apache_projects/$proj/  -iname "*_java.gz" -size +2c -printf '%s\t%p\n' | sort -n | cut -f2- | xargs -P1 -I% (poetry run python scripts/trace_parse.py % show_source verbose loc | aha > reports/$proj_%.html)

find /ssd/claudios/projects/jen  -name "*java.gz" -size +3M -size -5M -printf '%s\t%p\n' | sort -n | cut -f2- | xargs -P1 -I{} sh -c "(poetry run python scripts/trace_parse.py {} show_source verbose loc | aha > reports/jenkins_\$(basename {}).html)"

set +H; pcre2grep -M  -r  "Considering: (?<class>(\w|$|/)*) (?<type>\w*)\nInstrumenting: \k<class>\nConsidering: \k<class>\\\$1 (?!\k<type>)" .

pcre2grep -M  -r  "Considering: (?<class>(\w|$|/)*) (?<type>\w*)\nInstrumenting: \k<class>\nConsidering: \k<class>.{0,30} (?!\k<type>)" .


java -jar docker-setup/orchestrator.jar one_list.txt $PWD/Outputs/ $PWD/m2/ 8 > 2022_04_03.log 2>2022_04_03.errors

# -newermt yesterday

find /data/claudios/apache_projects/ /data/claudios/trace_projects/ /data/claudios/eclipse_projects/ /data/claudios/projects/ /ssd/claudios/jenkinsci_jenkins/ -type f -name "*java.gz" -size +2c  -exec ls -lh {} \; > files_thurs1.txt
