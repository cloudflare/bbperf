#!/usr/bin/python3

# Copyright (c) 2024 Cloudflare, Inc.
# Licensed under the Apache 2.0 license found in the LICENSE file or at https://www.apache.org/licenses/LICENSE-2.0

import time
import socket
import multiprocessing

from . import data_sender_thread
from . import data_receiver_thread
from . import control_receiver_thread
from . import util
from . import const
from . import tcp_helper

from .tcp_control_connection_class import TcpControlConnectionClass


def server_mainline(args):
    server_port = args.port

    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    listen_sock.bind(('0.0.0.0', server_port))

    listen_sock.listen(32)          # listen backlog
    listen_sock.setblocking(True)

    server_port = listen_sock.getsockname()[1]

    while True:
        print("server listening on port ", server_port, flush=True)

        # accept control connection

        # blocking
        control_sock, _ = listen_sock.accept()

        control_conn = TcpControlConnectionClass(control_sock)
        control_conn.set_args(args)

        print("client connected (control socket)", flush=True)

        # blocking
        run_id = control_conn.recv_initial_string()

        print("waiting for args from client", flush=True)

        # blocking
        client_args = control_conn.receive_args_from_client()

        print("received run_id: {}".format(run_id), flush=True)
        print("received args from client: {}".format(vars(client_args)), flush=True)

        control_conn.set_args(client_args)

        # accept data connection

        # "data " + uuid of 36 characters
        len_data_connection_initial_string = 5 + 36

        if client_args.udp:
            # data connection is udp
            if client_args.verbosity:
                print("creating data connection (udp)", flush=True)

            # unconnected socket to catch just the first packet
            # we need to do it this way so we can figure out the client addr for our connected socket
            data_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            data_sock.bind(("0.0.0.0", server_port))
            data_sock.settimeout(const.SOCKET_TIMEOUT_SEC)

            # read initial string
            # blocking
            payload_bytes, client_addr = data_sock.recvfrom(len_data_connection_initial_string)
            payload_str = payload_bytes.decode()

            # check run_id
            data_connection_run_id = payload_str[5:]
            if data_connection_run_id != run_id:
                raise Exception("ERROR: data connection invalid, control run_id {} data run_id {} ".format(
                    run_id, data_connection_run_id))

            data_sock.connect(client_addr)

        else:
            # data connection is tcp
            if client_args.verbosity:
                print("creating data connection (tcp)", flush=True)

            # blocking
            data_sock, _ = listen_sock.accept()
            data_sock.settimeout(const.SOCKET_TIMEOUT_SEC)
            tcp_helper.set_congestion_control(data_sock)
            client_addr = data_sock.getpeername()

            # read initial string
            # blocking
            payload_bytes = tcp_helper.recv_exact_num_bytes(data_sock, len_data_connection_initial_string)
            payload_str = payload_bytes.decode()

            # check run_id
            data_connection_run_id = payload_str[5:]
            if data_connection_run_id != run_id:
                raise Exception("ERROR: data connection invalid, control run_id {} data run_id {} ".format(
                    run_id, data_connection_run_id))

        print("created data connection", flush=True)

        shared_run_mode = multiprocessing.Value('i', const.RUN_MODE_CALIBRATING)
        shared_udp_sending_rate_pps = multiprocessing.Value('d', const.UDP_DEFAULT_INITIAL_RATE)

        if not client_args.reverse:
            # direction up

            data_receiver_process = multiprocessing.Process(
                name = "datareceiver",
                target = data_receiver_thread.run,
                args = (client_args, control_conn, data_sock),
                daemon = True)

            data_receiver_process.start()

            thread_list = []
            thread_list.append(data_receiver_process)

            tcp_helper.send_setup_complete_message_to_client(control_conn)

        if client_args.reverse:
            # direction down

            tcp_helper.send_setup_complete_message_to_client(control_conn)

            control_receiver_process = multiprocessing.Process(
                name = "controlreceiver",
                target = control_receiver_thread.run_recv_term_send,
                args = (client_args, control_conn, shared_run_mode, shared_udp_sending_rate_pps),
                daemon = True)

            data_sender_process = multiprocessing.Process(
                name = "datasender",
                target = data_sender_thread.run,
                args = (client_args, data_sock, shared_run_mode, shared_udp_sending_rate_pps),
                daemon = True)

            # wait for start message
            control_conn.wait_for_start_message()

            control_receiver_process.start()

            data_sender_process.start()

            thread_list = []
            thread_list.append(control_receiver_process)
            thread_list.append(data_sender_process)

        print("test running, {} {} from client {}".format(
              "udp" if client_args.udp else "tcp",
              "down" if client_args.reverse else "up",
              client_addr),
              flush=True)

        while True:
            if util.threads_are_running(thread_list):
                time.sleep(0.01)
                continue
            else:
                break

        util.done_with_socket(data_sock)
        util.done_with_socket(control_sock)

        print("client ended", flush=True)
