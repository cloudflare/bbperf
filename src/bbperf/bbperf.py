#!/usr/bin/python3

# Copyright (c) 2024 Cloudflare, Inc.
# Licensed under the Apache 2.0 license found in the LICENSE file or at https://www.apache.org/licenses/LICENSE-2.0

import argparse

from . import client
from . import server
from . import util
from . import const

def mainline():
    print("bbperf version {}".format(const.BBPERF_VERSION), flush=True)

    parser = argparse.ArgumentParser(description="bbperf: end to end performance and bufferbloat measurement tool")

    parser.add_argument("-s", "--server",
        action="store_true",
        default=False,
        help="run in server mode")

    parser.add_argument("-c", "--client",
        metavar="SERVER_ADDR",
        default=None,
        help="run in client mode (specify either DNS name or IP address)")

    parser.add_argument("-p", "--port",
        metavar="SERVER_PORT",
        type=int,
        default=const.SERVER_PORT,
        help="server port (default: {})".format(const.SERVER_PORT))

    parser.add_argument("-u", "--udp",
        action="store_true",
        default=False,
        help="run in UDP mode (default: TCP mode)")

    parser.add_argument("-R", "--reverse",
        action="store_true",
        default=False,
        help="data flow in download direction (server to client)")

    parser.add_argument("--max-ramp-time",
        metavar="SECONDS",
        type=int,
        default=None,
        help="max duration in seconds before collecting data samples (tcp default: {}, udp default: {})".format(
            const.DATA_SAMPLE_IGNORE_TIME_TCP_MAX_SEC,
            const.DATA_SAMPLE_IGNORE_TIME_UDP_MAX_SEC))

    parser.add_argument("-t", "--time",
        metavar="SECONDS",
        type=int,
        default=const.DEFAULT_VALID_DATA_COLLECTION_TIME_SEC,
        help="duration in seconds to collect valid data samples (default: {})".format(const.DEFAULT_VALID_DATA_COLLECTION_TIME_SEC))

    parser.add_argument("-v", "--verbosity",
        action="count",
        default=0,
        help="increase output verbosity (can be repeated)")

    parser.add_argument("-q", "--quiet",
        action="count",
        default=0,
        help="decrease output verbosity (can be repeated)")

    parser.add_argument("-J", "--json-file",
        default=None,
        help="JSON output file")

    parser.add_argument("-g", "--graph",
        action="store_true",
        default=False,
        help="generate graph and save in tmp file (requires gnuplot)")

    parser.add_argument("--graph-file",
        metavar="GRAPH_FILE",
        default=None,
        help="generate graph and save in the specified file (requires gnuplot)")

    parser.add_argument("-k", "--keep",
        action="store_true",
        default=False,
        help="keep data file")

    parser.add_argument("-B", "--bind",
        metavar="BIND_ADDR",
        default="0.0.0.0",
        help="bind server sockets to address")

    parser.add_argument("--local-data-port",
        metavar="LOCAL_DATA_PORT",
        type=int,
        default=0,
        help="local port for data connection (default: ephemeral)")

    parser.add_argument("-C", "--congestion",
        metavar="CC_ALGORITHM",
        default="cubic",
        help="congestion control algorithm (default: cubic)")

    args = parser.parse_args()

    util.validate_and_finalize_args(args)

    if args.client:
        client.client_mainline(args)
    else:
        server.server_mainline(args)


if __name__ == '__main__':
    mainline()
