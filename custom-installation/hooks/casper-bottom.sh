#!/bin/sh

#
#  Put here every steps that must be executed on the target system and can not
#  be done with the iso-override facility
#

PREREQ=""
DESCRIPTION="Running custom script..."

prereqs()
{
       echo "$PREREQ"
}

case $1 in
# get pre-requisites
    prereqs)
       prereqs
       exit 0
       ;;
esac

. /scripts/casper-functions

log_begin_msg "$DESCRIPTION"

sed -i 's/^%admin.*/%admin ALL=(ALL) NOPASSWD: ALL/' /root/etc/sudoers

log_end_msg
