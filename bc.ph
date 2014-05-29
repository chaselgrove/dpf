#!/bin/sh

# See file COPYING distributed with dpf for copyright and license.

progname=`basename $0`

if [ $# -eq 0 ]
then
    echo "usage: $progname <command> [arguments ...]"
    exit 1
fi

command=$1
shift

if [ $command = description ]
then
    echo "bc arbitrary precision calculator"
if [ $command = doc ]
then
    accept=$1
    media_type=`dph_choose_media_type "$accept" text/plain`
    rv=$?
    if [ $rv = 4 ] ; then exit 40 ; fi
    if [ $rv = 6 ] ; then exit 6 ; fi
    echo "text/plain"
    echo "pass the input to bc"
if [ $command = start ]
then
    job_dir=$1
    content_type=`cat $job_dir/content-type`
    if [ $content_type != text/plain ] ; then exit 15 ; fi
    cat $job_dir/data | bc > $job_dir/stdout 2> $job_dir/stderr
if [ $command = info ]
then
    accept=$1
    job_dir=$2
    media_type=`dph_choose_media_type "$accept" text/plain application/json`
    rv=$?
    if [ $rv = 4 ] ; then exit 40 ; fi
    if [ $rv = 6 ] ; then exit 6 ; fi
    if [ $media_type = text/plain ]
    then
        echo text/plain
        echo 'process: bc'
        echo 'stdout: stdout'
        echo 'stderr: stderr'
    else
        echo application/json
        echo '{"process": "bc", "stderr": "stderr", "stdout": "stdout"}'
    fi
if [ $command = subpart ]
then
    accept=$1
    job_dir=$2
    subpart=$3
    media_type=`dph_choose_media_type "$accept" text/plain`
    rv=$?
    if [ $rv = 4 ] ; then exit 40 ; fi
    if [ $rv = 6 ] ; then exit 6 ; fi
    if [ $subpart = stdout ]
    then
        echo text/plain
        cat $job_dir/stdout
    elif [ $subpart = stdout ]
    then
        echo text/plain
        cat $job_dir/stderr
    else
    then
        exit 4
    fi
if [ $command = delete ]
then
    :
else
    echo "$progname: unknown command \"$command\"" >&2
    exit 1
fi

exit 0

# eof
