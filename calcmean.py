import argparse
import urllib
import mechanize
import cookielib
from bs4 import BeautifulSoup
import hashlib
import re
from unidecode import unidecode
from exportfuction import extractdata
from tabulate import tabulate
import os.path
import ConfigParser
import time
import datetime

class Error(Exception):
        """Base class for exceptions in this module."""
        pass

class InputError(Error):
        """Exception raised for errors in the input.
        Attributes:
                expr -- input expression in which the error occurred
                data -- the data the expression had
                msg  -- explanation of the error
        """
        def __init__(self, expr, data, msg):
                self.expr = expr
                self.data = data
                self.msg = msg
        def __str__(self):
                return repr(self.expr+" had value "+self.data)


# Read session file
#sessiondata = ConfigParser.ConfigParser()
#sessiondata.read("sessiondata.txt")


# Parse some commandline switches
parser = argparse.ArgumentParser(description='Create a rolling mean from a EmonCMS feed')
parser.add_argument('-e','--emoncms', help='The EmonCMS base URL controller to scrape', required=True)
parser.add_argument('-a','--apikey', help='The EmonCMS ApiKey to read and write data', required=True)
parser.add_argument('-s','--srcfeed', help='The EmonCMS source feed to read from', required=True)
parser.add_argument('-d','--destfeed', help='The EmonCMS feed Destination to write Mean to', required=True)
parser.add_argument('--write', help='Really write data back to EmonCMS', required=False, action='store_true')
parser.add_argument('--starttime', help='Enter starttime Manually', required=True)

args = parser.parse_args()

# Browser
br = mechanize.Browser()

# Cookie Jar
cookiefile = "EmonCMScookiefile.txt"
cj = cookielib.LWPCookieJar()
if os.path.isfile(cookiefile):
	cj.load(cookiefile)
br.set_cookiejar(cj)

#timeout
browsertimeout = 4

#Averaging Interval
averaginginterval = 4320 #4320 equals 3 days in minutes

#print csession_id
#raise InputError("bis daheer und ned weiter")

sumdatas = []

# Browser options
br.set_handle_equiv(True)
br.set_handle_gzip(False)
br.set_handle_redirect(True)
br.set_handle_referer(True)
br.set_handle_robots(False)   # ignore robots

# Follows refresh 0 but not hangs on refresh > 0
br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)
#br.set_handle_refresh(False)  # alternatively we could turn refresh of completely

# User-Agent (this is cheating, ok?)
br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

#remember the current time
timerecord = datetime.datetime.now()

#validate manual start date
if args.starttime:
		manualstarttime = datetime.datetime.fromtimestamp(args.starttime)
		if (manualstarttimeepoch + datetime.timedelta(minutes=averaginginterval)) > timerecord:
			raise InputError("Manual Start Date + Averaginginterval",(manualstarttime + datetime.timedelta(minutes=averaginginterval)),"it should have been in the past")
else:
	manualstarttime = timerecord - datetime.timedelta(minutes=averaginginterval)

#if the minute is between 0 and 4 set minute to 0
if int(manualstarttime.strftime("%M")[1]) >= 0 and int(manualstarttime.strftime("%M")[1]) <= 4:
	#do the below stuff
	starttime = manualstarttime.replace(minute=int(manualstarttime.strftime("%M")[0]+"0"),second=0,microsecond=0)
#if the minute is between 5 and 9 set minute to 5
else:
	#do the above stuff
	starttime = manualstarttime.replace(minute=int(manualstarttime.strftime("%M")[0]+"5"),second=0,microsecond=0)



endtime = starttime + datetime.timedelta(minutes=averaginginterval)

starttimeepoch = ("%.0f" % (starttime - datetime.datetime(1970,1,1)).total_seconds()) - 60
endtimeepoch = ("%.0f" % (endtime - datetime.datetime(1970,1,1)).total_seconds()) - 60

#If we did not manually specify the start time we do the last 10 Minutes (2 Mean values)
if not args.starttime:
	starttimeepoch = starttimeepoch - 300
	endtimeepoch = endtimeepoch - 300

while endtimeepoch < ("%.0f" % (timerecord - datetime.datetime(1970,1,1)).total_seconds()):
	br.open('http://knx-server03.rdobhome/emoncms/feed/csvexport.json?id=23&start='+str(starttimeepoch)+'&end='+str(endtimeepoch)+'&interval=300&apikey=ed450805d09809d49d3fc31c11c72913',timeout=browsertimeout)
	cj.save(cookiefile)
	responsedata = br.response().read()
	responsedata = re.split('\s',responsedata)
	#The last record always seems to be empty, if so get rid of it
	if (responsedata[(len(responsedata)-1)]) == "":
		del responsedata[(len(responsedata)-1)]
	#Split the individual response lines in fields for time and value
	for index,data in enumerate(responsedata):
		responsedata[index] = re.split(",",data)
	#Iterate over all lines and build the sum
	for data in responsedata:
		sumdata += float(data[1])
	#Calculate the mean by dividing the sum by the count of rows
	mean = sumdata / (len(responsedata))
	#Write the information in a table
	sumdatas.apend((mean,responsedata[len(responsedata)-1][0]))
	starttimeepoch = starttimeepoch + 300
	endtimeepoch = endtimeepoch + 300



#print "Out of "+str(len(responsedata))+" Values the MEAN is: "+str(("%.2f" % mean))
print sumdatas


