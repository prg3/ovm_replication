#!/bin/bash

#Change these to be applicable for your environment
FROM="OVM Manager <root@yourdomain>"
TO="OVM Administrators <ovm_admins@yourdomain>"

#OVM Servers
Local=$1
Remote=$2
LOGFILE=/var/log/replication.log

if [ -f '/tmp/repl_email.out' ] ; then
	rm /tmp/repl_email.out
fi

if [ -f '/tmp/replication.out' ] ; then
	rm /tmp/replication.out
fi

replscript="/usr/bin/replication.py"

cd /tmp
rm -f $LOGFILE

Year=`date +%Y`
Month=`date +%m | sed s/0//g`
#Detect which days are Saturdays in the month
Sat_1=`python -c "import calendar; print calendar.monthcalendar($Year, $Month)[0][5]"`
Sat_2=`python -c "import calendar; print calendar.monthcalendar($Year, $Month)[1][5]"`
Sat_3=`python -c "import calendar; print calendar.monthcalendar($Year, $Month)[2][5]"`
Sat_4=`python -c "import calendar; print calendar.monthcalendar($Year, $Month)[3][5]"`
Sat_5=`python -c "import calendar; print calendar.monthcalendar($Year, $Month)[4][5]"`

case `date +%d` in
	$Sat_1 ) $replscript Snap_monthly_1 $Local $Remote >> $LOGFILE;;
	$Sat_2 ) $replscript Snap_monthly_2 $Local $Remote >> $LOGFILE;;
	$Sat_3 ) $replscript Snap_monthly_3 $Local $Remote >> $LOGFILE;;
	$Sat_4 ) $replscript Snap_monthly_4 $Local $Remote >> $LOGFILE;;
	$Sat_5 ) $replscript Snap_monthly_5 $Local $Remote >> $LOGFILE;;
	esac

case `date +%A` in
	Sunday ) $replscript Snap_sunday $Local $Remote >> $LOGFILE;;
	Monday ) $replscript Snap_monday $Local $Remote >> $LOGFILE;;
	Tuesday ) $replscript Snap_tuesday $Local $Remote >> $LOGFILE;;
	Wednesday ) $replscript Snap_wednesday $Local $Remote >> $LOGFILE;;
	Thursday ) $replscript Snap_thursday $Local $Remote >> $LOGFILE;;
	Friday ) $replscript Snap_friday $Local $Remote >> $LOGFILE;;
	esac

if [ -f /tmp/replication.out ] ; then
        echo "From: $FROM" > /tmp/repl_email.out
        echo "To: $TO" >> /tmp/repl_email.out
        echo "MIME-Version: 1.0" >> /tmp/repl_email.out
        echo "Content-type: text/html" >> /tmp/repl_email.out
        echo "Subject: OVM Replication Status for `hostname`" >> /tmp/repl_email.out
        cat /tmp/replication.out >> /tmp/repl_email.out
        cat /tmp/repl_email.out | /usr/sbin/sendmail -t
fi

