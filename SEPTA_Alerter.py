import csv
import datetime
import json
import logging
from logging.handlers import RotatingFileHandler
import os
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
		trainsToCheck = getTrainsToCheck()

		if len(trainsToCheck) == 0:
			logging.getLogger('logger').info("No trains to check")
			return
		else:
			status = 'Looking for trains: '
			for train in trainsToCheck:
				train['found'] = False
				status += train['trainNum'].rstrip() + ' '
			logging.getLogger('logger').info(status)

		#get the status from SEPTA
		septaStatus = requests.get(septaUrl).json()

		#evaluate status from SEPTA response
		for trainToCheck in trainsToCheck:
			for train in septaStatus:
				if train['trainno'] == trainToCheck['trainNum']:
					#this train is one we're looking to check
					trainToCheck['found'] = True
					updateStatus(train, trainToCheck)
			if trainToCheck['found'] == False:
				logging.getLogger('logger').warning('Could not find status for train ' + trainToCheck['trainNum'])
				trainNotFound(trainToCheck)
		
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
#dict keys are 'trainNum', 'email', 'start', 'stop', 'threshold', 'days'
def getTrainsToCheck():
	f = open('trains.csv', 'r')
	if (f.mode != 'r'):
		raise Error('Could not open trains.json');
		return
	alerts = csv.DictReader(f)

	returnList = []
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
				removeStatusFile(alert)
		else:
			removeStatusFile(alert)
	
	return returnList
	
def getDayOfWeekString():
	days = ['M','Tu','W','Th','F','Sa','Su']
	return days[datetime.datetime.now().weekday()]	

def removeStatusFile(trainToCheck):
	#remove status file if it exists
	statusFileName = getStatusFileName(trainToCheck)
	if os.path.exists(statusFileName):
		os.remove(statusFileName)

def updateStatus(train, trainToCheck):
	late = train['late']
	if isInt(late) != True:
		#make sure 'late' is an int
		logging.getLogger('logger').error('Train %s late status is not an Int:' % train['trainno'])
		logging.getLogger('logger').error(train)
		return
	late = int(late)
	
	#check for existence of statusFile
	statusFilename = getStatusFileName(trainToCheck)
	try :
		f = open(statusFilename, 'r')
		#if open() doesn't throw, the file exists.  Keep sending updates until late == 0
		lastLate = f.readline()
		f.close()
		if isInt(lastLate):
			#compare to current late time
			if int(lastLate) != late:
				#send an update email
				sendTrainLateEmail(trainToCheck, late)
		else:
			#delete the status file, log error. send a message to the client
			os.remove(statusFile)
			logging.getLogger('logger').error('File ' + statusFIleName + ' had invalid status "' + lastLate + '"')
			sendTrainLateEmail(trainToCheck, late)

		#close the status file
		f.close()
	except:
		#file does not exist.  Only send if late is greater than threshold
		threshold = trainToCheck['threshold']
		if isInt(threshold) and late >= int(threshold):
			sendTrainLateEmail(trainToCheck, late)
		else:
			logging.getLogger('logger').info('Train ' + trainToCheck['trainNum'] + ' does not exceed threshold (' + threshold + ').'

	#if the train is no longer late, delete the status file
	if late == 0:
		os.remove(statusFile)

def getStatusFileName(trainToCheck):
	return trainToCheck['trainNum'] + '.' + trainToCheck['email'] + '.status'

def createStatusFile(filename, late):
	f = open(filename, 'w')
	f.write(str(late))
	f.close()

def sendTrainLateEmail(trainToCheck, late):
	logging.getLogger('logger').info('Sending status email to ' + trainToCheck['email'] + '. Train ' + trainToCheck['trainNum'] + ' is ' + str(late) + ' minutes late.')
	sendEmail(trainToCheck['email'], 'Train ' + trainToCheck['trainNum'] + ' is ' + str(late) + ' minutes late.')
	createStatusFile(getStatusFileName(trainToCheck), late)

def trainNotFound(trainToCheck):
	#send an email notifying the user that the train doesn't have a status (presumably isn't running).
	sendEmail(trainToCheck['email'], 'Couldn\'t find Train %s status!' % trainToCheck['trainNum'])
	logging.getLogger('logger').warning('Sent email to %s notifying about lack of train status' % trainToCheck['email'])

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

def isInt(str):
	try:
		int(str)
		return True
	except:
		return False

main()
