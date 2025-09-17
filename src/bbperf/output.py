# Copyright (c) 2024 Cloudflare, Inc.
# Licensed under the Apache 2.0 license found in the LICENSE file or at https://www.apache.org/licenses/LICENSE-2.0

import os
import time
import tempfile

from . import const
from . import util

from .json_output_class import JsonOutputClass


args = None
tmpfile1 = None
tmpfile2 = None
last_line_to_stdout_time = 0
print_header1 = True
print_header2 = True
print_header3 = True
relative_start_time_sec = None
json_output = None
unloaded_latency_rtt_ms = None


def init(args0):
    global args
    global tmpfile1
    global tmpfile2
    global json_output

    args = args0

    # create and open file

    if args.udp:
        tmp_graph_filename_prefix = "bbperf-graph-data-udp-"
        tmp_raw_filename_prefix = "bbperf-raw-data-udp-"
    else:
        tmp_graph_filename_prefix = "bbperf-graph-data-tcp-"
        tmp_raw_filename_prefix = "bbperf-raw-data-tcp-"

    tmpfile1 = tempfile.NamedTemporaryFile(prefix=tmp_graph_filename_prefix, delete=False)
    tmpfile2 = tempfile.NamedTemporaryFile(prefix=tmp_raw_filename_prefix, delete=False)

    json_output = JsonOutputClass(args)


def get_graph_data_file_name():
    return tmpfile1.name

def get_raw_data_file_name():
    return tmpfile2.name

def term():
    tmpfile1.close()
    tmpfile2.close()

    json_output.write_output()


def delete_data_files():
    if args.verbosity:
        print("deleting graph data file: {}".format(tmpfile1.name), flush=True)
        print("deleting raw data file: {}".format(tmpfile2.name), flush=True)

    os.remove(tmpfile1.name)
    os.remove(tmpfile2.name)


def write_data_to_file(lineout, fileout):
    lineout_bytes = "{}\n".format(lineout).encode()
    fileout.file.write(lineout_bytes)

def write_raw_data_to_file(lineout):
    write_data_to_file(lineout, tmpfile2)

def write_graph_data_to_file(lineout):
    write_data_to_file(lineout, tmpfile1)


# keep in mind here that the interval data is coming in at a faster
# rate than what we want to (normally) display on stdout

def print_output(s1):
    global args
    global last_line_to_stdout_time
    global print_header1
    global print_header2
    global print_header3
    global relative_start_time_sec
    global unloaded_latency_rtt_ms

    write_raw_data_to_file(s1)

    curr_time = time.time()

    r_record = util.parse_r_record(args, s1)

    if relative_start_time_sec is None:
        # first incoming result has arrived
        relative_start_time_sec = r_record["r_pkt_sent_time_sec"]
        relative_pkt_sent_time_sec = 0
        relative_pkt_received_time_sec = 0
    else:
        relative_pkt_sent_time_sec = r_record["r_pkt_sent_time_sec"] - relative_start_time_sec
        relative_pkt_received_time_sec = r_record["r_pkt_received_time_sec"] - relative_start_time_sec

    if r_record["r_record_type"] == "run":
        json_output.set_unloaded_rtt_ms(unloaded_latency_rtt_ms)

        bdp_bytes = int( r_record["receiver_interval_rate_bytes_per_sec"] * (unloaded_latency_rtt_ms / 1000.0) )

        if bdp_bytes > 0:
            bloat_factor = float(r_record["buffered_bytes"]) / bdp_bytes
        else:
            bloat_factor = 0

        if print_header3:
            lineout = "sent_time recv_time sender_pps sender_Mbps receiver_pps receiver_Mbps unloaded_rtt_ms rtt_ms BDP_bytes buffered_bytes bloat_factor pkts_dropped pkts_dropped_percent"
            write_graph_data_to_file(lineout)
            print_header3 = False

        # write to file the same data and same rate as what we are receiving over the control connection
        lineout = "{} {} {} {} {} {} {} {} {} {} {} {} {}".format(
            relative_pkt_sent_time_sec,
            relative_pkt_received_time_sec,
            r_record["sender_pps"],
            r_record["sender_interval_rate_mbps"],
            r_record["receiver_pps"],
            r_record["receiver_interval_rate_mbps"],
            unloaded_latency_rtt_ms,
            r_record["rtt_ms"],
            bdp_bytes,
            r_record["buffered_bytes"],
            bloat_factor,
            r_record["interval_dropped"],
            r_record["interval_dropped_percent"]
            )

        write_graph_data_to_file(lineout)

        # add to JSON output
        excess = r_record["buffered_bytes"] - bdp_bytes
        if excess < 0:
            excess = 0
        new_entry = {
            "sent_time_sec": r_record["r_pkt_sent_time_sec"],
            "received_time_sec": r_record["r_pkt_received_time_sec"],
            "loaded_rtt_ms": r_record["rtt_ms"],
            "sender_throughput_rate_mbps": r_record["sender_interval_rate_mbps"],
            "receiver_throughput_rate_mbps": r_record["receiver_interval_rate_mbps"],
            "bdp_bytes": bdp_bytes,
            "excess_buffered_bytes": excess,
            "receiver_pps": r_record["receiver_pps"],
            "pkt_loss_percent": r_record["interval_dropped_percent"],
            "is_sample_valid": r_record["is_sample_valid"]
        }
        json_output.add_entry(new_entry)

        # write to stdout at the rate of one line per second
        # each stdout line will be a 0.1s snapshot
        if ((curr_time > (last_line_to_stdout_time + const.STDOUT_INTERVAL_SEC)) and not args.quiet) or args.verbosity > 2:
            if print_header2:
                print("  sent_time   recv_time  sender_Mbps receiver_Mbps sender_pps receiver_pps unloaded_rtt_ms rtt_ms BDP_bytes buffered_bytes bloat pkts_dropped  drop%", flush=True)
                print_header2 = False

            if r_record["interval_dropped_percent"] < 0:
                dropped_percent_str = "   n/a"
            else:
                dropped_percent_str = "{:6.3f}%".format(r_record["interval_dropped_percent"])

            print("{:11.6f} {:11.6f} {:11.3f}   {:11.3f}   {:8d}     {:8d}    {:8.3f}   {:9.3f} {:9d}    {:9d} {:6.1f}x   {:6d}    {}".format(
                relative_pkt_sent_time_sec,
                relative_pkt_received_time_sec,
                r_record["sender_interval_rate_mbps"],
                r_record["receiver_interval_rate_mbps"],
                r_record["sender_pps"],
                r_record["receiver_pps"],
                unloaded_latency_rtt_ms,
                r_record["rtt_ms"],
                bdp_bytes,
                r_record["buffered_bytes"],
                bloat_factor,
                r_record["interval_dropped"],
                dropped_percent_str
                ),
                flush=True)

            last_line_to_stdout_time = curr_time

    else:
        # calibrating
        # do we have a new unloaded latency?
        if (unloaded_latency_rtt_ms is None) or (r_record["rtt_ms"] < unloaded_latency_rtt_ms):
            unloaded_latency_rtt_ms = r_record["rtt_ms"]

        if ((curr_time > (last_line_to_stdout_time + const.STDOUT_INTERVAL_SEC)) and not args.quiet) or args.verbosity > 2:
            if print_header1:
                print("calibrating", flush=True)
                print("  sent_time   recv_time     rtt_ms", flush=True)
                print_header1 = False

            print("{:11.6f} {:11.6f} {:11.6f}".format(
                relative_pkt_sent_time_sec,
                relative_pkt_received_time_sec,
                unloaded_latency_rtt_ms
                ),
                flush=True)

            last_line_to_stdout_time = curr_time
