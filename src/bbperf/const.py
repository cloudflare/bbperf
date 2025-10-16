# Copyright (c) 2024 Cloudflare, Inc.
# Licensed under the Apache 2.0 license found in the LICENSE file or at https://www.apache.org/licenses/LICENSE-2.0

BBPERF_VERSION = "0.0.28"

SERVER_PORT = 5301

DEFAULT_VALID_DATA_COLLECTION_TIME_SEC = 20

# max duration for calibration phase
MAX_DURATION_CALIBRATION_TIME_SEC = 20

# cap the amount of time we will wait for valid data
MAX_DATA_COLLECTION_TIME_WITHOUT_VALID_DATA = 60

# ignore incoming data for this amount of time after starting data collection phase
DATA_SAMPLE_IGNORE_TIME_ALWAYS_SEC = 1
DATA_SAMPLE_IGNORE_TIME_TCP_MAX_SEC = 5
DATA_SAMPLE_IGNORE_TIME_UDP_MAX_SEC = 10

# for socket recv()
BUFSZ = (128 * 1024)

PAYLOAD_1K = b'a'*1024
PAYLOAD_128K = b'a'*(128 * 1024)

RUN_MODE_CALIBRATING = 1
RUN_MODE_RUNNING = 2
RUN_MODE_STOP = 3

SAMPLE_INTERVAL_SEC = 0.1
STDOUT_INTERVAL_SEC = 1

# pacing for UDP sends
UDP_BATCHES_PER_SECOND = 1000
UDP_DELAY_BETWEEN_BATCH_STARTS = (1.0 / UDP_BATCHES_PER_SECOND)
UDP_NEGATIVE_DELAY_BETWEEN_BATCHES_WARNING_EVERY = UDP_BATCHES_PER_SECOND

SETUP_COMPLETE_MSG = "setup complete"
START_MSG = " start "
UDP_STOP_MSG = "stop"
TCP_CONTROL_INITIAL_ACK = "control initial ack"
TCP_CONTROL_ARGS_ACK = "control args ack"
UDP_DATA_INITIAL_ACK = "data initial ack"

SOCKET_TIMEOUT_SEC=30

UDP_DEFAULT_INITIAL_RATE = 8000

UDP_MIN_RATE = 100
UDP_MAX_RATE = 800000
