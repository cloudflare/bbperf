#!/usr/bin/python3

# Copyright (c) 2024 Cloudflare, Inc.
# Licensed under the Apache 2.0 license found in the LICENSE file or at https://www.apache.org/licenses/LICENSE-2.0

import multiprocessing
import time
import queue
import socket
import uuid
import ipaddress
import shutil

from . import data_sender_thread
from . import udp_string_sender_thread
from . import data_receiver_thread
from . import control_receiver_thread
from . import util
from . import const
from . import output
from . import graph
from . import tcp_helper
from . import udp_helper

from .tcp_control_connection_class import TcpControlConnectionClass


def client_mainline(args):
    client_start_time = time.time()

    if args.verbosity:
        print("args: {}".format(args), flush=True)

    if args.client:
        try:
            # is the arg already an IP address?
            ipaddress.ip_address(args.client)
            server_ip = args.client

        except ValueError:
            # not an ip address, must be a hostname
            try:
                server_ip = socket.gethostbyname(args.client)

            except socket.gaierror as e:
                raise Exception("ERROR: unable to resolve hostname {}, {}".format(args.client, e))

    server_port = args.port
    server_addr = (server_ip, server_port)

    # create control connection

    if args.verbosity:
        print("creating control connection to server at {}".format(server_addr), flush=True)

    control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    control_sock.connect(server_addr)

    client_control_addr = control_sock.getsockname()

    if args.verbosity:
        print("created control connection, client {}, server {}".format(
              client_control_addr, server_addr), flush=True)

    control_conn = TcpControlConnectionClass(control_sock)
    control_conn.set_args(args)

    # generate a random UUID (36 character string)
    run_id = str(uuid.uuid4())

    control_conn.send_control_initial_string(run_id)

    control_conn.wait_for_control_initial_ack()

    control_conn.send_args_to_server(args)

    control_conn.wait_for_control_args_ack()

    # create data connection

    if args.verbosity:
        print("creating data connection to server at {}".format(server_addr), flush=True)

    data_initial_string = "data " + run_id

    if args.udp:
        data_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # bind client data connection to specific local port
        if args.local_data_port > 0:
            data_sock.bind(('0.0.0.0', args.local_data_port))
        data_sock.settimeout(const.SOCKET_TIMEOUT_SEC)
        # must send something just to bind a local addr
        data_sock.sendto("foo".encode(), ("127.0.0.1", 65535))
        client_data_addr = data_sock.getsockname()
        if args.verbosity:
            print("created udp data connection, client {}, no server addr".format(client_data_addr), flush=True)

        if args.verbosity:
            print("sending data initial string (async udp): {}".format(data_initial_string), flush=True)

        # start and keep sending the data connection initial string asynchronously
        readyevent = multiprocessing.Event()
        doneevent = multiprocessing.Event()
        udp_data_initial_string_sender_process = multiprocessing.Process(
            name = "udpdatainitialstringsender",
            target = udp_string_sender_thread.run,
            args = (readyevent, doneevent, args, data_sock, server_addr, data_initial_string),
            daemon = True)
        udp_data_initial_string_sender_process.start()
        if not readyevent.wait(timeout=60):
            raise Exception("ERROR: process failed to become ready")

        if args.verbosity:
            print("waiting for data initial ack", flush=True)

        # wait for data init ack
        udp_helper.wait_for_string(data_sock, server_addr, const.UDP_DATA_INITIAL_ACK)

        if args.verbosity:
            print("received data initial ack", flush=True)

        # stop sending data initial string
        doneevent.set()

    else:
        data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # bind client data connection to specific local port
        if args.local_data_port > 0:
            data_sock.bind(('0.0.0.0', args.local_data_port))
        tcp_helper.set_congestion_control(args, data_sock)
        tcp_helper.set_tcp_notsent_lowat(data_sock)
        data_sock.connect(server_addr)
        data_sock.settimeout(const.SOCKET_TIMEOUT_SEC)
        client_data_addr = data_sock.getsockname()
        if args.verbosity:
            print("created tcp data connection, client {}, server {}".format(
                client_data_addr, server_addr), flush=True)

        if args.verbosity:
            print("sending data initial string (tcp): {}".format(data_initial_string), flush=True)
        data_sock.sendall(data_initial_string.encode())
        if args.verbosity:
            print("sent data initial string (tcp)", flush=True)

    control_conn.wait_for_setup_complete_message()

    shared_run_mode = multiprocessing.Value('i', const.RUN_MODE_CALIBRATING)
    shared_udp_sending_rate_pps = multiprocessing.Value('i', const.UDP_DEFAULT_INITIAL_RATE)
    control_receiver_results_queue = multiprocessing.Queue()

    if args.reverse:
        # direction down

        readyevent = multiprocessing.Event()

        data_receiver_process = multiprocessing.Process(
            name = "datareceiver",
            target = data_receiver_thread.run,
            args = (readyevent, args, control_conn, data_sock, server_addr),
            daemon = True)

        data_receiver_process.start()
        if not readyevent.wait(timeout=60):
            raise Exception("ERROR: process failed to become ready")

        readyevent = multiprocessing.Event()

        control_receiver_process = multiprocessing.Process(
            name = "controlreceiver",
            target = control_receiver_thread.run_recv_queue,
            args = (readyevent, args, control_conn, control_receiver_results_queue),
            daemon = True)

        control_receiver_process.start()
        if not readyevent.wait(timeout=60):
            raise Exception("ERROR: process failed to become ready")

        # test starts here

        control_conn.send_start_message()

        thread_list = []
        thread_list.append(data_receiver_process)
        thread_list.append(control_receiver_process)


    else:
        # direction up

        readyevent = multiprocessing.Event()

        control_receiver_process = multiprocessing.Process(
            name = "controlreceiver",
            target = control_receiver_thread.run_recv_term_queue,
            args = (readyevent, args, control_conn, control_receiver_results_queue, shared_run_mode, shared_udp_sending_rate_pps),
            daemon = True)

        control_receiver_process.start()
        if not readyevent.wait(timeout=60):
            raise Exception("ERROR: process failed to become ready")

        data_sender_process = multiprocessing.Process(
            name = "datasender",
            target = data_sender_thread.run,
            args = (args, data_sock, server_addr, shared_run_mode, shared_udp_sending_rate_pps),
            daemon = True)

        # test starts here
        data_sender_process.start()

        thread_list = []
        thread_list.append(control_receiver_process)
        thread_list.append(data_sender_process)


    if args.verbosity:
        print("test running, {} {}, control conn addr {}, data conn addr {}, server addr {}, elapsed startup time {} seconds".format(
              "udp" if args.udp else "tcp",
              "down" if args.reverse else "up",
              client_control_addr,
              client_data_addr,
              server_addr,
              (time.time() - client_start_time)),
              flush=True)

    # output loop

    output.init(args)

    start_time_sec = time.time()

    while True:
        try:
            s1 = control_receiver_results_queue.get_nowait()
        except queue.Empty:
            s1 = None

        if s1:
            output.print_output(s1)
            continue

        if util.threads_are_running(thread_list):
            # nothing in queues, but test is still running
            time.sleep(0.01)
        else:
            break

        curr_time_sec = time.time()

        if ((curr_time_sec - start_time_sec) > args.max_run_time_failsafe_sec):
            raise Exception("ERROR: max_run_time_failsafe_sec exceeded")

    if args.verbosity:
        print("test finished, generating output", flush=True)

    output.term()

    util.done_with_socket(data_sock)
    control_conn.close()

    graphdatafilename = output.get_graph_data_file_name()
    rawdatafilename = output.get_raw_data_file_name()

    if (args.graph or args.graph_file) and not args.quiet:
        pngfilename = graphdatafilename + ".png"

        graph.create_graph(args, graphdatafilename, pngfilename)

        if args.graph_file:
            try:
                # move the pngfile to the user specified destination
                shutil.move(pngfilename, args.graph_file)
                print("created graph: {}".format(args.graph_file), flush=True)

            except Exception as e:
                print("ERROR: during move of graph png file: {}".format(e), flush=True)

        else:
            print("created graph: {}".format(pngfilename), flush=True)

    if args.keep and not args.quiet:
        print("keeping graph data file: {}".format(graphdatafilename), flush=True)
        print("keeping raw data file: {}".format(rawdatafilename), flush=True)
    else:
        output.delete_data_files()

    if args.verbosity:
        print("test complete, exiting")
