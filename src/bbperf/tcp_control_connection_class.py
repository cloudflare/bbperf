# Copyright (c) 2024 Cloudflare, Inc.
# Licensed under the Apache 2.0 license found in the LICENSE file or at https://www.apache.org/licenses/LICENSE-2.0

import json
import argparse
import socket
import select

from . import const
from . import util

from .exceptions import PeerDisconnectedException

# this needs to be serializable to get from driver to child thread
class TcpControlConnectionClass:

    # class variables

    def __init__(self, control_sock):
        self.control_sock = control_sock
        self.args = None

        self.read_buffer = bytearray()

        # set TCP_NODELAY because the control messages back to the
        # sender from the data receiver are part of the RTT measurement
        control_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)


    def set_args(self, args):
        self.args = args


    def send_bytes(self, payload_bytes):
        self.control_sock.sendall(payload_bytes)

        if self.args.verbosity > 3:
            print("control conn sending: {}".format(payload_bytes.decode()), flush=True)


    def send_string(self, str0):
        self.send_bytes(str0.encode())


    def send_control_initial_string(self, run_id):

        control_initial_string = "control " + run_id

        if self.args.verbosity:
            print("sending control initial string: {}".format(control_initial_string), flush=True)

        self.send_string(control_initial_string)

        if self.args.verbosity:
            print("sent control initial string", flush=True)


    def wait_for_control_initial_string(self):

        print("waiting to receive control initial string from client", flush=True)

        # "control " + uuid of 36 characters
        len_str = 8 + 36

        received_bytes = self.recv_exact_num_bytes(len_str)

        received_str = received_bytes.decode()

        uuid = received_str[8:]

        print("received control initial string: run_id: {}".format(uuid), flush=True)

        return uuid


    def send_control_initial_ack(self):

        print("sending control initial ack", flush=True)

        self.send_string(const.TCP_CONTROL_INITIAL_ACK)

        print("sent control initial ack", flush=True)


    def wait_for_control_initial_ack(self):

        if self.args.verbosity:
            print("waiting for control initial ack", flush=True)

        received_bytes = self.recv_exact_num_bytes(len(const.TCP_CONTROL_INITIAL_ACK))

        received_str = received_bytes.decode()

        if received_str != const.TCP_CONTROL_INITIAL_ACK:
            raise Exception("ERROR: received invalid control initial ack: {}".format(received_str))

        if self.args.verbosity:
            print("received control initial ack", flush=True)


    def send_args_to_server(self, args):

        if self.args.verbosity:
            print("sending args to server: {}".format(vars(args)), flush=True)

        args_json = json.dumps(vars(args))

        self.send_string(args_json)

        if self.args.verbosity:
            print("sent args to server", flush=True)


    def wait_for_args_from_client(self):

        print("waiting for args from client", flush=True)

        # starts with "{" and ends with "}"

        substr_idx = self.recv_into_buffer_until_substr_found(b'}')

        received_bytes = self.read_buffer[ 0 : substr_idx + 1 ]
        self.read_buffer = self.read_buffer[ substr_idx + 1 : ]

        received_str = received_bytes.decode()

        args_d = json.loads(received_str)

        # recreate args as if it came directly from argparse
        args = argparse.Namespace(**args_d)

        print("received args from client: {}".format(vars(args)), flush=True)

        return args


    def send_control_args_ack(self):

        print("sending control args ack", flush=True)

        self.send_string(const.TCP_CONTROL_ARGS_ACK)

        print("sent control args ack", flush=True)


    def wait_for_control_args_ack(self):

        if self.args.verbosity:
            print("waiting for control args ack", flush=True)

        received_bytes = self.recv_exact_num_bytes(len(const.TCP_CONTROL_ARGS_ACK))

        received_str = received_bytes.decode()

        if received_str != const.TCP_CONTROL_ARGS_ACK:
            raise Exception("ERROR: received invalid control args ack: {}".format(received_str))

        if self.args.verbosity:
            print("received control args ack", flush=True)


    def send_setup_complete_message(self):

        if self.args.verbosity:
            print("sending setup complete message to client", flush=True)

        self.send_string(const.SETUP_COMPLETE_MSG)

        if self.args.verbosity:
            print("sent setup complete message to client", flush=True)


    def wait_for_setup_complete_message(self):

        if self.args.verbosity:
            print("waiting for connection setup complete message from server", flush=True)

        received_bytes = self.recv_exact_num_bytes(len(const.SETUP_COMPLETE_MSG))

        received_str = received_bytes.decode()

        if received_str != const.SETUP_COMPLETE_MSG:
            raise Exception("ERROR: client_mainline: setup complete message was not received")

        if self.args.verbosity:
            print("connection setup complete message received from server", flush=True)


    def send_start_message(self):

        if self.args.verbosity:
            print("sending start message to server", flush=True)

        self.send_string(const.START_MSG)

        if self.args.verbosity:
            print("sent start message to server", flush=True)


    def wait_for_start_message(self):

        if self.args.verbosity:
            print("waiting for start message from client", flush=True)

        received_bytes = self.recv_exact_num_bytes(len(const.START_MSG))

        received_str = received_bytes.decode()

        if received_str != const.START_MSG:
            raise Exception("ERROR: failed to receive start message")

        if self.args.verbosity:
            print("received start message from client", flush=True)


    def recv(self, max_bytes_to_read):
        # block here because we don't want the recv() to block indefinitely
        rlist, _, _ = select.select( [self.control_sock], [], [], const.SOCKET_TIMEOUT_SEC)

        if len(rlist) == 0:
            raise Exception("ERROR: select() timed out")

        recv_bytes = self.control_sock.recv(max_bytes_to_read)

        if len(recv_bytes) == 0:
            raise PeerDisconnectedException()

        self.read_buffer.extend(recv_bytes)


    def recv_into_buffer_until_minimum_size(self, minimum_buffer_size):

        while len(self.read_buffer) < minimum_buffer_size:

            num_bytes_remaining = minimum_buffer_size - len(self.read_buffer)

            self.recv(num_bytes_remaining)


    def recv_exact_num_bytes(self, exact_num_bytes_to_read):

        self.recv_into_buffer_until_minimum_size(exact_num_bytes_to_read)

        received_bytes = self.read_buffer[ 0 : exact_num_bytes_to_read ]
        self.read_buffer = self.read_buffer[ exact_num_bytes_to_read : ]

        return received_bytes


    def recv_into_buffer_until_substr_found(self, substr_bytes):

        while True:

            substr_idx = self.read_buffer.find(substr_bytes)
            if substr_idx > -1:
                # found
                break

            self.recv(const.BUFSZ)

        return substr_idx


    def recv_a_c_block(self):
        start_bytes = b' a '
        end_bytes = b' c '

        substr_idx = self.recv_into_buffer_until_substr_found(end_bytes)

        received_bytes = self.read_buffer[ 0 : substr_idx + 3 ]
        self.read_buffer = self.read_buffer[ substr_idx + 3 : ]

        if not (received_bytes.startswith(start_bytes) and received_bytes.endswith(end_bytes)):
            raise Exception("recv_a_c_block failed")

        return received_bytes


    def recv_a_d_block(self):
        start_bytes = b' a '
        end_bytes = b' d '

        substr_idx = self.recv_into_buffer_until_substr_found(end_bytes)

        received_bytes = self.read_buffer[ 0 : substr_idx + 3 ]
        self.read_buffer = self.read_buffer[ substr_idx + 3 : ]

        if not (received_bytes.startswith(start_bytes) and received_bytes.endswith(end_bytes)):
            raise Exception("recv_a_d_block failed")

        return received_bytes


    def close(self):
        util.done_with_socket(self.control_sock)
