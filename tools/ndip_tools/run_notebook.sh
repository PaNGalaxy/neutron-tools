#!/usr/bin/env bash

while /bin/true; do
    cp $1 $2
    sleep 1
done &
lpid=$!

jupyter lab --allow-root --no-browser --NotebookApp.shutdown_button=True
wait $!
wait $lpid