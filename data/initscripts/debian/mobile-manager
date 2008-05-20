#! /bin/sh
#
# skeleton	example file to build /etc/init.d/ scripts.
#		This file should be used to construct scripts for /etc/init.d.
#
#		Written by Miquel van Smoorenburg <miquels@cistron.nl>.
#		Modified for Debian 
#		by Ian Murdock <imurdock@gnu.ai.mit.edu>.
#
# Version:	@(#)skeleton  1.9  26-Feb-2001  miquels@cistron.nl
#

PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
DAEMON=/usr/sbin/MobileManagerDaemon
NAME="mobile-manager"
DESC="mobile-manager (GPRS/3G Manager)"

test -x $DAEMON || exit 0

# Include mobile-manager defaults if available
if [ -f /etc/default/mobile-manager ] ; then
	. /etc/default/mobile-manager
fi

set -e

remove_old_pid()
{
    PIDFILE=/var/run/$1.pid
    DAEMON=$2

    if [ -e $PIDFILE ]; then
        PIDDIR=/proc/$(cat $PIDFILE)
        if [ -d ${PIDDIR} -a  "$(readlink -f ${PIDDIR}/exe)" = "${DAEMON}" ]; then
            echo "$1 : already started; not starting."
        else
            if test -e $PIDDIR/cmdline && grep $1 $PIDDIR/cmdline > /dev/null  ;
            then
                echo "$1 : already started; not starting."
            else
                echo "Removing stale PID file $PIDFILE."
                rm -f $PIDFILE
            fi
        fi
    fi
}


case "$1" in
  start)
	remove_old_pid $NAME $DAEMON
        if [ ! -e /var/run/$NAME.pid ] ;
        then
            echo -n "Starting $DESC_PPP: "
            start-stop-daemon --start --quiet --pidfile /var/run/$NAME.pid \
                --exec $DAEMON -- --pid-file=/var/run/$NAME.pid
            echo "$NAME."
        fi

	;;
  stop)
	if [ -e /var/run/$NAME.pid ] ;
        then
            echo -n "Stopping $DESC: "
            start-stop-daemon --stop -s 9 --pidfile /var/run/$NAME.pid
            test -e /var/run/$NAME.pid && rm /var/run/$NAME.pid
            echo "$NAME."
        else
            test -e /var/run/$NAME.pid && rm /var/run/$NAME.pid
            killall -9 MobileManagerDaemon 2> /dev/null || echo "No MobileManagerDaemon killed"
        fi
	;;
  
  restart|force-reload)
	$0 stop
	sleep 1
	$0 start
	;;
  *)
	N=/etc/init.d/$NAME
	# echo "Usage: $N {start|stop|restart|reload|force-reload}" >&2
	echo "Usage: $N {start|stop|restart|force-reload}" >&2
	exit 1
	;;
esac

exit 0
