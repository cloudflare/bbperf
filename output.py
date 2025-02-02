# Copyright (c) 2024 Cloudflare, Inc.
# Licensed under the Apache 2.0 license found in the LICENSE file or at https://www.apache.org/licenses/LICENSE-2.0

import os
import time
import tempfile

import calibration
import const


args = None
tmpfile1 = None
tmpfile2 = None
last_line_to_stdout_time = 0
print_header1 = True
print_header2 = True
print_header3 = True
relative_start_time_sec = None
total_dropped_as_of_last_interval = 0


def init(args0):
    global args
    global tmpfile1
    global tmpfile2

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


def get_graph_data_file_name():
    return tmpfile1.name

def get_raw_data_file_name():
    return tmpfile2.name

def term():
    tmpfile1.close()
    tmpfile2.close()


def delete_data_files():
    if args.verbosity:
        print("deleting graph data file: {}".format(tmpfile1.name))
        print("deleting raw data file: {}".format(tmpfile2.name))

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
    global total_dropped_as_of_last_interval

    write_raw_data_to_file(s1)

    swords = s1.split()

    r_record_type = swords[1]
    r_pkt_sent_time_sec = float(swords[2])
    r_sender_interval_duration_sec = float(swords[3])
    r_sender_interval_pkts_sent = int(swords[4])                # valid for udp only
    r_sender_interval_bytes_sent = int(swords[5])
    r_sender_total_pkts_sent = int(swords[6])                   # valid for udp only
    r_receiver_interval_duration_sec = float(swords[8])
    r_receiver_interval_pkts_received = int(swords[9])          # valid for udp only
    r_receiver_interval_bytes_received = int(swords[10])
    r_receiver_total_pkts_received = int(swords[11])            # valid for udp only
    r_pkt_received_time_sec = float(swords[13])

    curr_time = time.time()
    rtt_sec = r_pkt_received_time_sec - r_pkt_sent_time_sec

    if relative_start_time_sec is None:
        # first incoming result has arrived
        relative_start_time_sec = r_pkt_sent_time_sec
        relative_pkt_sent_time_sec = 0
        relative_pkt_received_time_sec = 0
    else:
        relative_pkt_sent_time_sec = r_pkt_sent_time_sec - relative_start_time_sec
        relative_pkt_received_time_sec = r_pkt_received_time_sec - relative_start_time_sec

    if r_record_type == "run":

        sender_interval_rate_bps = (r_sender_interval_bytes_sent * 8.0) / r_sender_interval_duration_sec
        sender_interval_rate_mbps = sender_interval_rate_bps / (10 ** 6)

        receiver_interval_rate_bytes_per_sec = r_receiver_interval_bytes_received / r_receiver_interval_duration_sec
        receiver_interval_rate_bps = receiver_interval_rate_bytes_per_sec * 8
        receiver_interval_rate_mbps = receiver_interval_rate_bps / (10 ** 6)

        rtt_ms = rtt_sec * 1000

        unloaded_rtt_sec = calibration.get_unloaded_latency_rtt_sec()
        unloaded_rtt_ms = unloaded_rtt_sec * 1000

        bdp_bytes = int( receiver_interval_rate_bytes_per_sec * unloaded_rtt_sec )
        buffered_bytes = int( receiver_interval_rate_bytes_per_sec * rtt_sec )

        if bdp_bytes > 0:
            bloat_factor = float(buffered_bytes) / bdp_bytes
        else:
            bloat_factor = 0

        if args.udp:
            sender_pps = int(r_sender_interval_pkts_sent / r_sender_interval_duration_sec)
            receiver_pps = int(r_receiver_interval_pkts_received / r_receiver_interval_duration_sec)

            total_dropped = r_sender_total_pkts_sent - r_receiver_total_pkts_received
            dropped_this_interval = total_dropped - total_dropped_as_of_last_interval
            if dropped_this_interval < 0:
                dropped_this_interval = 0
            dropped_this_interval_percent = (dropped_this_interval * 100.0) / r_sender_interval_pkts_sent
            # remember this for next loop:
            total_dropped_as_of_last_interval = total_dropped
        else:
            # tcp
            sender_pps = -1
            receiver_pps = -1
            dropped_this_interval = -1
            dropped_this_interval_percent = -1

        if print_header3:
            lineout = "sent_time recv_time sender_pps sender_Mbps receiver_pps receiver_Mbps unloaded_rtt_ms rtt_ms BDP_bytes buffered_bytes bloat_factor pkts_dropped pkts_dropped_percent"
            write_graph_data_to_file(lineout)
            print_header3 = False

        # write to file the same data and same rate as what we are receiving over the control connection
        lineout = "{} {} {} {} {} {} {} {} {} {} {} {} {}".format(
            relative_pkt_sent_time_sec,
            relative_pkt_received_time_sec,
            sender_pps,
            sender_interval_rate_mbps,
            receiver_pps,
            receiver_interval_rate_mbps,
            unloaded_rtt_ms,
            rtt_ms,
            bdp_bytes,
            buffered_bytes,
            bloat_factor,
            dropped_this_interval,
            dropped_this_interval_percent
            )
        write_graph_data_to_file(lineout)

        # write to stdout at the rate of one line per second
        # each stdout line will be a 0.1s snapshot
        if (curr_time > (last_line_to_stdout_time + const.STDOUT_INTERVAL_SEC)) or args.verbosity:
            if print_header2:
                print("  sent_time   recv_time  sender_pps sender_Mbps receiver_pps receiver_Mbps unloaded_rtt_ms  rtt_ms  BDP_bytes buffered_bytes  bloat   pkts_dropped  drop%")
                print_header2 = False

            if dropped_this_interval_percent < 0:
                dropped_this_interval_percent_str = "  n/a"
            else:
                dropped_this_interval_percent_str = "{:6.3f}%".format(dropped_this_interval_percent)

            print("{:11.6f} {:11.6f} {:8d}   {:11.3f}   {:8d}    {:11.3f}    {:8.3f}    {:9.3f}  {:9d}    {:9d}    {:6.1f}x    {:6d}     {}".format(
                relative_pkt_sent_time_sec,
                relative_pkt_received_time_sec,
                sender_pps,
                sender_interval_rate_mbps,
                receiver_pps,
                receiver_interval_rate_mbps,
                unloaded_rtt_ms,
                rtt_ms,
                bdp_bytes,
                buffered_bytes,
                bloat_factor,
                dropped_this_interval,
                dropped_this_interval_percent_str
                ))

            last_line_to_stdout_time = curr_time

    else:
        calibration.update_rtt_sec(rtt_sec)

        if curr_time > (last_line_to_stdout_time + const.STDOUT_INTERVAL_SEC):
            if print_header1:
                print("calibrating")
                print("  sent_time   recv_time     rtt_ms")
                print_header1 = False

            unloaded_latency_rtt_sec = calibration.get_unloaded_latency_rtt_sec()
            unloaded_latency_rtt_ms = unloaded_latency_rtt_sec * 1000

            print("{:11.6f} {:11.6f} {:11.6f}".format(
                relative_pkt_sent_time_sec,
                relative_pkt_received_time_sec,
                unloaded_latency_rtt_ms
                ))

            last_line_to_stdout_time = curr_time
