<p align="center"><strong>bbperf</strong> <em>- An end-to-end performance and bufferbloat measurement tool</em></p>

`bbperf` measures what matters most.

Traditional network performance measurement tools collect metrics such as latency and throughput regardless of the conditions that exist during the collection period.  While valuable for many uses, that approach can miss reporting the actual performance that real user payloads experience on production networks.  This tool only reports performance metrics when the flow is operating at "max buffer usage".  Max buffer usage is when the active flow has filled any and all buffers that exist along the packet path between the endpoints.

User payload is used to measure latency and throughput.  This accounts for the performance impact of transparent proxies, transparent tunnels, transparent firewalls, and all the other things that are not visible to the endpoints.  It also simplifies the interpretation of retransmissions on user performance, which is non-intuitive at best.  This is because some retransmissions are due to the real loss of user payload while many are not.  In this tool, the loss of user payload will show up in the latency and throughput metrics, i.e. higher latencies and lower throughput.

Features:

* Latency, both unloaded and loaded, is measured by the same flow that is under test.

    Other tools will commonly measure latency using a different flow or different protocol.  One of the reasons why using different protocols and/or different flows is not desirable is because fair queuing will cause the latency of those other flows to be much lower (better) than the flow that matters.

* Throughput

    Both sender and receiver rates are collected, but the receiver rate (a.k.a. goodput) is the important one.

* Bufferbloat is calculated

    It is often assumed that TCP receive buffers are the only source of bufferbloat.  While that is common, it misses many other locations where bufferbloat may occur.  This tool reports the effects of all sources of bufferbloat, not just TCP receive buffers.

    `bbperf` calculates both the BDP (bandwidth delay product) and the total amount of buffer actually used.  The difference between those two is reported as "excess buffer usage".  A small number for this metric is normal and expected, but a large number, relative to BDP, is bufferbloat.  Bufferbloat also appears as a large difference between unloaded and loaded latency.

* Both TCP and UDP are supported

    Both benchmark tests will wait until it has reached "max buffer usage" before collecting metrics data.  For TCP, it will wait for the sending and receiving rates to match.  For UDP, the sending rate will be automatically adjusted to be just above the maximum packet rate without dropping packets before starting its metrics collection.

* `bbperf` measures the performance of data flow in one direction only.

    Network routing can be asymmetric, bottleneck links are asymmetric, bufferbloat is asymmetric, all of which means that performance is asymmetric.  `bbperf` allows us to see the asymmetry.

    Data flow in `bbperf` is one way.  The direction of data flow is from the client host to the server host (unless the `-R` option is specified).  That is the direction being measured, and is what is reported in the metrics.

    Latency is measured round trip, but the return traffic (from the data receiver back to the data sender) is low-volume and should not contribute any bufferbloat-related latency to the measurement.  This cannot be guaranteed, in the same way that it cannot be guaranteed that the unloaded latency measurement does not contain any bufferbloat-induced latency.  But it does ensure that no bufferbloat-induced latency is cause by `bbperf`s own flow.

* Automatic generation of graphs

### Usage

To run a test:

1. Start the server on one host
```
    $ bbperf.py -s
```

2. Run the client on another host
```
    $ bbperf.py -c <ip address of server> [additional options as desired]
```

`bbperf` will use port 5301 between the client and server (by default).

The first few seconds performs a calibration, during which it captures the unloaded latency between endpoints.

The direction of data flow is from the client to the server.  That is reversed when the "-R" option is specified.

The duration of this tool is non-deterministic.  The time option (`-t`/`--time`) specifies how long to run _after_ valid data samples are observed.  `bbperf` will automatically detect when it has enough data samples for the calibration, which establishes the unloaded latency value.  It will also not collect data samples during inital ramp up of the flow.

Should `bbperf` not detect any valid data samples for 60 seconds after calibration is complete, the tool will exit without results.  An example of when that might happen is if the sending host is cpu constrained such that no bottleneck is created on the network.

```
$ bbperf.py --help
usage: bbperf.py [-h] [-s] [-c SERVER_ADDR] [-p SERVER_PORT] [-u] [-R] [--max-ramp-time SECONDS] [-t SECONDS] [-v] [-q] [-J JSON_FILE] [-g]
                 [--graph-file GRAPH_FILE] [-k] [-B BIND_ADDR] [--local-data-port LOCAL_DATA_PORT] [-C CC_ALGORITHM]

bbperf: end to end performance and bufferbloat measurement tool

options:
  -h, --help            show this help message and exit
  -s, --server          run in server mode
  -c SERVER_ADDR, --client SERVER_ADDR
                        run in client mode (specify either DNS name or IP address)
  -p SERVER_PORT, --port SERVER_PORT
                        server port (default: 5301)
  -u, --udp             run in UDP mode (default: TCP mode)
  -R, --reverse         data flow in download direction (server to client)
  --max-ramp-time SECONDS
                        max duration in seconds before collecting data samples (tcp default: 5, udp default: 10)
  -t SECONDS, --time SECONDS
                        duration in seconds to collect valid data samples (default: 20)
  -v, --verbosity       increase output verbosity (can be repeated)
  -q, --quiet           decrease output verbosity (can be repeated)
  -J JSON_FILE, --json-file JSON_FILE
                        JSON output file
  -g, --graph           generate graph and save in tmp file (requires gnuplot)
  --graph-file GRAPH_FILE
                        generate graph and save in the specified file (requires gnuplot)
  -k, --keep            keep data file
  -B BIND_ADDR, --bind BIND_ADDR
                        bind server sockets to address
  --local-data-port LOCAL_DATA_PORT
                        local port for data connection (default: ephemeral)
  -C CC_ALGORITHM, --congestion CC_ALGORITHM
                        congestion control algorithm (default: cubic)
```

Output from `bbperf` includes the following information:
```
    sent_time       time when a packet was sent
    recv_time       time when a packet was received
    sender_pps      packets per second sent
    sender_Mbps     bits per second sent
    receiver_pps    packets per second received
    receiver_Mbps   bits per second received
    unloaded_rtt_ms unloaded RTT in milliseconds (determined during calibration)
    rtt_ms          RTT in milliseconds
    BDP_bytes       Calculated BDP in bytes
    buffered_bytes  Actual bytes in flight
    bloat           Ratio of buffered bytes to BDP
    pkts_dropped    number of packets dropped (UDP only)
    drop%           percentage of packets dropped (UDP only)
```

Output to standard out is controlled via the `--verbosity` and `--quiet` options as follows:
```
    -qq           nothing to stdout except errors
    -q            run summary in json format only (no interval output)
(neither option)  progress update once per second plus run summary in json format (default)
    -v            plus one-time messages showing progress setting up and running the test
    -vv           plus rate change events (udp only)
    -vvv          plus interval output at the rate of one per 0.1 seconds
    -vvvv         plus all control connection messages
```

### Installation

`bbperf` is available via PyPI repository (pypi.org) and can be installed using pip.

```
python3 -m venv bbperf-venv
. bbperf-venv/bin/active
pip install bbperf

bbperf.py [options]
```

In the event python3 is not already installed on the host:

```
apt-get install python3 python3-pip  (Debian/Ubuntu)
dnf install python3 python3-pip      (Fedora/RHEL)
```

---
Copyright (c) 2024 Cloudflare, Inc.<br/>
Licensed under the Apache 2.0 license found in the LICENSE file or at https://www.apache.org/licenses/LICENSE-2.0

