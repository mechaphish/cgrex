#!/bin/bash

set -x

./qemu-cgc  -D "$2/qemu_log.txt" -d exec,circular,in_asm $1 

