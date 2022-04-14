import os
from pathlib import Path
import subprocess
import argparse
from collections import Counter

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a gzipped trace.")
    parser.add_argument("path", metavar="Path", type=Path)
    args = parser.parse_args()
    filename = Path(args.path)
    empty_dumps  = Counter()
    full_dumps = Counter()
    with open(filename, "rt") as f:
        for line in f:
            # for each project
            line_split = line.split(',')
            proj_name = line_split[0]
            proj_path = line_split[1]
            print(f"{proj_name} : {proj_path}")

            files =  subprocess.run(
                            ("find", proj_path.rstrip(), "-type", "f","-name","*java.gz"),
                            check=True,
                            capture_output=True
                        )
            for dump in files.stdout.decode("UTF-8").splitlines():
                size = os.path.getsize(dump)
                if size > 1:
                    full_dumps[proj_name] += 1
                else:
                    empty_dumps[proj_name] += 1
            print(f"Empty: {empty_dumps}")
            print(f"not empty: {full_dumps}")
