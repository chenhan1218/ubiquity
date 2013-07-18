#!/bin/sh -eux

#
# This script runs autopilot
#

# Copyright © 2013 Canonical Ltd.
# Author: Jean-baptiste Lallement <jean-baptiste.lallement@canonical.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

# Required to display stdout in ~/.xsession-error

TESTBASE=/var/local/autopilot/
AP_ARTIFACTS=$TESTBASE/videos/
AP_RESULTS=$TESTBASE/junit/
AP_TESTSUITES=$TESTBASE/testsuites
AP_LOGFILE=$TESTBASE/autopilot.log
SPOOLDIR=$TESTBASE/spool
AP_OPTS="-v -f xml"
RMD_OPTS="-r -rd $AP_ARTIFACTS"
# TESTING ONLY -- Recording is disabled
AP_OPTS="-v -f xml"
OTTO_SUMMARY=/var/local/otto/summary.log
TSBRANCH=lp:~dpniel/ubiquity/autopilot
TSEXPORT=$HOME/ubiquity-autopilot
SHUTDOWN=1

PACKAGES="bzr ssh python-autopilot libautopilot-gtk python-xlib"

# Define general configuration files 
[ -f $TESTBASE/config ] && . $TESTBASE/config

usage() {
    cat<<EOF
Usage: $(basename $0) [OPTIONS...]
Run autopilot tests in $SPOOLDIR

Options:
  -h, --help      This help
  -d, --debug     Enable debug mode
  -N, --new       Restart all the tests in $AP_TESTSUITES otherwise
                  only the remaining tests in $SPOOLDIR are run
  -R, --norecord  Do not use recordmydesktop.
  -S, --noshutdown
                  Do not shutdown the system after the tests

EOF
    exit 1
}

setup_tests() {
    # Prepares the environment for the tests
    flag=$HOME/.ap_setup_done

    [ -e "$flag" ] && return 0

    xterm &
    tail_logs /home/ubuntu/.cache/upstart/gnome-session.log
    # Disable notifications and screensaver
    if which gsettings >/dev/null 2>&1; then 
        echo "I: Disabling crash notifications"
        gsettings set com.ubuntu.update-notifier show-apport-crashes false
        echo "I: Disabling screensaver"
        gsettings set org.gnome.desktop.screensaver idle-activation-enabled false
    fi

    # Loads the list of test and queue them in test spool
    sudo mkdir -p $SPOOLDIR $AP_ARTIFACTS $AP_RESULTS $(dirname $OTTO_SUMMARY)
    sudo chown -R $USER:$USER $TESTBASE $SPOOLDIR $AP_ARTIFACTS $AP_RESULTS $(dirname $OTTO_SUMMARY)

    echo "I: Installating additional packages"
    sudo apt-get update
    sudo apt-get install -yq $PACKAGES

    bzr export $TSEXPORT $TSBRANCH
    # See README in ubiquity ap branch for details
    sudo cp $TSEXPORT/bin/ubiquity-wrapper /usr/bin/ubiquity
    sudo cp $TSEXPORT/bin/ubiquity /usr/lib/ubiquity/bin/ubiquity
    sudo chmod +x /usr/bin/ubiquity /usr/lib/ubiquity/bin/ubiquity

    touch $flag
}

shutdown_host() {
    # Shutdown host
    if [ $SHUTDOWN -eq 1 ]; then
        echo "I: Shutting down test environment"
        sudo shutdown -h now
    else
        echo "I: Shutdown disabled, host will keep running"
    fi
}

tail_logs() {
    # Tail log files in -F mode in background
    #   
    # $@ List of log files
    for log in $@; do
        if [ -f "$log" ]; then
            sudo sh -c "/bin/busybox tail -n0 -f $log | mawk -Winteractive -v logfile=\"$log\" '{print logfile\":\",\$0}' > /dev/ttyS1" &
        fi
    done
    }


run_tests() {
    # Runs all the tests in spooldir
    #
    # $1: Spool directory
    spooldir=$1
    if [ ! -d $spooldir ]; then
        echo "E: '$spooldir is not a directory. Exiting!"
        exit 1
    fi

    if ! which autopilot >/dev/null 2>&1; then
        echo "E: autopilot is required to run autopilot tests"
        echo "autopilot_installed (see autopilot.log for details): ERROR" >> $OTTO_SUMMARY
        shutdown_host
        exit 1
    fi
    echo "autopilot_installed: PASS" >> $OTTO_SUMMARY

    exec >>$AP_LOGFILE
    exec 2>&1
    touch $AP_LOGFILE
    tail_logs $AP_LOGFILE

    echo "I: Launching Ubiquity"
    cd $TSEXPORT/autopilot
    ./run_ubiquity &
    sleep 30
    tail_logs /var/log/installer/debug
    for testname in ubiquity; do
        # We don't want to fail if AP fail but we want the return code
        set +e  
        echo "I: Running autopilot run $testname $AP_OPTS -o $AP_RESULTS/$testname.xml"
        ./autopilot run -v $testname
        AP_RC=$?
        if [ $AP_RC -gt 0 ]; then
            echo "${testname}: FAIL" >> $OTTO_SUMMARY
        else
            echo "${testname}: DONE" >> $OTTO_SUMMARY
        fi
        set -e
    done

    shutdown_host
}

reset_test() {
    # Reset the tests for a new run
    rm -f $HOME/.ap_setup_done $OTTO_SUMMARY $AP_LOGFILE $SPOOLDIR/* $AP_ARTIFACTS/* $AP_RESULTS/*
}
SHORTOPTS="hdNRS"
LONGOPTS="help,debug,new,norecord,noshutdown"

TEMP=$(getopt -o $SHORTOPTS --long $LONGOPTS -- "$@")
eval set -- "$TEMP"

while true ; do
    case "$1" in
    -h|--help)
        usage;;
    -d|--debug)
        set -x
        shift;;
    -N|--new)
        reset_test
        shift;;
    -R|--norecord)
        RMD_OPTS=""
        shift;;
    -S|--noshutdown)
        SHUTDOWN=0
        shift;;
    --) shift;
        break;;
    *) usage;;
    esac
done

# Specific option for recordmydesktop for unity tests
# It is suspected to caused memory fragmentation and make the test crash
if [ -e "$AP_TESTSUITES" ]; then
    if grep -qw "unity" "$AP_TESTSUITES" 2>/dev/null; then
        RMD_OPTS="$RMD_OPTS --record-options=--fps=6,--no-wm-check"
    fi
fi

if which recordmydesktop >/dev/null 2>&1; then
    AP_OPTS="$AP_OPTS $RMD_OPTS"
fi

setup_tests
run_tests $SPOOLDIR
