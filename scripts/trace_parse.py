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
from typing import List, Tuple


indexed_traces = {}  # dump: []


def clean_event(event):
    if isinstance(event, int):
        return event
    del_keys = event.keys() - {
        "event_kind",
        "called_class_name",
        "called_method_name",
        "parameter_types",
        "line_numbers",
        "return_type",
    }
    for key in del_keys:
        del event[key]
    return event


def get_core_methods(path, test_path, index_traces=True):
    """Generates a stream of core method events from a traced test suite."""
    # Use an expanding set of all method calls starting from a core/test method to track where we are in the call tree.
    # This set is initialized & updated with expected method events as soon as we enter a test case and should be empty
    # once we have seen its entire execution.
    fanout = set()
    line_ix = 0
    suite_name = path.name.replace("_", "/").split("/")[:-1]
    if test_path:
        search_root = test_path
    else:
        search_root = (path.parents[1]
            / "src"
            / "test"
            / "java")
    heuristic_path = (
        search_root / ("/".join(suite_name) + ".java")
    )

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
            indexed_traces[data["index"]] = {
                "index": data["index"],
                "class_name": data["class_name"],
                "method_name": data["method_name"],
                "method_events": [
                    clean_event(e)
                    for e in data["method_events"]
                    if isinstance(e, int)
                    or e["event_kind"] in ["method_entry", "method_call", "method_exit"]
                ],
            }
            del data
    for key, data in indexed_traces.items():  # this is the number of traces
        class_name = data["class_name"]
        method_name = data["method_name"]

        # Heuristically detect test case entries.
        is_test_class = "test" in class_name.lower()
        is_junit_class = "junit" in class_name.lower()
        if is_junit_class:
            print(f"jUnit class detected in: {path} method: {class_name}.{method_name}")

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


def method_call_to_debug_str(
    class_name: str, method_name: str, parameter_types: List[str], return_type: str
) -> str:
    method_repr = (
        f" -> {class_name}.{method_name}({type_list(parameter_types)}): {return_type}"
    )
    return method_repr


def method_entry_to_debug_str(
    class_name: str, method_name: str, parameter_types: List[str], return_type: str
) -> str:
    method_repr = (
        f" -> {class_name}.{method_name}({type_list(parameter_types)}): {return_type}"
    )
    return method_repr


def traverse_call_graph(
    trace: dict, call_counter: Counter, java_calls: str, all_calls: str, root: bool
) -> Tuple[Counter, str, str]:  # counter of calls, java_calls, all_calls
    for event in trace["method_events"]:
        if type(event) is int:
            if event in indexed_traces:
                call_counter_child, java_calls_child, all_calls_child = traverse_call_graph(
                    indexed_traces[event], call_counter, java_calls, all_calls, False
                )
                call_counter += call_counter_child
                java_calls += java_calls_child
                all_calls += all_calls_child
            else:
                print("Trace not found in index")
        else:
            e_k = event["event_kind"]
            method_class = trace["class_name"]
            method_name = trace["method_name"]
            if e_k == "method_entry" and not (root):
                method_entry_repr = method_entry_to_debug_str(
                    method_class,
                    method_name,
                    event.get("parameter_types", [""]),
                    event["return_type"],
                )
                all_calls += method_entry_repr
            elif e_k == "method_call":
                called_class_name = event.get("called_class_name", "Unknown")
                called_method_name = event.get("called_method_name", "Unknown")

                method_call_repr = method_call_to_debug_str(
                    called_class_name,
                    called_method_name,
                    event.get("parameter_types", [""]),
                    event.get("return_type", ""),
                )
                all_calls += method_call_repr

                if called_class_name.startswith("java."):
                    java_calls += method_call_repr

                call_counter[f"{called_class_name}.{called_method_name}"] += 1
            elif e_k == "method_exit":
                if "return_type" in event:
                    all_calls += " ⇧ " + event["return_type"]
                else:
                    all_calls += " ⇧"
            else:
                pass
                # print(event)
    return (call_counter, java_calls, all_calls)


def count_java_calls(call_counter: Counter) -> int:
    total = 0
    for call, count in call_counter.items():
        if call.startswith("java."):
            total += count
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a gzipped trace.")
    parser.add_argument("--source_path", metavar="Path", type=Path, required=False)
    parser.add_argument("--test_path", metavar="Path", type=Path, required=False)
    parser.add_argument("--show_source", type=bool, action=argparse.BooleanOptionalAction)
    parser.add_argument("--verbose", type=bool, action=argparse.BooleanOptionalAction)
    parser.add_argument("path", metavar="Path", type=Path)

    # parser.add_argument("mode", choices=["one_call", "extract", "loc"])
    args = parser.parse_args()
    # one_call = args.mode == "one_call"
    # loc = args.mode == "loc"
    # extract = args.mode == "extract"

    dumps = {}
    dump_counter = {}
    file_name = Path(args.path)
    file_stem = file_name.stem
    if os.path.getsize(file_name) < 1:
        exit()
    # source_path = Path()
    files = {}
    string_traces = []
    visited = []
    visit_counter = Counter()
    loc_vs_calls = {}

    method_dicts = []

    for method in get_core_methods(file_name, args.test_path):
        call_counter = Counter()
        java_calls = ""
        all_calls = ""
        class_name = method["class_name"]
        method_name = method["method_name"]
        just_class_name = class_name.rpartition(".")[-1]
        just_method_name = method_name.partition("$")[0]
        anonymous_classes = class_name.split("$")[1:]
        anonymous_methods = method_name.split("$")[1:]
        call_counter, java_calls, all_calls = traverse_call_graph(
            method, call_counter, "", "", True
        )
        java_call_count = count_java_calls(call_counter)

        if args.verbose:
            print(
                f"    Analyzing trace {method['index']} FQN: {class_name} : {method_name}"
            )
            print(f"        Method makes {java_call_count} calls to java:{all_calls}")

        if args.source_path:
            search_root = args.source_path
        else:
            search_root = (file_name.parents[1]
            / "src"
            / "main"
            / "java")
        heuristic_path = (
            search_root
            / (class_name.replace(".", "/").partition("$")[0] + ".java")
        )
        size = 0
        try:
            size = os.path.getsize(heuristic_path)
        except FileNotFoundError:
            print(f"{heuristic_path} FILE NOT FOUND!")
            print(f"{class_name}:{method_name}")
            continue

        method_dict_template = {
            "test_suite": file_stem,  # this is the dump name
            "index_in_dump": method["index"],
            "class_name": class_name,
            "method_name": method_name,
            "just_class_name": just_class_name,
            "just_method_name": just_method_name,
            "anonymous_classes": anonymous_classes,
            "anonymous_methods": anonymous_methods,
            "source_code": "",
            "loc_executed": "",
            "loc_span": "",
            "loc": "",
            "notes": "",
            "all_calls": all_calls,
            "java_calls": java_calls,
            "java_call_count": java_call_count,
            "nonjava_call_count": sum(call_counter.values()) - java_call_count,
            "heuristic_path": str(heuristic_path),
        }

        for event in method["method_events"]:
            if not (type(event) is int):
                if "line_numbers" in event:
                    line_numbers = event["line_numbers"]

                    if len(line_numbers) > 0:
                        distance = max(line_numbers) - min(line_numbers)
                        extended_line_numbers = list(map(str, line_numbers))
                        line_regex = "|".join(extended_line_numbers)  # str(None) "None"
                        method_dict_template["loc"] = tuple(line_numbers)
                        method_dict_template["loc_executed"] = len(line_numbers)
                        method_dict_template["loc_span"] = distance + 1
                        if args.verbose:
                            print(f"    Analyzing {event['event_kind']} event:")
                            print(f"    Heuristic source: {heuristic_path}")
                            print(f"        Anonymous methods: {anonymous_methods}")
                            print(f"        Anonymous classes: {anonymous_classes}")
                            if len(line_numbers) > 1:
                                print(
                                    f"        {distance+1} / {len(line_numbers)} lines ({line_numbers})"
                                )
                            else:
                                print(f"        One liner ({line_numbers})")
                            print(f"        Source snippet:")
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
                            ("grep", "--color=always", "-E", f"(^({line_regex}).*)|^"),
                            check=False,
                            stdin=sed_2.stdout,
                            text=True,
                            capture_output=True,
                        )
                        sed_1.wait()
                        sed_2.wait()
                        if args.show_source:
                            print(grep.stdout)
                        method_dict_template["source_code"] = grep.stdout
                    else:
                        print(f"Heuristic source: {heuristic_path}")
                        print("         Something went wrong! 1")
                        method_dict_template["notes"] += "Couldn't find LOC event"
                        pass
                    if args.verbose:
                        print("----------------------------\n")
            # -- TYPE OF EVENT
        # ----- END OF EVENT LOOP

        method_dicts.append(method_dict_template)
    # -------------------- END OF THE MONSTER LOOP ------------------

    df = pd.DataFrame.from_records(method_dicts)
    df.to_parquet(f"parquets/{file_stem}.parquet")


def multiline_match(
    grep,
    anonymous_methods,
    anonymous_classes,
    just_method_name,
    just_class_name,
    method_name,
):
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
            pass
        else:
            print("             -> Something went wrong! 2")
            print(grep.stdout.decode("UTF-8"))
    elif just_method_name == "lambda" and (f"->" in grep_out):
        pass
    else:
        print("             -> Something went wrong! 3")
        print(grep.stdout.decode("UTF-8"))
