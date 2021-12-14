import json
import glob
import os
import gzip
from pathlib import Path
import pickle
from collections import Counter

final_dict = { "recursions_per_trace": Counter({}),
"distinct_calls": Counter({}),
"vocab_counter": Counter({}),
"api_counter": Counter({}),
"calls_per_trace": Counter({})
}

for filename in glob.iglob('pickles/*.pkl'):
    with open(filename,'rb') as infile:
        new_dict = pickle.load(infile)
        # print(new_dict)
        # print(new_dict["recursions_per_trace"])
        final_dict["recursions_per_trace"].update(Counter(new_dict["recursions_per_trace"]))
        final_dict["distinct_calls"].update(Counter(new_dict["distinct_calls"]))
        final_dict["vocab_counter"].update(Counter(new_dict["vocab_counter"]))
        final_dict["api_counter"].update(Counter(new_dict["api_counter"]))
        final_dict["calls_per_trace"].update(Counter(new_dict["calls_per_trace"]))
#         { "recursions_per_trace": [],
# "distinct_calls": [],
# "vocab_counter": [],
# "api_counter": [],
# "calls_per_trace": []
# }

with open(f"reduced.pkl","wb") as f:
    pickle.dump(final_dict,f)