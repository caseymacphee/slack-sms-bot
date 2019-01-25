#!/bin/bash
CWD=`pwd`
if [ -f "$CWD/sms_slackbot.zip" ]
then
    rm $CWD/sms_slackbot.zip
fi
echo "Adding application files"
zip -r9 $CWD/sms_slackbot.zip logger.py
zip -r9 $CWD/sms_slackbot.zip sms_command.py
zip -r9 $CWD/sms_slackbot.zip common.py
zip -r9 $CWD/sms_slackbot.zip settings.py
echo "------------------------------------------"
echo "Adding site packages..."
cd $VIRTUAL_ENV/lib/python2.7/site-packages/
echo `pwd`
sleep 1
zip -r9 $CWD/sms_slackbot.zip *
echo "------------------------------------------"
echo "Adding site packages (lib64)..."
cd $VIRTUAL_ENV/lib64/python2.7/site-packages/
echo `pwd`
sleep 1
zip -r9 $CWD/sms_slackbot.zip *
