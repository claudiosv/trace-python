import argparse
import gzip
import json
from operator import index

import orjson as json

# import glob
import os
import pickle
from pathlib import Path
import subprocess
import pandas as pd
from collections import Counter
from typing import List, Tuple


indexed_traces = {}  # dump: []

heuristic_suite_path = ""
test_case_names = set()

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


def get_core_methods(path, test_path, index_traces=True, silent=False):
    """Generates a stream of core method events from a traced test suite."""
    # Use an expanding set of all method calls starting from a core/test method to track where we are in the call tree.
    # This set is initialized & updated with expected method events as soon as we enter a test case and should be empty
    # once we have seen its entire execution.
    fanout = set()
    line_ix = 0
    suite_name = path.name.replace("_", "/").split("/")[:-1]
    suite_name[-1] = suite_name[-1].partition(".")[0]
    if test_path:
        search_root = test_path
    else:
        search_root = path.parents[1] / "src" / "test" / "java"
    heuristic_suite_path = search_root / ("/".join(suite_name) + ".java")

    size = 0
    try:
        size = os.path.getsize(heuristic_suite_path)
    except FileNotFoundError:
        if not silent:
            print(suite_name)
            print(f"{heuristic_suite_path} SUITE NOT FOUND!")
        # continue
    if not silent:
        print(
            f"Opening dump of Java test suite {'.'.join(suite_name)} (size: {size}) from {path}:"
        )
    with gzip.open(path, "rt") as f:
        for line in f:
            line_ix += 1
            try:
                json_line = json.loads(line.rstrip())
            except:
                if not silent:
                    print("JSON error? line", line_ix, "of file", path)
                continue
            indexed_traces[json_line["index"]] = {
                "index": json_line["index"],
                "class_name": json_line["class_name"],
                "method_name": json_line["method_name"],
                "method_events": [
                    clean_event(e)
                    for e in json_line["method_events"]
                    if isinstance(e, int)
                    or e["event_kind"] in ["method_entry", "method_call", "method_exit"]
                ],
            }
            json_line = None
            del json_line
    for key, data in indexed_traces.items():  # this is the number of traces
        class_name = data["class_name"]
        method_name = data["method_name"]
        class_name_lower = class_name.lower()
        method_name_lower = method_name.lower()

        # Heuristically detect test case entries.
        is_test_class = "test" in class_name_lower
        is_junit_class = "junit" in class_name_lower
        # if is_junit_class:
        #    print(f"jUnit class detected in: {path} method: {class_name}.{method_name}")

        is_test_case = is_test_class and (
            "test" in method_name_lower or "when" in method_name_lower or method_name in test_case_names
        )  # we could skip junit classes too
        if is_test_case:
            if not silent:
                print("Test case found: ", class_name + "." + method_name)
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
                if not silent:
                    raise ValueError("Index not found in fan-out!", data["index"])
            else:
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
    trace: dict, depth: int, max_depth: int, call_counter, all_traces=indexed_traces
) -> Tuple[int, str, int]:
    if depth > max_depth and not max_depth == -1:
        return (depth, "", 0)
    depth += 1
    event_max = 512
    java_calls = ""
    call_counter = 0
    """
    calls = "eventblah eventblah kasjdk kasjdk bleh"
    This method should accept a list of method events like [
        "eventblah",
        "kasjdk",
        1,
        "kasjdk",
        5,
        6,
        7
        "bleh"
    ]

    It should add the Java calls to a string. This means it must be able to recurse
    on the the event indexes (1,5,6,7). These recursions should not in the end produce
    strings with more than 512 java calls. So if 1 and 5 produce a total of 511, 6 should
    not be traversed. If 5 reaches 512, it should exit, regardless of how deep
    with 512 calls.
    """
    event_cnt = 0
    for event in trace["method_events"]:
        # print(event)
        if type(event) is int:
            # print("entered index event", event)
            if event in all_traces:
                # print(event)
                depth, java_calls_child, call_counter_child = traverse_call_graph(
                    all_traces[event], depth, max_depth, call_counter
                )
                call_counter += call_counter_child
                java_calls += java_calls_child
                # print(java_calls)
            # else:
            # print("event not in index")
            # print(indexed_tracess)
            continue
        if call_counter > event_max:
            break
        event_cnt += 1
        e_k = event["event_kind"]
        if e_k == "method_call":
            called_class_name = event.get("called_class_name", "Unknown")
            called_method_name = event.get("called_method_name", "Unknown")
            # print("entered method call", called_class_name)

            if called_class_name.startswith("java."):
                method_call_repr = method_call_to_debug_str(
                    called_class_name,
                    called_method_name,
                    event.get("parameter_types", [""]),
                    event.get("return_type", "void"),
                )
                java_calls += method_call_repr
                # print(java_calls)
                call_counter += 1
    return (depth, java_calls, call_counter)


def iterate_method_call_count(method_events: dict) -> int:
    event_max = 999999999999
    event_cnt = 0
    for event in method_events:
        if type(event) is int:
            continue
        if event_cnt > event_max:
            break
        event_cnt += 1
        e_k = event["event_kind"]
        if e_k == "method_call":
            called_class_name = event.get("called_class_name", "Unknown")
            if called_class_name.startswith("java."):
                return 1
    return 0


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
    parser.add_argument("--project_name", metavar="Path", type=Path, required=False)
    parser.add_argument("--out_path", metavar="Path", type=Path, required=False)
    parser.add_argument(
        "--show_source", type=bool, action=argparse.BooleanOptionalAction
    )
    parser.add_argument("--verbose", type=bool, action=argparse.BooleanOptionalAction)
    parser.add_argument("--max_depth", type=int)
    parser.add_argument("action", type=str)
    parser.add_argument("path", metavar="Path", type=Path)
    with open("interesting_names.txt") as f:
            mylist = f.read().splitlines()
            test_case_names = set(mylist)
    args = parser.parse_args()

    if args.action == "parse":
        dumps = {}
        dump_counter = {}
        project_name = args.project_name
        out_path = args.out_path
        file_name = Path(args.path)
        file_stem = file_name.stem
        if os.path.getsize(file_name) < 1:
            print("File size invalid!!!", file_name)
            exit()
        files = {}
        string_traces = []
        visited = []
        visit_counter = Counter()
        loc_vs_calls = {}

        method_dicts = []
        any_core_methods = False
        for method in get_core_methods(file_name, args.test_path):
            any_core_methods = True
            class_name = method["class_name"]
            method_name = method["method_name"]
            just_class_name = class_name.rpartition(".")[-1]
            just_method_name = method_name.partition("$")[0]
            anonymous_classes = class_name.split("$")[1:]
            anonymous_methods = method_name.split("$")[1:]
            max_depth, java_calls, java_call_count = traverse_call_graph(
                method, 0, args.max_depth, 0
            )

            if args.verbose:
                print(
                    f"    Analyzing trace {method['index']} FQN: {class_name} : {method_name}"
                )
                print(
                    f"        Method makes {java_call_count} calls to java:{java_calls}"
                )

            if args.source_path:
                search_root = args.source_path
            else:
                search_root = file_name.parents[1] / "src" / "main" / "java"
            heuristic_path = search_root / (
                class_name.replace(".", "/").partition("$")[0] + ".java"
            )
            size = 0
            skip_file = False
            try:
                size = os.path.getsize(heuristic_path)
            except FileNotFoundError:
                print(f"{heuristic_path} FILE NOT FOUND!")
                print(f"{class_name}:{method_name}")
                skip_file = True
                # continue

            method_dict_template = {
                "project": project_name,
                "dump_path": str(file_name),
                "test_suite": file_stem,  # this is the dump name
                "index_in_dump": method["index"],
                "class_name": class_name,
                "method_name": method_name,
                "just_class_name": just_class_name,
                "just_method_name": just_method_name,
                "anonymous_classes": anonymous_classes,
                "anonymous_methods": anonymous_methods,
                "source_code": "",
                "loc_executed": 0,
                "loc_span": 0,
                "loc": (),
                "notes": "",
                "java_calls": java_calls,
                "java_call_count": java_call_count,
                "heuristic_source_path": str(heuristic_path),
                "heuristic_suite_path": str(heuristic_suite_path),
                "max_depth": max_depth
            }

            for event in method["method_events"]:
                if not (type(event) is int):
                    if "line_numbers" in event:
                        line_numbers = event["line_numbers"]

                        if len(line_numbers) > 0:
                            distance = max(line_numbers) - min(line_numbers)
                            extended_line_numbers = list(map(str, line_numbers))
                            line_regex = "|".join(
                                extended_line_numbers
                            )  # str(None) "None"
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
                            if not (skip_file or size < 1):
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
                                    (
                                        "grep",
                                        "--color=always",
                                        "-E",
                                        f"(^({line_regex}).*)|^",
                                    ),
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
                                method_dict_template[
                                    "notes"
                                ] += "Couldn't find source code heuristically"
                        else:
                            print(f"Heuristic source: {heuristic_path}")
                            print("         Something went wrong! 1")
                            method_dict_template["notes"] += "Couldn't find LOC event"
                        if args.verbose:
                            print("----------------------------\n")
                # -- TYPE OF EVENT
            # ----- END OF EVENT LOOP

            method_dicts.append(method_dict_template)
        # -------------------- END OF THE MONSTER LOOP ------------------
        if any_core_methods:
            df = pd.DataFrame.from_records(method_dicts)
            del method_dicts
            df["test_suite"] = df["test_suite"].astype(pd.StringDtype())
            df["class_name"] = df["class_name"].astype(pd.StringDtype())
            df["method_name"] = df["method_name"].astype(pd.StringDtype())
            df["just_class_name"] = df["just_class_name"].astype(pd.StringDtype())
            df["just_method_name"] = df["just_method_name"].astype(pd.StringDtype())
            df["anonymous_classes"] = df["anonymous_classes"].astype(pd.StringDtype())
            df["anonymous_methods"] = df["anonymous_methods"].astype(pd.StringDtype())
            df["source_code"] = df["source_code"].astype(pd.StringDtype())
            df["notes"] = df["notes"].astype(pd.StringDtype())
            df["java_calls"] = df["java_calls"].astype(pd.StringDtype())
            df["heuristic_source_path"] = df["heuristic_source_path"].astype(
                pd.StringDtype()
            )
            df["heuristic_suite_path"] = df["heuristic_suite_path"].astype(
                pd.StringDtype()
            )
            print(df.info())
            print(df.dtypes)
            print(df.info(memory_usage="deep"))
            os.makedirs(out_path, exist_ok=True)
            # df.to_parquet(f"parquets/{file_stem}.parquet", engine='pyarrow')
            df.to_pickle(out_path / f"{file_stem}.gz")
        else:
            print("Warning: Not a single core method was encountered")
    elif args.action == "count":
        file_name = Path(args.path)
        file_stem = file_name.stem
        if os.path.getsize(file_name) < 1:
            print(0)
            exit()

        core_method_counter = 0
        methods_call_java_count = 0
        for method in get_core_methods(file_name, args.test_path, silent=True):
            core_method_counter += 1
            methods_call_java_count += iterate_method_call_count(
                method.get("method_events", [])
            )
        print(f"{core_method_counter},{methods_call_java_count}")


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
