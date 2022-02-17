import argparse
import gzip
import json

# import glob
import os
import pickle
from pathlib import Path
import subprocess


indexed_traces = {}  # dump: []
vocab_counter = {}
distinct_calls = {}
calls_per_trace = {}  # dump_name.trace: \d
recursions_per_trace = {}  # dump_name.trace: \d
api_counter = {}

def get_core_methods(path):
    """Generates a stream of core method events from a traced test suite."""
    # Use an expanding set of all method calls starting from a core/test method to track where we are in the call tree.
    # This set is initialized & updated with expected method events as soon as we enter a test case and should be empty
    # once we have seen its entire execution.
    fanout = set()
    line_ix = 0
    print("Opening dump:", path)
    with gzip.open(path, "rt") as f:
        for line in f: # this is the number of traces
            line_ix += 1
            try:
                data = json.loads(line.rstrip())
            except:
                print("JSON error? line", line_ix, "of file", path)
                continue
            class_name = data["class_name"]
            method_name = data["method_name"]

            # Heuristically detect test case entries.
            is_test_class = "test" in class_name.lower()
            is_junit_class = "junit" in class_name.lower()
            if is_junit_class:
                print(f"jUnit class detected in: {path} method: {class_name}.{method_name}")
            # if "assert" in method_name:
            #     print(f"Assert in: {path} method: {class_name}.{method_name}")
            #     print(filename.parents[1] / 'src' / 'main' / 'java' / (method['class_name'].replace('.','/').partition('$')[0] + '.java'))

            is_test_case = is_test_class and method_name.startswith("test")

            # Skip methods that don't belong to either category of interest.
            if not is_test_case and not fanout:
                continue

            # For all other cases, we now track the "fan-out" set of methods called to keep track of the call tree.
            # We will track all the non-Java methods called from this method.
            new_method_calls = [
                event for event in data["method_events"] if isinstance(event, int)
            ]

            # First, check if we have just entered a new test case.
            if not fanout:
                # We must have arrived here from a test method.
                # print("    Test detected:", method_name)
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
                yield data

def type_list(types):
    value = " "
    for t in types:
        value += t + "|"
    return value[:-1]

def event_to_str(event, trace_root_fqn):
    # print(event)
    e_k = event["event_kind"]
    string = ""
    if e_k == "method_entry":
        # entry
        string += (
            "[ENTRY] "
            + event["return_type"]
            + type_list(event.get("parameter_types", [""]))
            + " "
        )
    elif e_k == "method_call":
        # oo
        intermediate = (
            "[CALL] "
            + event["called_class_name"]
            + " "
            + event["called_method_name"]
            + type_list(event.get("parameter_types", [""]))
            + " "
            + event["return_type"]
            + " "
        )
        string += intermediate
        if intermediate in distinct_calls:
            distinct_calls[intermediate] += 1
        else:
            distinct_calls[intermediate] = 1
        if trace_root_fqn in calls_per_trace:
            calls_per_trace[trace_root_fqn] += 1
        else:
            calls_per_trace[trace_root_fqn] = 1
        called_class_name = event["called_class_name"]
        if called_class_name.startswith("java"):
            class_stems = event["called_class_name"].split(".")
            class_stem = ".".join(class_stems[:3])
            if class_stem in api_counter:
                api_counter[class_stem] += 1
            else:
                api_counter[class_stem] = 1
    elif e_k == "method_exit":
        # oo
        if "return_type" in event:
            string += "[EXIT] " + event["return_type"]
        else:
            string += "[EXIT] "
    else:
        pass
    return string

def trace_to_string(dump_name, trace, trace_root_fqn, recursive=True):
    string = trace["method_name"] + " "
    if not trace_root_fqn:
        trace_root_fqn = dump_name + "." + trace["method_name"]
    for event in trace["method_events"]:
        if recursive and type(event) is int:
            # print('Trace indexed')
            # pass
            if dump_name in indexed_traces and event in indexed_traces[dump_name]:
                if trace_root_fqn in recursions_per_trace:
                    recursions_per_trace[trace_root_fqn] += 1
                else:
                    recursions_per_trace[trace_root_fqn] = 1
                string += trace_to_string(
                    dump_name, indexed_traces[dump_name][event], trace_root_fqn
                )
            else:
                pass
                # print('Trace not indexed')
        else:
            event_string = event_to_str(event, trace_root_fqn)
            # if not trace_root_fqn in recursions_per_trace:
            #    recursions_per_trace[trace_root_fqn] = 0
            if event_string in vocab_counter:
                vocab_counter[event_string] += 1
            else:
                vocab_counter[event_string] = 1
            string += event_string
    if dump_name in indexed_traces:
        indexed_traces[dump_name][trace["index"]] = trace
    else:
        indexed_traces[dump_name] = {}
        indexed_traces[dump_name][trace["index"]] = trace
    return string

def process_file():
    stem = Path(filename).stem
    traces_in_dump = []
    with gzip.open(filename, "rb") as f:
        for line in f:
            if stem in dump_counter:
                dump_counter[stem] += 1
            else:
                dump_counter[stem] = 0
            traces_in_dump.append(json.loads(line))
    dumps[stem] = traces_in_dump
    # print(trace_to_string(sample_dump, sample_trace, '')[:-1])
    string_traces = []
    for dump_name, traces in dumps.items():
        for trace in traces:
            class_name = trace["class_name"]
            if "org.junit" not in class_name:
                string_traces.append(trace_to_string(dump_name, trace, "") + "\n")
    # longest_string = max(string_traces, key=len)
    # print(longest_string)
    # print(f"API counter: {api_counter}")
    # print(f"Recursions per trace: {recursions_per_trace}")
    for k in calls_per_trace.keys():
        if not k in recursions_per_trace:
            recursions_per_trace[k] = 0
    pkl = {
        "recursions_per_trace": recursions_per_trace,
        "distinct_calls": distinct_calls,
        "vocab_counter": vocab_counter,
        "api_counter": api_counter,
        "calls_per_trace": calls_per_trace,
    }
    with open(f"pickles1/{stem}.pkl", "wb") as f:
        pickle.dump(pkl, f)
    # sort_vocab = {k: v for k, v in sorted(vocab_counter.items(), key=lambda item: item[1])}
    # print(f"Number of distinct calls: {len(distinct_calls.keys())}") # 230 distinct calls
    # print(f"Vocab values (event string freq): {sort_vocab.values()}")
    # print(f"Number of string traces: {len(string_traces)}")
    # print(f"Indexed traces: {len(indexed_traces)}")
    # print(f"Number of traces: {len(traces)}")
    with open(f"datasets1/{stem}_data_set.txt", "w") as out:
        out.writelines(string_traces)
    # recursions_per_trace_counter = {k: v for k, v in sorted(recursions_per_trace.items(), reverse=True, key=lambda item: item[1])}.values()
    # print(f"Recursions per trace counter: {recursions_per_trace_counter}")
    # api_counter_sort = {k: v for k, v in sorted(api_counter.items(), reverse=True, key=lambda item: item[1])}
    # import itertools
    # api_counter_sorted = dict(itertools.islice(api_counter_sort.items(), 30))
    # print(f"api_counter_sorted: {api_counter_sorted}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a gzipped trace.")
    parser.add_argument(
        "path", metavar="Path", type=Path
    )
    args = parser.parse_args()

    dumps = {}
    dump_counter = {}
    filename = Path(args.path)
    if os.path.getsize(filename) < 1:
        exit()
    files = {}
    string_traces = []
    for method in get_core_methods(filename):
        s_trace =  trace_to_string(filename.stem, method, "") + "\n"
        string_traces.append(s_trace)
        print(s_trace)
        class_name = method['class_name']
        method_name = method['method_name']
        just_class_name = class_name.rpartition('.')[-1]
        just_method_name = method_name.partition('$')[0]
        anonymous_classes = class_name.split('$')[1:]
        anonymous_methods = method_name.split('$')[1:]
        # print(f"    Analyzing FQN: {method['class_name']}.{method_name}")
        #  find /Users/claudio/projects/binarydecomp/Jackal/repos/commons-io/src/main/java/org/apache/commons/io/ -name "Counters.java"
        #  grep /Users/claudio/projects/binarydecomp/Jackal/repos/commons-io/src/main/java/org/apache/commons/io//file/Counters.java longCounter
        heuristic_path = filename.parents[1] / 'src' / 'main' / 'java' / (method['class_name'].replace('.','/').partition('$')[0] + '.java')
        size = 0
        try:
            size = os.path.getsize(heuristic_path)
        except FileNotFoundError:
            print(f"{heuristic_path} FILE NOT FOUND!")
            print(f"{class_name}:{method_name}")
            continue
        files[heuristic_path] = size
        # print(f"    Heuristic source: {heuristic_path}")
        for event in method['method_events']:
            if not(type(event) is int):
                if 'line_numbers' in event:
                    line_numbers = event['line_numbers']
                    if len(line_numbers) == 0:
                        # print(f"Heuristic source: {heuristic_path}")
                        # print("         Something went wrong! 1")
                        pass
                    elif len(line_numbers) == 1:
                        pass
                        # print(f"        One liner ({event.get('line_numbers')})")
                        sed_1 = subprocess.Popen(('sed', f"{min(line_numbers[0], line_numbers[0]-2)},{line_numbers[-1]}!d;=", heuristic_path), stdout=subprocess.PIPE)
                        sed_2 = subprocess.Popen(('sed', 'N;s/\\n/ /'), stdin=sed_1.stdout, stdout=subprocess.PIPE)
                        grep =  subprocess.run(('grep', '--color', '-E', f"(^({line_numbers[0]}).*)|^"), check=False, stdin=sed_2.stdout, capture_output=True)
                        sed_1.wait()

                        grep_out = grep.stdout.decode('UTF-8')
                        grep_lines = grep_out.split('\n')
                        matching = False
                        if len(anonymous_methods) > 0 or len(anonymous_classes) > 0:
                            # anonymous class or method, be more generous with matching
                            for m in anonymous_methods:
                                if m in grep_out:
                                    matching = True
                            for c in anonymous_classes:
                                if c in grep_out:
                                    matching = True

                        for i in range(0,min(3,len(grep_lines))):
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
                            elif just_method_name == 'lambda' and (f"->" in grep_out):
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
                                print(f"    Analyzing FQN: {method['class_name']}:{method_name}")
                                print(f"    Heuristic source: {heuristic_path}")
                                print(f"        Anonymous methods: {anonymous_methods}")
                                print(f"        Anonymous classes: {anonymous_classes}")
                                print(f"        One liner ({event.get('line_numbers')})")
                                print("             -> Something went wrong! 3")
                                print(grep.stdout.decode('UTF-8'))
                    else:
                        distance = max(line_numbers) - min(line_numbers)
                        # print(f"        {distance+1} / {len(event.get('line_numbers'))} lines ({event.get('line_numbers')})")
                        extended_line_numbers = list(map(str, line_numbers))
                        line_regex = '|'.join(extended_line_numbers) # str(None) "None"
                        # sed '1022,1030!d;=' /Users/claudio/projects/binarydecomp/Jackal/repos/commons-io/src/main/java/org/apache/commons/io/file/PathUtils.java | sed 'N;s/\n/ /' | grep --color -E '(^(1023|1024|1028|1030).*)|^'
                        sed_1 = subprocess.Popen(('sed', f"{min(line_numbers[0], line_numbers[0]-2)},{line_numbers[-1]}!d;=", heuristic_path), stdout=subprocess.PIPE)
                        # sed_2 = subprocess.check_output(('sed', 'N;s/\\n/ /'), stdin=sed_1.stdout)
                        sed_2 = subprocess.Popen(('sed', 'N;s/\\n/ /'), stdin=sed_1.stdout, stdout=subprocess.PIPE)
                        grep =  subprocess.run(('grep', '--color', '-E', f"(^({line_regex}).*)|^"), check=False, stdin=sed_2.stdout, capture_output=True)
                        sed_1.wait()
                        grep_out = grep.stdout.decode('UTF-8')
                        grep_lines = grep_out.split('\n')
                        matching = False
                        if len(anonymous_methods) > 0 or len(anonymous_classes) > 0:
                            # anonymous class or method, be more generous with matching
                            for m in anonymous_methods:
                                if m in grep_out:
                                    matching = True
                            for c in anonymous_classes:
                                if c in grep_out:
                                    matching = True

                        for i in range(0,min(3,len(grep_lines))):
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
                            elif just_method_name == 'lambda' and (f"->" in grep_out):
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
                                print(f"    Analyzing FQN: {method['class_name']}:{method_name}")
                                print(f"    Heuristic source: {heuristic_path}")
                                print(f"        Anonymous methods: {anonymous_methods}")
                                print(f"        Anonymous classes: {anonymous_classes}")
                                print(f"        {distance+1} / {len(event.get('line_numbers'))} lines ({event.get('line_numbers')})")
                                print("             -> Something went wrong! 3")
                                print(grep.stdout.decode('UTF-8'))
                        # print(f"        {event['event_kind']}: {event.get('line_numbers')}")
                    # print('===============================')
        # break
    # print(fisles)
#ls -1 /Users/claudio/projects/binarydecomp/Jackal/repos/**/*.gz | xargs -n 1 -P 8 -I% timeout 1h poetry run python trace_parse.py %
