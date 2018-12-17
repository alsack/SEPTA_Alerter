# SEPTA_Alerter
Send notifications to email addresses if SEPTA trains are running late.

This is a python script to check the SEPTA REST API and send out an email if train(s) are running late.  It is intended to be run periodically (such as by a cron job) from the root directory of this project.

Example crontab entry:

*/5 * * * * cd /home/username/git/SEPTA_Alerter/ && python SEPTA_Alerter.py
