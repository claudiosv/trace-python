import argparse
from pathlib import Path
import json
# import glob
import os
import gzip
import pickle

parser = argparse.ArgumentParser(description='Process a gzipped trace.')
parser.add_argument('path', metavar='Path', type=Path,
                    help='an integer for the accumulator')

args = parser.parse_args()
print(args.path)

dumps = {}
dump_counter = {}
filename = args.path
if os.path.getsize(filename) < 1:
    exit()

stem = Path(filename).stem
traces_in_dump = []
with gzip.open(filename, 'rb') as f:
    for line in f:
        if stem in dump_counter:
            dump_counter[stem] += 1
        else:
            dump_counter[stem] = 0
        traces_in_dump.append(json.loads(line))
dumps[stem] = traces_in_dump

indexed_traces = {} # dump: []
vocab_counter = {}
distinct_calls = {}
calls_per_trace = {} # dump_name.trace: \d
recursions_per_trace = {} # dump_name.trace: \d
api_counter = {}

def type_list(types):
    value = " "
    for t in types:
        value += (t + '|')
    return value[:-1]
def event_to_str(event, trace_root_fqn):
    #print(event)
    e_k = event['event_kind']
    string = ''
    if e_k == 'method_entry':
      # entry
        string += "[ENTRY] " + event['return_type'] + type_list(event.get('parameter_types', [''])) + ' '
    elif e_k == 'method_call':
       # oo
        intermediate = "[CALL] " + event['called_class_name'] + ' ' + event['called_method_name'] + type_list(event.get('parameter_types', [''])) + ' ' + event['return_type'] + ' '
        string += intermediate
        if intermediate in distinct_calls:
            distinct_calls[intermediate] += 1
        else:
            distinct_calls[intermediate] = 1

        if trace_root_fqn in calls_per_trace:
            calls_per_trace[trace_root_fqn] += 1
        else:
            calls_per_trace[trace_root_fqn] = 1

        called_class_name = event['called_class_name']
        if called_class_name.startswith('java'):
            class_stems = event['called_class_name'].split('.')
            class_stem = '.'.join(class_stems[:3])
            if class_stem in api_counter:
                api_counter[class_stem] += 1
            else:
                api_counter[class_stem] = 1

    elif e_k == 'method_exit':
       # oo
        if 'return_type' in event:
            string += "[EXIT] " + event['return_type']
        else:
            string += "[EXIT] "
    else:
        pass
    return string
def trace_to_string(dump_name, trace, trace_root_fqn, recursive=True):
    string = trace['method_name'] + ' '
    if not trace_root_fqn:
            trace_root_fqn = dump_name + '.' + trace['method_name']
    for event in trace['method_events']:
        if recursive and type(event) is int:
            #print('Trace indexed')
            #pass
            if dump_name in indexed_traces and event in indexed_traces[dump_name]:
                if trace_root_fqn in recursions_per_trace:
                    recursions_per_trace[trace_root_fqn] += 1
                else:
                    recursions_per_trace[trace_root_fqn] = 1
                string += trace_to_string(dump_name, indexed_traces[dump_name][event], trace_root_fqn)
            else:
                pass
                #print('Trace not indexed')
        else:
            event_string = event_to_str(event, trace_root_fqn)
            #if not trace_root_fqn in recursions_per_trace:
            #    recursions_per_trace[trace_root_fqn] = 0
            if event_string in vocab_counter:
                vocab_counter[event_string] += 1
            else:
                vocab_counter[event_string] = 1
            string += event_string
    if dump_name in indexed_traces:
        indexed_traces[dump_name][trace['index']] = trace
    else:
        indexed_traces[dump_name] = {}
        indexed_traces[dump_name][trace['index']] = trace
    return string

# print(trace_to_string(sample_dump, sample_trace, '')[:-1])

string_traces = []
for dump_name,traces in dumps.items():
    for trace in traces:
        class_name = trace['class_name']
        if "org.junit" not in class_name:
            string_traces.append(trace_to_string(dump_name,trace, '') + '\n')
# longest_string = max(string_traces, key=len)
# print(longest_string)
# print(f"API counter: {api_counter}")
# print(f"Recursions per trace: {recursions_per_trace}")
for k in calls_per_trace.keys():
    if not k in recursions_per_trace:
        recursions_per_trace[k] = 0
pkl = { "recursions_per_trace": recursions_per_trace,
"distinct_calls": distinct_calls,
"vocab_counter": vocab_counter,
"api_counter": api_counter,
"calls_per_trace": calls_per_trace
}

with open(f"pickles/{stem}.pkl","wb") as f:
    pickle.dump(pkl,f)

# sort_vocab = {k: v for k, v in sorted(vocab_counter.items(), key=lambda item: item[1])}
# print(f"Number of distinct calls: {len(distinct_calls.keys())}") # 230 distinct calls
# print(f"Vocab values (event string freq): {sort_vocab.values()}")
# print(f"Number of string traces: {len(string_traces)}")
# print(f"Indexed traces: {len(indexed_traces)}")
# print(f"Number of traces: {len(traces)}")
with open(f"datasets/{stem}_data_set.txt", "w") as out:
    out.writelines(string_traces)

# recursions_per_trace_counter = {k: v for k, v in sorted(recursions_per_trace.items(), reverse=True, key=lambda item: item[1])}.values()
# print(f"Recursions per trace counter: {recursions_per_trace_counter}")
# api_counter_sort = {k: v for k, v in sorted(api_counter.items(), reverse=True, key=lambda item: item[1])}

# import itertools
# api_counter_sorted = dict(itertools.islice(api_counter_sort.items(), 30))
# print(f"api_counter_sorted: {api_counter_sorted}")