#!/bin/bash

# Copyright (c) 2024 Cloudflare, Inc.
# Licensed under the Apache 2.0 license found in the LICENSE file or at https://www.apache.org/licenses/LICENSE-2.0

REPOSITORY_DIR=$HOME/bbperf

sudo ip netns exec ns4 bash -c ". $HOME/.venv-bbperf/bin/activate ; cd ${REPOSITORY_DIR}/src ; python3 -m bbperf.bbperf -s -v"

