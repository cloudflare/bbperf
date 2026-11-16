
import socket

def set_so_rcvbuf(args, data_sock):
    # the stored value is 2x the specified value
    # the retrieved value is the doubled value

    if not args.udp_rcvbuf:
        return

    desired_size = args.udp_rcvbuf

    expected_size = desired_size * 2

    data_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, desired_size)

    actual_size = data_sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)

    if actual_size != expected_size:
        raise Exception("ERROR: unexpected SO_RCVBUF size in effect, expected: {} actual: {}".format(
            expected_size, actual_size))
