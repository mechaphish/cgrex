#!/bin/sh
echo "test.sh START"
PORT=10000
#a problem is that we cannot have any output from pin
#not to interfere with the testing
nc -e ./pin_wrap.sh -l 127.0.0.1 -p $PORT &
PID=$!

#wait for nc opening the port
netstat -ltun | grep ":$PORT" > /dev/null
STATUS=$?
while [ $STATUS -eq 1 ]
do
	sleep 1
	netstat -ltun | grep ":$PORT" > /dev/null
	STATUS=$?
	echo "waiting for netcat..."
done
#echo `cat /proc/$PID/cmdline` ###

cb-replay --host 127.0.0.1 --port 10000  $1

echo "waiting $PID"
#echo `cat /proc/$PID/cmdline`
#wait for nc termination
wait $PID 
echo "test.sh END"

