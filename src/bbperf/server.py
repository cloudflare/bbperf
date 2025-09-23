#!/usr/bin/python3

# Copyright (c) 2024 Cloudflare, Inc.
# Licensed under the Apache 2.0 license found in the LICENSE file or at https://www.apache.org/licenses/LICENSE-2.0

import time
import socket
import multiprocessing

from . import data_sender_thread
from . import data_receiver_thread
from . import control_receiver_thread
from . import udp_string_sender_thread
from . import util
from . import const
from . import tcp_helper

from .tcp_control_connection_class import TcpControlConnectionClass


def server_mainline(args):
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_addr = (args.bind, args.port)

    print("binding tcp control socket to local address {}".format(server_addr), flush=True)
    listen_sock.bind(server_addr)

    listen_sock.listen(32)          # listen backlog
    listen_sock.setblocking(True)

    server_port = listen_sock.getsockname()[1]

    while True:
        print("server listening on port {}".format(server_port), flush=True)

        # accept control connection

        # blocking
        control_sock, _ = listen_sock.accept()

        client_control_addr = control_sock.getpeername()

        print("client connected (control socket): client addr {}, server addr {}".format(
            client_control_addr, server_addr), flush=True)

        control_conn = TcpControlConnectionClass(control_sock)
        control_conn.set_args(args)

        curr_client_start_time = time.time()

        run_id = control_conn.wait_for_control_initial_string()

        control_conn.send_control_initial_ack()

        client_args = control_conn.wait_for_args_from_client()

        control_conn.send_control_args_ack()

        control_conn.set_args(client_args)

        # accept data connection

        # "data " + uuid of 36 characters
        len_data_connection_initial_string = 5 + 36

        if client_args.udp:
            # data connection is udp
            if client_args.verbosity:
                print("creating udp data connection", flush=True)

            # unconnected socket to catch just the first packet
            # we need to do it this way so we can figure out the client addr for our connected socket
            data_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            print("binding udp data socket to local address {}".format(server_addr), flush=True)
            data_sock.bind(server_addr)
            data_sock.settimeout(const.SOCKET_TIMEOUT_SEC)
            if client_args.verbosity:
                print("created udp data connection, no client addr, server addr {}".format(server_addr), flush=True)

            if client_args.verbosity:
                print("waiting to receive data initial string", flush=True)

            payload_bytes, client_data_addr = data_sock.recvfrom(len_data_connection_initial_string)
            payload_str = payload_bytes.decode()

            if client_args.verbosity:
                print("received data initial string: client data addr: {} string: {}".format(client_data_addr, payload_str), flush=True)

            # check run_id
            util.validate_data_connection(client_args, run_id, payload_str)

            if client_args.verbosity:
                print("sending data initial ack (async udp)", flush=True)

            # start and keep sending the data initial ack asynchronously
            readyevent = multiprocessing.Event()
            doneevent = multiprocessing.Event()
            udp_data_initial_ack_sender_process = multiprocessing.Process(
                name = "udpdatainitialacksender",
                target = udp_string_sender_thread.run,
                args = (readyevent, doneevent, client_args, data_sock, client_data_addr, const.UDP_DATA_INITIAL_ACK),
                daemon = True)
            udp_data_initial_ack_sender_process.start()
            if not readyevent.wait(timeout=60):
                raise Exception("ERROR: process failed to become ready")

        else:
            # data connection is tcp
            if client_args.verbosity:
                print("creating data connection (tcp), waiting for accept", flush=True)

            data_sock, _ = listen_sock.accept()
            data_sock.settimeout(const.SOCKET_TIMEOUT_SEC)
            tcp_helper.set_congestion_control(client_args, data_sock)
            tcp_helper.set_tcp_notsent_lowat(data_sock)
            client_data_addr = data_sock.getpeername()
            if client_args.verbosity:
                print("accepted tcp data connection, client {}, server {}".format(
                    client_data_addr, server_addr), flush=True)

            if client_args.verbosity:
                print("waiting to receive data initial string", flush=True)

            payload_bytes = tcp_helper.recv_exact_num_bytes(data_sock, len_data_connection_initial_string)
            payload_str = payload_bytes.decode()

            if client_args.verbosity:
                print("received data initial string: {}".format(payload_str), flush=True)

            # check run_id
            util.validate_data_connection(client_args, run_id, payload_str)


        shared_run_mode = multiprocessing.Value('i', const.RUN_MODE_CALIBRATING)
        shared_udp_sending_rate_pps = multiprocessing.Value('i', const.UDP_DEFAULT_INITIAL_RATE)

        if client_args.reverse:
            # direction down

            control_conn.send_setup_complete_message()

            readyevent = multiprocessing.Event()

            control_receiver_process = multiprocessing.Process(
                name = "controlreceiver",
                target = control_receiver_thread.run_recv_term_send,
                args = (readyevent, client_args, control_conn, shared_run_mode, shared_udp_sending_rate_pps),
                daemon = True)

            data_sender_process = multiprocessing.Process(
                name = "datasender",
                target = data_sender_thread.run,
                args = (client_args, data_sock, client_data_addr, shared_run_mode, shared_udp_sending_rate_pps),
                daemon = True)

            control_conn.wait_for_start_message()

            if client_args.udp:
                # stop sending UDP data init acks
                if client_args.verbosity:
                    print("stopping sending udp data initial acks to client", flush=True)
                doneevent.set()

            control_receiver_process.start()
            if not readyevent.wait(timeout=60):
                raise Exception("ERROR: process failed to become ready")

            data_sender_process.start()

            thread_list = []
            thread_list.append(control_receiver_process)
            thread_list.append(data_sender_process)

        else:
            # direction up

            readyevent = multiprocessing.Event()

            data_receiver_process = multiprocessing.Process(
                name = "datareceiver",
                target = data_receiver_thread.run,
                args = (readyevent, client_args, control_conn, data_sock, client_data_addr),
                daemon = True)

            data_receiver_process.start()
            if not readyevent.wait(timeout=60):
                raise Exception("ERROR: process failed to become ready")

            thread_list = []
            thread_list.append(data_receiver_process)

            control_conn.send_setup_complete_message()

        print("test running, {} {}, control conn addr {}, data conn addr {}, server addr {}, elapsed startup time {} seconds".format(
              "udp" if client_args.udp else "tcp",
              "down" if client_args.reverse else "up",
              client_control_addr,
              client_data_addr,
              server_addr,
              (time.time() - curr_client_start_time)),
              flush=True)

        start_time_sec = time.time()

        while True:
            if util.threads_are_running(thread_list):
                time.sleep(0.01)
            else:
                break

            curr_time_sec = time.time()

            if ((curr_time_sec - start_time_sec) > client_args.max_run_time_failsafe_sec):
                raise Exception("ERROR: max_run_time_failsafe_sec exceeded")

        if client_args.verbosity:
            print("test finished, cleaning up", flush=True)

        util.done_with_socket(data_sock)
        control_conn.close()

        print("client ended", flush=True)
