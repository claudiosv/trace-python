import argparse
import gzip
import json

# import glob
import os
import pickle
from pathlib import Path
import subprocess
import pandas as pd
from collections import Counter


indexed_traces = {}  # dump: []
vocab_counter = {}
distinct_calls = {}
calls_per_trace = {}  # dump_name.trace: \d
recursions_per_trace = {}  # dump_name.trace: \d
api_counter = {}


def get_core_methods(path,index_traces=True):
    """Generates a stream of core method events from a traced test suite."""
    # Use an expanding set of all method calls starting from a core/test method to track where we are in the call tree.
    # This set is initialized & updated with expected method events as soon as we enter a test case and should be empty
    # once we have seen its entire execution.
    fanout = set()
    line_ix = 0
    suite_name = path.name.replace("_", "/").split("/")[:-1]
    heuristic_path = (
        path.parents[1] / "src" / "test" / "java" / ("/".join(suite_name) + ".java")
    )  # (path.replace('_', '.').split('.')[3:-1] + '.java')

    size = 0
    try:
        size = os.path.getsize(heuristic_path)
    except FileNotFoundError:
        print(f"{heuristic_path} SUITE NOT FOUND!")
        # continue
    print(
        f"Opening dump of {('.'.join(suite_name) + '.java')} (size: {size}) from {path}:"
    )
    with gzip.open(path, "rt") as f:
        for line in f:
            line_ix += 1
            try:
                data = json.loads(line.rstrip())
            except:
                print("JSON error? line", line_ix, "of file", path)
                continue
            indexed_traces[data["index"]] = data
    for key,data in indexed_traces.items():  # this is the number of traces
        class_name = data["class_name"]
        method_name = data["method_name"]

        # Heuristically detect test case entries.
        is_test_class = "test" in class_name.lower()
        is_junit_class = "junit" in class_name.lower()
        if is_junit_class:
            print(
                f"jUnit class detected in: {path} method: {class_name}.{method_name}"
            )

        is_test_case = is_test_class and method_name.startswith("test")

        # Skip methods that don't belong to either category of interest.
        if not is_test_case and not fanout:
            # print(f"    Skipping trace {data['index']} of {class_name} : {method_name} as it is a test case (or fanout has not begun)...")
            continue

        # For all other cases, we now track the "fan-out" set of methods called to keep track of the call tree.
        # We will track all the non-Java methods called from this method.
        new_method_calls = [
            event for event in data["method_events"] if isinstance(event, int)
        ]

        # First, check if we have just entered a new test case.
        if not fanout:
            # We must have arrived here from a test method.
            fanout = set(new_method_calls)
        else:
            if data["index"] not in fanout:
                raise ValueError("Index not found in fan-out!", data["index"])
            # Remove the current call and add fan-out based on whether this is a test or core.
            fanout.remove(data["index"])
            fanout.update(new_method_calls)

        # Yield only non-test methods.
        if (
            not is_test_class
        ):  # Focus on test classes to exclude calls from test cases to other test util functions.
            # pass
            yield data

def type_list(types):
    """Convert a list of type strings into one comma separated list"""
    value = ""
    for t in types:
        value += t + ","
    return value[:-1]

def event_to_str(event, trace_root_fqn, method_class, method_name):
    e_k = event["event_kind"]
    string = ""
    if e_k == "method_entry":
        string += (
            "-> "
            + method_class
            + "."
            + method_name + '('
            + type_list(event.get("parameter_types", [""]))
            + ") "
            # + event["return_type"]
        )
    elif e_k == "method_call":
        string += (
            "-> "
            + event["called_class_name"]
            + "."
            + event["called_method_name"] + '('
            + type_list(event.get("parameter_types", [""]))
            + ") "
            # + event["return_type"]
        )
    elif e_k == "method_exit":
        pass
    return string


def event_java_calls(event):
    """Used for counting number of java.* calls"""
    called_class_name = event["called_class_name"]
    if called_class_name.startswith("java."):
        return 1
    else:
        return 0


def trace_to_string(dump_name, trace, trace_root_fqn, string):
    if not trace_root_fqn:
        trace_root_fqn = dump_name + "." + trace["method_name"]
    for event in trace["method_events"]:
        if type(event) is int and event in indexed_traces:
            string += trace_to_string(
                    dump_name,
                    indexed_traces[event],
                    trace_root_fqn,
                    string,
                )
        else:
            string += event_to_str(event, trace_root_fqn, trace['class_name'], trace['method_name'])
    return string


def trace_to_java_calls(dump_name, trace, trace_root_fqn):
    java_calls = 0
    if not trace_root_fqn:
        trace_root_fqn = dump_name + "." + trace["method_name"]
    for event in trace["method_events"]:
        if type(event) is int and event in indexed_traces:
            java_calls += trace_to_java_calls(
                dump_name, indexed_traces[event], trace_root_fqn
            )
        else:
            if event["event_kind"] == "method_call":
                java_calls += event_java_calls(event)
    return java_calls

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a gzipped trace.")
    parser.add_argument("path", metavar="Path", type=Path)
    args = parser.parse_args()

    dumps = {}
    dump_counter = {}
    filename = Path(args.path)
    if os.path.getsize(filename) < 1:
        exit()
    files = {}
    string_traces = []
    visited = []
    visit_counter = Counter()
    loc_vs_calls = {}
    for method in get_core_methods(filename):
        class_name = method["class_name"]
        method_name = method["method_name"]
        # if f"{class_name}:{method_name}" in visited:
        #     continue
        # else:
        #     visited.append(f"{class_name}:{method_name}")
        visit_counter[f"{class_name}:{method_name}"] += 1
        trace_java_calls = trace_to_java_calls(filename.stem, method, "")
        # if trace_java_calls < 1:
        #     continue
        s_trace = trace_to_string(filename.stem, method, "", '')
        # string_traces.append(s_trace)
        # print(s_trace)

        just_class_name = class_name.rpartition(".")[-1]
        just_method_name = method_name.partition("$")[0]
        anonymous_classes = class_name.split("$")[1:]
        anonymous_methods = method_name.split("$")[1:]
        print(
            f"    Analyzing trace {method['index']} FQN: {method['class_name']} : {method_name}"
        )
        print(f"        Method makes {trace_java_calls} calls to java: {s_trace}")
        # print(f"        Abstract: {s_trace}")
        #  find /Users/claudio/projects/binarydecomp/Jackal/repos/commons-io/src/main/java/org/apache/commons/io/ -name "Counters.java"
        #  grep /Users/claudio/projects/binarydecomp/Jackal/repos/commons-io/src/main/java/org/apache/commons/io//file/Counters.java longCounter
        heuristic_path = (
            filename.parents[1]
            / "src"
            / "main"
            / "java"
            / (method["class_name"].replace(".", "/").partition("$")[0] + ".java")
        )
        size = 0
        try:
            size = os.path.getsize(heuristic_path)
        except FileNotFoundError:
            print(f"{heuristic_path} FILE NOT FOUND!")
            print(f"{class_name}:{method_name}")
            continue
        files[heuristic_path] = size
        # print(f"    Heuristic source: {heuristic_path}")

        lines_of_code = 0
        for event in method["method_events"]:
            if not (type(event) is int):
                if "line_numbers" in event:
                    lines_of_code += len(event.get("line_numbers", []))
                    line_numbers = event["line_numbers"]

                    if len(line_numbers) == 0:
                        print(f"Heuristic source: {heuristic_path}")
                        print("         Something went wrong! 1")
                        pass
                    elif len(line_numbers) == 1:
                        # print(f"        One liner ({event.get('line_numbers')})")
                        loc_vs_calls[f"{class_name}:{method_name}"] = (trace_java_calls, 1, 1)
                        print(
                            f"    Analyzing {event['event_kind']} event:"
                        )
                        print(f"    Heuristic source: {heuristic_path}")
                        print(f"        Anonymous methods: {anonymous_methods}")
                        print(f"        Anonymous classes: {anonymous_classes}")
                        print(f"        One liner ({event.get('line_numbers')})")
                        print(f"        Source snippet:")
                        # print("             -> Something went wrong! 3")
                        sed_1 = subprocess.Popen(
                            (
                                "sed",
                                f"{min(line_numbers[0], line_numbers[0]-2)},{line_numbers[-1]}!d;=",
                                heuristic_path,
                            ),
                            stdout=subprocess.PIPE,
                        )
                        sed_2 = subprocess.Popen(
                            ("sed", "N;s/\\n/ /"),
                            stdin=sed_1.stdout,
                            stdout=subprocess.PIPE,
                        )
                        grep = subprocess.run(
                            ("grep", "--color=always", "-E", f"(^({line_numbers[0]}).*)|^"),
                            check=False,
                            stdin=sed_2.stdout,
                            text=True,
                            capture_output=True
                            )
                        sed_1.wait()
                        sed_2.wait()
                        print(grep.stdout)
                        # one_line match
                    else:
                        distance = max(line_numbers) - min(line_numbers)
                        # print(f"        {distance+1} / {len(event.get('line_numbers'))} lines ({event.get('line_numbers')})")
                        extended_line_numbers = list(map(str, line_numbers))
                        line_regex = "|".join(extended_line_numbers)  # str(None) "None"
                        # sed '1022,1030!d;=' /Users/claudio/projects/binarydecomp/Jackal/repos/commons-io/src/main/java/org/apache/commons/io/file/PathUtils.java | sed 'N;s/\n/ /' | grep --color -E '(^(1023|1024|1028|1030).*)|^'
                        print(
                                f"    Analyzing {event['event_kind']} event:"
                            )
                        print(f"    Heuristic source: {heuristic_path}")
                        print(f"        Anonymous methods: {anonymous_methods}")
                        print(f"        Anonymous classes: {anonymous_classes}")
                        print(
                            f"        {distance+1} / {len(event.get('line_numbers'))} lines ({event.get('line_numbers')})"
                        )
                        print(f"        Source snippet:")
                        loc_vs_calls[f"{class_name}:{method_name}"] = (trace_java_calls, distance+1, len(event.get('line_numbers')))

                        sed_1 = subprocess.Popen(
                            (
                                "sed",
                                f"{min(line_numbers[0], line_numbers[0]-2)},{line_numbers[-1]}!d;=",
                                heuristic_path,
                            ),
                            stdout=subprocess.PIPE,
                        )
                        # sed_2 = subprocess.check_output(('sed', 'N;s/\\n/ /'), stdin=sed_1.stdout)
                        sed_2 = subprocess.Popen(
                            ("sed", "N;s/\\n/ /"),
                            stdin=sed_1.stdout,
                            stdout=subprocess.PIPE,
                        )
                        grep = subprocess.run(
                            ("grep", "--color=always", "-E", f"(^({line_regex}).*)|^"),
                            check=False,
                            stdin=sed_2.stdout,
                            text=True,
                            capture_output=True
                        )
                        sed_1.wait()
                        sed_2.wait()
                        print(grep.stdout)

                    print("----------------------------\n")
    print(visit_counter)
        # print(f"        Method calls {lines_of_code} lines of code")s
        # print(f"        {event['event_kind']}: {event.get('line_numbers')}")
        # print('===============================')
        # breaks
    # print(fisles)
    # df = pd.DataFrame.from_dict(loc_vs_calls, orient='index', columns=['num_calls', 'span', 'executed'])
    # existing = pd.read_csv("test.csv", index_col='fqn')
    # print(existing)
    # print(df)
    # pd.concat([df,existing]).to_csv("test.csv", index_label='fqn')
# ls -1 /Users/claudio/projects/binarydecomp/Jackal/repos/**/*.gz | xargs -n 1 -P 8 -I% timeout 1h poetry run python trace_parse.py %

def multiline_match():
    grep_out = grep.stdout.decode("UTF-8")
    grep_lines = grep_out.split("\n")
    matching = False
    if len(anonymous_methods) > 0 or len(anonymous_classes) > 0:
        # anonymous class or method, be more generous with matching
        for m in anonymous_methods:
            if m in grep_out:
                matching = True
        for c in anonymous_classes:
            if c in grep_out:
                matching = True

    for i in range(0, min(3, len(grep_lines))):
        if f" {method_name}" in grep_lines[i]:
            # not anonymous class or method
            matching = True

    if not matching:
        if (
            f" {just_class_name}" in grep_out
            or "         //" in grep_lines[0]
        ):
            # THIS IS A PROBLEM, but not one for now, notice the visitFile method name but it is deep in the class
            """
            Analyzing FQN: org.apache.commons.io.file.DeletingPathVisitor:visitFile
                Heuristic source: /Users/claudio/projects/binarydecomp/Jackal/repos/commons-io/src/main/java/org/apache/commons/io/file/DeletingPathVisitor.java
                    Anonymous methods: []
                    Anonymous classes: []
                    One liner ([37])
                         -> Something went wrong! 3
            36  */
            37 public class DeletingPathVisitor extends CountingPathVisitor {
            """
            # Here the problem is that the method def is too high up due to comments
            """
    Analyzing FQN: org.apache.commons.io.output.DeferredFileOutputStream:toInputStream
    Heuristic source: /Users/claudio/projects/binarydecomp/Jackal/repos/commons-io/src/main/java/org/apache/commons/io/output/DeferredFileOutputStream.java
        Anonymous methods: []
        Anonymous classes: []
        8 / 3 lines ([271, 275, 278])
             -> Something went wrong! 3
269         // but we should force the habit of closing whether we are working with
270         // a file or memory.
271         if (!closed) {
272             throw new IOException("Stream not closed");
273         }
274
275         if (isInMemory()) {
276             return memoryOutputStream.toInputStream();
277         }
278         return Files.newInputStream(outputPath);
        """
        pass
    elif just_method_name == "lambda" and (f"->" in grep_out):
        """
        Analyzing FQN: org.apache.commons.io.input.CharacterFilterReader:lambda$new$0
            Heuristic source: /Users/claudio/projects/binarydecomp/Jackal/repos/commons-io/src/main/java/org/apache/commons/io/input/CharacterFilterReader.java
                Anonymous methods: ['new', '0']
                Anonymous classes: []
                One liner ([38])
                     -> Something went wrong! 3
        37     public CharacterFilterReader(final Reader reader, final int skip) {
        38         super(reader, c -> c == skip);
        """
        pass
    else:
        print("             -> Something went wrong! 3")
        print(grep.stdout.decode("UTF-8"))
def one_line_match():
    grep_out = grep.stdout.decode("UTF-8")
    grep_lines = grep_out.split("\n")
    matching = False
    if len(anonymous_methods) > 0 or len(anonymous_classes) > 0:
        # anonymous class or method, be more generous with matching
        for m in anonymous_methods:
            if m in grep_out:
                matching = True
        for c in anonymous_classes:
            if c in grep_out:
                matching = True

    for i in range(0, min(3, len(grep_lines))):
        if f" {method_name}" in grep_lines[i]:
            # not anonymous class or method
            matching = True

    if not matching:
        if f" {just_class_name}" in grep_out or "         //" in grep_lines[0]:
            # THIS IS A PROBLEM, but not one for now, notice the visitFile method name but it is deep in the class
            """
            Analyzing FQN: org.apache.commons.io.file.DeletingPathVisitor:visitFile
                Heuristic source: /Users/claudio/projects/binarydecomp/Jackal/repos/commons-io/src/main/java/org/apache/commons/io/file/DeletingPathVisitor.java
                    Anonymous methods: []
                    Anonymous classes: []
                    One liner ([37])
                         -> Something went wrong! 3
            36  */
            37 public class DeletingPathVisitor extends CountingPathVisitor {
            """
            # Here the problem is that the method def is too high up due to comments
            """
    Analyzing FQN: org.apache.commons.io.output.DeferredFileOutputStream:toInputStream
    Heuristic source: /Users/claudio/projects/binarydecomp/Jackal/repos/commons-io/src/main/java/org/apache/commons/io/output/DeferredFileOutputStream.java
        Anonymous methods: []
        Anonymous classes: []
        8 / 3 lines ([271, 275, 278])
             -> Something went wrong! 3
269         // but we should force the habit of closing whether we are working with
270         // a file or memory.
271         if (!closed) {
272             throw new IOException("Stream not closed");
273         }
274
275         if (isInMemory()) {
276             return memoryOutputStream.toInputStream();
277         }
278         return Files.newInputStream(outputPath);
                                """
            pass
        elif just_method_name == "lambda" and (f"->" in grep_out):
            """
            Analyzing FQN: org.apache.commons.io.input.CharacterFilterReader:lambda$new$0
                Heuristic source: /Users/claudio/projects/binarydecomp/Jackal/repos/commons-io/src/main/java/org/apache/commons/io/input/CharacterFilterReader.java
                    Anonymous methods: ['new', '0']
                    Anonymous classes: []
                    One liner ([38])
                         -> Something went wrong! 3
            37     public CharacterFilterReader(final Reader reader, final int skip) {
            38         super(reader, c -> c == skip);
            """
            pass
        else:
            print("             -> Something went wrong! 3")
            print(grep.stdout.decode("UTF-8"))

# find /Users/claudio/projects/binarydecomp/Jackal/repos -iname "*_java.gz" -print0 | xargs -0 poetry run python trace_parse.py | ansi2html > report.html
