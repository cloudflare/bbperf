#!/bin/bash

# Copyright (c) 2024 Cloudflare, Inc.
# Licensed under the Apache 2.0 license found in the LICENSE file or at https://www.apache.org/licenses/LICENSE-2.0

sudo ip netns exec ns4 bash -c ". $HOME/bbperf/.venv/bin/activate ; cd $HOME/bbperf/src ; python3 -m bbperf.bbperf -s -v"

