import glob
import gzip
import json
import os
import pickle
from collections import Counter
from pathlib import Path
import pandas as pd

dfs = []

for filename in glob.iglob("parquets/*.parquet"):
    dfs.append(pd.read_parquet(filename))
df = pd.concat(dfs)
df.to_parquet("reduced.parquet")