#!/bin/bash

gnuplot <<ZZZ
datafile1 = "graph-data-p432.txt"
graphtitle = "graph title here"
load "$HOME/bbperf/src/bbperf/tcp-graph.gp"
ZZZ

