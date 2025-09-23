# Copyright (c) 2024 Cloudflare, Inc.
# Licensed under the Apache 2.0 license found in the LICENSE file or at https://www.apache.org/licenses/LICENSE-2.0

import socket
import struct

from .exceptions import PeerDisconnectedException


def recv_exact_num_bytes(data_sock, total_num_bytes_to_read):
    payload_bytes = bytearray()
    num_bytes_read = 0

    while num_bytes_read < total_num_bytes_to_read:

        num_bytes_remaining = total_num_bytes_to_read - num_bytes_read

        recv_bytes = data_sock.recv(num_bytes_remaining)

        if len(recv_bytes) == 0:
            raise PeerDisconnectedException()

        num_bytes_received = len(recv_bytes)

        if num_bytes_received == 0:
            raise PeerDisconnectedException()

        num_bytes_read += num_bytes_received

        payload_bytes.extend(recv_bytes)

    return payload_bytes


def get_congestion_control(data_sock):
    cc_algo_bytes = data_sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_CONGESTION, 1024)
    # cc_algo is null-terminated bytes
    cc_algo_str = cc_algo_bytes.split(b'\x00')[0].decode()
    return cc_algo_str


def set_congestion_control(client_args, data_sock):
    if get_congestion_control(data_sock) == client_args.congestion:
        # already set, nothing to do here
        return

    data_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_CONGESTION, client_args.congestion.encode())

    cc_algo_str = get_congestion_control(data_sock)
    if cc_algo_str != client_args.congestion:
        raise Exception("ERROR: unexpected congestion control in effect: {}".format(cc_algo_str))


def set_tcp_notsent_lowat(data_sock):
    lowat_value = 128 * 1024
    lowat_val_bytes = struct.pack('I', lowat_value)
    data_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NOTSENT_LOWAT, lowat_val_bytes)
