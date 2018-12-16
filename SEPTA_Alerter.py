import csv
import datetime
import json
import logging
from logging.handlers import RotatingFileHandler
import requests
import smtplib
import sys

#global variables that will be defined later
emailUrl = emailPort = emailUser = emailPw = ''

def main():
	#initialize data from config file
	try:
		global emailUrl, emailPort, emailUser, emailPw
		emailUrl, emailPort, emailUser, emailPw, septaUrl = init()

		logging.getLogger('logger').info('Running at ' + datetime.datetime.now().ctime())
		
		#get the alerts to check for.
		checks = getTrainsToCheck()

		if len(checks) == 0:
			logging.getLogger('logger').info("No trains to check")
			return
		else:
			status = 'Looking for trains: '
			for check in checks:
				check['found'] = False
				status += check['train'].rstrip() + ' '
			logging.getLogger('logger').info(status)

		#get the status from SEPTA
		septaStatus = requests.get(septaUrl).json()

		#check its status
		for train in septaStatus:
			for check in checks:
				if train['trainno'] == check['train']:
					#this train is one we're looking to check
					check['found'] = True
					updateStatus(train, check)
		
		for check in checks:
			if check['found'] == False:
				logging.getLogger('logger').warning('Could not find status for train ' + check['train'])

		
	except:
		logging.getLogger('logger').exception("Unexpected Exception")
	
def init():
	#create error and status logger
	logger = logging.getLogger('logger')
	handler = RotatingFileHandler('log.log', maxBytes=10000, backupCount=5)
	logger.setLevel(logging.DEBUG)
	logger.addHandler(handler)

	#open file and get email info and REST URI
	f = open('config.txt','r')
	lines = f.readlines()
	if (len(lines) < 5):
		logging.getLogger('logger').error('Error reading from config.txt.  Not enough data')
		raise Error('Error reading from config.txt.  Not enough data.')
		return
	emailUrl = lines[0].rstrip()
	emailPort = lines[1].rstrip()
	emailUser = lines[2].rstrip()
	emailPw = lines[3].rstrip()
	septaUrl = lines[4].rstrip()
	return emailUrl, emailPort, emailUser, emailPw, septaUrl	

#returns a list of dictionaries corresponding to trains to check
#dict keys are 'train', 'email', 'start', 'stop', 'threshold', 'days'
def getTrainsToCheck():
	f = open('trains.csv', 'r')
	if (f.mode != 'r'):
		raise Error('Could not open trains.json');
		return
	alerts = csv.DictReader(f)

	returnList = [];
	#add the dictionary to the returnList if it is within the day/time window
	for alert in alerts:
		if getDayOfWeekString() in alert['days']:
			timeFmt = '%H:%M:%S'
			start = datetime.datetime.strptime(alert['start'], timeFmt).time()
			stop = datetime.datetime.strptime(alert['stop'], timeFmt).time()
			now = datetime.datetime.now().time()
			if now >= start and now <= stop:
				returnList.append(alert)
			else:
				#TODO: delete status file if present
				pass
	
	return returnList;
	
def getDayOfWeekString():
	days = ['M','Tu','W','Th','F','Sa','Su']
	return days[datetime.datetime.now().weekday()]	

def updateStatus(train, check):
	late = train['late']
	print('need to add logic to save status, check if late is past threshold, and send email.')
	#sendEmail(check['email'], 'test: %d' % late)
	

def sendEmail(recipient, subject):
	message = '''From: %s\nTo: %s\nSubject: %s\n\n''' % (emailUser,recipient,subject)
	server = smtplib.SMTP_SSL(emailUrl, emailPort)
	#qserver.starttls()
	server.ehlo()
	server.login(emailUser, emailPw)
	server.sendmail(emailUser, recipient, message)
	server.quit()

class Error(Exception):
	pass

main()
