#!/bin/bash

# Pipe the files into xargs with timeout
ls -1 $0/**/*.gz | xargs -n 1 -P 8 -I% timeout 1h poetry run python trace_parse.py %