# Copyright (c) 2024 Cloudflare, Inc.
# Licensed under the Apache 2.0 license found in the LICENSE file or at https://www.apache.org/licenses/LICENSE-2.0

import os
import argparse
import subprocess


def create_graph(args, datafile1, pngfilename):

    if args.graph_file:
        filename_in_title = args.graph_file
    else:
        filename_in_title = pngfilename

    this_script_dir = os.path.dirname(os.path.abspath(__file__))

    if args.udp:
        gp_file = this_script_dir + "/udp-graph.gp"
        graph_title = "bbperf UDP {}".format(filename_in_title)
    else:
        gp_file = this_script_dir + "/tcp-graph.gp"
        graph_title = "bbperf TCP {}".format(filename_in_title)

    gnuplot_script = "datafile1 = \"{}\" ; graphtitle = \"{}\" ; load \"{}\"".format(
        datafile1, graph_title, gp_file)

    result = subprocess.run(["gnuplot", "-e", gnuplot_script], capture_output=True)

    if args.verbosity or (result.returncode != 0):
        print("gnuplot -e {}".format(gnuplot_script), flush=True)
        print("returncode: {}".format(result.returncode), flush=True)
        print("stdout: {}".format(result.stdout), flush=True)
        print("stderr: {}".format(result.stderr), flush=True)


if __name__ == '__main__':
    datafile1 = "/tmp/bbperf-tcp-data-aa97m9xl"

    args_d = { "udp": True }

    # recreate args as if it came directly from argparse
    args = argparse.Namespace(**args_d)

    create_graph(args, datafile1)
