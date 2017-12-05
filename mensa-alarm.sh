#!/bin/bash

# this script calls parse_mensa.py (located in your home directory) and checks for certain meals in the mensa
# if no argument is specified, Käsespätzle is assumed by default
# a notification is send to the desktop environment, it has to support desktop notifications
# you can run this script as a cron job, e.g. every monday at 11:
#	add a new cron job by calling "crontab -e"
#	add the line "0 11 * * 1 /path/to/mensa_alarm.sh (dish)"

if [[ "$(command -v notify-send)" == "" ]]; then
	echo "notify-send not found. Make sure notifications are supported by your system"
	exit 1
fi

dish=$1
[ "$dish" == "" ] && dish='Käsespätzle'

ret=$($HOME/parse_mensa.py --no-detail check $dish)

if [[ $? == 0 ]]; then
	notify-send "${dish} Alarm!" "${ret}" -i dialog-warning -u critical
fi
