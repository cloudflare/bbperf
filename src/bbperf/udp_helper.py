# Copyright (c) 2024 Cloudflare, Inc.
# Licensed under the Apache 2.0 license found in the LICENSE file or at https://www.apache.org/licenses/LICENSE-2.0

import socket
import time

from . import const


def sendto(data_sock, peer_addr, payload_bytes):
    num_payload_bytes = len(payload_bytes)

    num_bytes_sent = data_sock.sendto(payload_bytes, peer_addr)

    if num_bytes_sent <= 0 or num_bytes_sent != num_payload_bytes:
        raise Exception("ERROR: udp_helper.sendto(): send failed")


def send_stop_message(data_sock, peer_addr):
        payload_bytes = const.UDP_STOP_MSG.encode()

        # 3 times just in case the first one does not make it to the destination
        for i in range(3):
            try:
                data_sock.sendto(payload_bytes, peer_addr)
            except (OSError, socket.error):
                # probable "ConnectionRefusedError: [Errno 111] Connection refused" here if first message was processed successfully
                pass

            time.sleep(0.1)


def wait_for_string(data_sock, peer_addr, expected_string):
    expected_bytes = expected_string.encode()
    start_time = time.time()

    while True:
        payload_bytes, pkt_from_addr = data_sock.recvfrom(len(expected_bytes))

        if pkt_from_addr != peer_addr:
            continue

        payload_str = payload_bytes.decode()

        if payload_str == expected_string:
            break

        elapsed_time = time.time() - start_time
        if elapsed_time > 60:
            raise Exception("ERROR: failed to UDP recv string: {}".format(expected_string))

