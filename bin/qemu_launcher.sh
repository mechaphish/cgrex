#!/bin/bash

set -x

echo "qemu_launcher.sh START"

echo "$1 $2 $4"
socat -d -d TCP-LISTEN:0,bind=localhost,reuseaddr EXEC:"timeout -k 70 65 $1 $2 $4" &
PID=$!

#wait for nc opening the port
netstat -ltunp 2>/dev/null | grep " $PID/" > /dev/null
STATUS=$?
while [ $STATUS -eq 1 ]
do
    sleep 1
    netstat -ltunp 2>/dev/null | grep " $PID/" > /dev/null
    STATUS=$?
    echo "waiting for socat..."
done
#echo `cat /proc/$PID/cmdline` ###

PORT=`netstat -ltunp 2>/dev/null | grep " $PID/" | awk -F':' '{print $2}' | awk -F' ' '{print $1}'`
echo "port is $PORT"
./cb-replay_mod --timeout 60 --host 127.0.0.1 --port $PORT $3

sleep 1 #giving qemu time to write everything, this is bad, but other solutions are bad too
kill -9 $PID

echo "qemu_launcher.sh END"

