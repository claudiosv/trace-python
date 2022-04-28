import gzip
import orjson as json
import argparse


def get_core_methods(path):
    """Generates a stream of core method events from a traced test suite."""
    # Use an expanding set of all method calls starting from a core/test method to track where we are in the call tree.
    # This set is initialized & updated with expected method events as soon as we enter a test case and should be empty
    # once we have seen its entire execution.
    fanout = set()
    line_ix = 0
    print("Opening:", path)
    with gzip.open(path, "rt") as f:
        for line in f:
            line_ix += 1
            try:
                data = json.loads(line.rstrip())
            except:
                print("JSON error? line", line_ix, "of file", path)
                continue
            class_name = data["class_name"]
            method_name = data["method_name"]
            class_name_lower = class_name.lower()
            method_name_lower = method_name.lower()

            # Heuristically detect test case entries.
            is_test_class = "test" in class_name_lower
            is_test_case = is_test_class and (
                "test" in method_name_lower or "when" in method_name_lower
            )
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
                print("  Test:", method_name)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("in_file", help="Path to JSON data.")
    args = ap.parse_args()
    methods = get_core_methods(args.in_file)
    for m in methods:
        print("Got test method: ", m["class_name"], "#", m["method_name"])
