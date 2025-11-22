#!/bin/bash

# Copyright (c) 2024 Cloudflare, Inc.
# Licensed under the Apache 2.0 license found in the LICENSE file or at https://www.apache.org/licenses/LICENSE-2.0

do_run() {
  ARGS=$1

  #bbperf -c $ARGS
  sudo ip netns exec ns1 bash -c ". $HOME/.venv-314/bin/activate ; cd $HOME/bbperf/src ; python3 -m bbperf.bbperf $ARGS"
}

#SERVER_ADDR=127.0.0.1
SERVER_ADDR=10.66.30.2

EXTRAARGS="-v -t 10"

set -x

do_run "-c $SERVER_ADDR $EXTRAARGS"

do_run "-c $SERVER_ADDR $EXTRAARGS -R"

do_run "-c $SERVER_ADDR $EXTRAARGS -u"

do_run "-c $SERVER_ADDR $EXTRAARGS -u -R"

EXTRAARGS="-t 10"

do_run "-c $SERVER_ADDR $EXTRAARGS"

do_run "-c $SERVER_ADDR $EXTRAARGS -R"

do_run "-c $SERVER_ADDR $EXTRAARGS -u"

do_run "-c $SERVER_ADDR $EXTRAARGS -u -R"

do_run "-c $SERVER_ADDR $EXTRAARGS -J /tmp/foo578439759837.out"

head /tmp/foo578439759837.out
tail /tmp/foo578439759837.out
sudo rm /tmp/foo578439759837.out

