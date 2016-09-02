#!/bin/sh

./qemu-cgc 2>"$2/qemu_stderr.txt" -singlestep -D "$2/qemu_log.txt" -d exec,in_asm,circular $1


