#!/usr/bin/gnuplot

# Copyright (c) 2024 Cloudflare, Inc.
# Licensed under the Apache 2.0 license found in the LICENSE file or at https://www.apache.org/licenses/LICENSE-2.0

#datafile1 = "/tmp/bbperf-udp-data-aa97m9xl"

pngfile1 = datafile1.".png"

set grid

set key right top
set key box opaque

set style data lines

# noenhanced to avoid need to escape underscores in labels
set terminal pngcairo size 1200,1300 noenhanced
set output pngfile1

# generate stats for column 2
# nooutput - do not sent to "screen"
# name - prefix
stats datafile1 using 1 nooutput name "XRANGE"

set multiplot title "bbperf UDP ".datafile1 layout 5,1

set lmargin 12

# dt 1 (solid), dt 2 (dotted), dt 4 (dot dash)
# lc 1 (purple), lc 4 (orange), lc 6 (blue), lc 7 (red), lc 8 (black)

set ylabel "pps"

plot datafile1 using ($1-XRANGE_min):5 title "receiver pps" lw 2 lc 6, \
     ""        using ($1-XRANGE_min):3 title "sender pps"   lw 2 lc 1 dt 2

set ylabel "Mbps"

plot datafile1 using ($1-XRANGE_min):6 title "receiver throughput" lw 2 lc 6, \
     ""        using ($1-XRANGE_min):4 title "sender throughput"   lw 2 lc 1 dt 2

set ylabel "ms"

plot datafile1 using ($1-XRANGE_min):7 title "unloaded RTT" lw 2 lc 1, \
     ""        using ($1-XRANGE_min):8 title "RTT"          lw 2 lc 6

set ylabel "bytes"

plot datafile1 using ($1-XRANGE_min):9  title "BDP"           lw 2 lc 1, \
     ""        using ($1-XRANGE_min):10 title "buffered data" lw 2 lc 6

set ylabel "percent"

plot datafile1 using ($1-XRANGE_min):13 title "pkt loss %"  lw 2 lc 6

unset multiplot

