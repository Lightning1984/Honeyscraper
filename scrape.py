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
import MySQLdb


# Define our own error class
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
sessiondata = ConfigParser.ConfigParser()
sessiondata.read("sessiondata.txt")


# Parse some commandline switches
parser = argparse.ArgumentParser(description='Screen scrape data from Honeywell Excel Web controller')
parser.add_argument('-i','--ip', help='The IP of the controller to scrape', required=True)
parser.add_argument('-s','--iptwo', help='The IP of the second controller to scrape all in one go', required=False)
args = parser.parse_args()

# Browser
br = mechanize.Browser()

# Cookie Jar
cookiefile = "cookiefile.txt"
cj = cookielib.LWPCookieJar()
if os.path.isfile(cookiefile):
	cj.load(cookiefile)
br.set_cookiejar(cj)

# Honeywell Controller IP
l_controllerip = args.ip
l_controlleriptwo = args.iptwo
# Login Credentials
l_username = "SystemAdmin"
l_password = "qqqqq"

# Other Variables
l_localeid = "1033" #This is the language setting of the controller
c_session_expected_response = "4194561" #This number indicates a successful session creation
try:
	csession_id = sessiondata.get("sessiondetails", "session_id")
	session_creation_time = sessiondata.get("sessiondetails", "session_creation_time")
	#if (not csession_id) or ((time.time()-float(session_creation_time)) > 3600):
	if (not csession_id):
		csession_id = "" #Create the empty session id Variable
except:
	csession_id = "" #Create the empty session id Variable

#print csession_id
#raise InputError("bis daheer und ned weiter")

datapoints_response = []
login_response = []



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

def checksession(): #Check if we have a working login session
	global l_loginvalid
	if csession_id and l_localeid:
		parameters = [
		("SessionID" , csession_id),
		("LocaleID" , l_localeid)
		]
		posturldata = urllib.urlencode(parameters) #Encode the parameters in the proper format for posting
		br.open('http://'+l_controllerip+'/standard/mainframe.php',posturldata)
		cj.save(cookiefile)
	else:
		br.open('http://'+l_controllerip+'/standard/mainframe.php')
		cj.save(cookiefile)
	l_checksession_response = br.response().read()
	l_soup = BeautifulSoup(l_checksession_response)
	if (len(l_soup.findAll("frame"))) < 2:
		l_loginvalid = False
	else:
		l_loginvalid = True
	return l_checksession_response

def createsession(): #Function to create a valid session ID
	global csession_response_code
	global csession_id
	l_createsession = ('http://'+l_controllerip+'/standard/login/session.php')
	br.open(l_createsession)
	createsession_response = br.response().read()

	#extraction our login session ID
	soup = BeautifulSoup(createsession_response)
	# soup.script.string
	#u'\n    <!--\n      function startLogin ()\n      {\n        if (opener && opener.onSessionCreated)\n        {\n          opener.onSessionCreated ("4194561",\n                                   "azHgEvTSuJH");\n        }\n        close ();\n      }\n    //-->\n

	quoted_filter = re.compile('.*\"(.*?)\".*') #matches for everything in between two ""

	csession_response_code = quoted_filter.findall(soup.script.string)[0] #Session creation Response Code
	csession_id = quoted_filter.findall(soup.script.string)[1] #session creation ID
	del soup #clean up afterwards

	if csession_response_code != c_session_expected_response:
		raise InputError("csession_response_code",csession_response_code,"it should have been 4194561")


	#Lets get ourselfs a clean md5 object
	try:
		del md5data
	except NameError:
		pass # if it didn't exist, we don't worry

	# We create our md5 objet
	md5data = hashlib.md5()
	md5data.update(l_password) #First we hash our Password
	l_password_md5 = md5data.hexdigest()
	del md5data # cleanup

	# Then we hash the password again (honeywell is a bit dimm here I guess)
	md5data = hashlib.md5()
	md5data.update(csession_id+l_username+l_password_md5)
	l_password_concat_md5 = md5data.hexdigest()
	del md5data # cleanup

	# Finally we hash the Username
	md5data = hashlib.md5()
	md5data.update(l_username)
	l_username_md5 = md5data.hexdigest()
	del md5data # cleanup

	#Create the parameter set for the Login Post request
	parameters = [
	("SessionID" , ""),
	("LocaleID" , ""),
	("LoginDevice", l_controllerip),
	("LoginSessionID" , csession_id),
	("LoginUserNameMD5" , l_username_md5),
	("LoginPasswordMD5" , l_password_concat_md5),
	("LoginCommand" , "Login"),
	("LoginUserName" , l_username),
	("LoginPassword" , l_password)
	]
	posturldata = urllib.urlencode(parameters) #Encode the paraters in the proper Format for posting
	#This request will log us in
	br.open('http://'+l_controllerip+'/standard/mainframe.php',posturldata)
	cj.save(cookiefile)

	#Save the session id in our session file
	sessionfile = open("sessiondata.txt","w")
	try:
		sessiondata.add_section("sessiondetails")
	except:
		pass
	sessiondata.set("sessiondetails","session_id",csession_id)
	sessiondata.set("sessiondetails","session_creation_time",time.time())
	sessiondata.write(sessionfile)
	sessionfile.close()
	#Keep the response just in case
	l_createsession_response = br.response().read()
	return l_createsession_response

def getdatapage():
	global pagenum
	pagenum = 1
	#Create the parameter set to get the first Page of Datapoints
	parameters = [
	("SessionID" , csession_id),
	("LocaleID" , l_localeid)
	]
	posturldata = urllib.urlencode(parameters) #Encode the paraters in the proper format for posting
	#This request will give us the first set of data
	br.open('http://'+l_controllerip+'/standard/datapoints/datapoints.php',posturldata)
	cj.save(cookiefile)
	#Of course we want to keep the response
	datapoints_response.append(unidecode(br.response().read().decode("UTF-8")))
	return

def checkadditionalpage():
	#define function to check if there is another page
	#Now it might be time for the second page, thanks to Honeywell quite a P i t A
	global pagenum
	soup = BeautifulSoup(datapoints_response[(len(datapoints_response)-1)])
	sites = soup.findAll("a", attrs={"class": "pagelink"})
	nextpagefilter = re.compile('\"JavaScript\:goToPage \(([0-9]+)\)\;\"')
	for index, data in enumerate(sites):
		if int(nextpagefilter.findall(str(data))[0]) > pagenum:
			pagenum = pagenum+1
			getadditionalpage(pagenum)
			break
		else:
			continue
		break
	return

def getadditionalpage(pagenum):
	#define function to get additional pages
	global datapoints_response
	parameters = [
	("SessionID" , csession_id),
	("LocaleID" , l_localeid),
	("Session" , "<Session><LocaleID>"+l_localeid+"</LocaleID><Precision>2</Precision><Page>"+str(pagenum)+"</Page><Filter><DatapointTypes><DatapointType>0</DatapointType><DatapointType>1</DatapointType><DatapointType>2</DatapointType><DatapointType>3</DatapointType><DatapointType>4</DatapointType><DatapointType>5</DatapointType><DatapointType>13</DatapointType><DatapointType>14</DatapointType><DatapointType>19</DatapointType><DatapointType>24</DatapointType></DatapointTypes><SearchText>*</SearchText><PointsInAlarm>0</PointsInAlarm><PointsInManual>0</PointsInManual></Filter><Sort><Columns><Column><ColumnID>2</ColumnID><Descending>0</Descending></Column><Column><ColumnID>3</ColumnID><Descending>0</Descending></Column></Columns></Sort><PointsInAlarm>0</PointsInAlarm><PointsInManual>0</PointsInManual><EntriesPerPage>50</EntriesPerPage></Session>"),
	("Page" , str(pagenum)),
	("Plants" , ""),
	("Columns" , ""),
	("Descending" , ""),
	("Command" , "GoToPage"),
	("PlantName" , "<Alle>"),
	("AnalogInput" , "on"),
	("BinaryInput" , "on"),
	("MultiStateInput" , "on"),
	("TotalizerInput" , "on"),
	("AnalogOutput" , "on"),
	("BinaryOutput" , "on"),
	("MultiStateOutput" , "on"),
	("AnalogValue" , "on"),
	("BinaryValue" , "on"),
	("MultiStateValue" , "on"),
	("SearchText" , "*"),
	("SortBy" , "Name"),
	("EntriesPerPage" , "50")
	]

	posturldata = urllib.urlencode(parameters) #Encode the parameters in the proper Format for posting
	posturldata = posturldata.replace("%2A","*") #The Asterisk should not be encoded though
	#print posturldata

	br.open('http://'+l_controllerip+'/standard/datapoints/datapoints.php',posturldata)
	cj.save(cookiefile)
	datapoints_response.append(unidecode(br.response().read().decode("UTF-8")))
	checkadditionalpage()
	return

def logout():
	#When we have finished reading the data, it might be time to close the session
	parameters = [
	("Command" , "Logout"),
	("LocaleID" , l_localeid),
	("NewLocaleID" , l_localeid),
	("OldSessionID" , csession_id),
	("RefreshTime" , "-1"),
	("SessionID" , csession_id)
	]

	posturldata = urllib.urlencode(parameters)
	#print posturldata

	br.open('http://'+l_controllerip+'/standard/footer/footer.php',posturldata)
	cj.save(cookiefile)
	l_logout_response = br.response().read()
	return l_logout_response



checksession()
if l_loginvalid == False:
	createsession()

getdatapage()
checkadditionalpage()

if l_controlleriptwo:
	l_controllerip = l_controlleriptwo
	checksession()
	if l_loginvalid == False:
       		createsession()
	getdatapage()
	checkadditionalpage()

"""
print "first response"
print "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
print datapoints_response[0]
print "############################################################"
print "second response"
print "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
"""
scrapedata = extractdata(datapoints_response)

#The following list of Datapoints contain constantly changing numeric values (Temperatures, Valve positions, etc)
numericdatapoint = [1,2,3,6,7,8,9,10,11,4194305,4194306,4194307,4194308,8388609,8388610,8388612,8388613,8388614,8388616,8388619,8388622,8388630,8388631,8388654,8388655,8388664,8388665,8388667,8388668,8388669,8388671]

#open the Mysql DB for status datapoints
db = MySQLdb.connect("localhost","heatingupdater","BDND2zJ6Dj4DX3nU","heatingdata" )
dbcursor = db.cursor()

#fetch the last values from all datapoints
dbquery = """select datapoint_id,value,state,flags from ( select *  from datapointchangelog order by timestamp desc ) x group by datapoint_id"""

try:
	# Execute the SQL command
	dbcursor.execute(dbquery)
	# Fetch all the rows in a list of lists.
	statuselemetsoldvalues = dbcursor.fetchall()
except:
	print "Error: unable to fetch data"
	pass

	
#iterate through the scraped data and extract data elemnts
numericelements = []
statuselements =[[]]

for index, data in enumerate(scrapedata):
	if index > 0: #We need a new column before we can start adding further stuff
               	statuselements.append([])
	if int(data[0]) in numericdatapoint:
		numericelements.append(str((str(data[1])[:6])+" "+data[2]+":"+data[3]))
		statuselements[(len(statuselements))-1].append(str(data[0]))
		statuselements[(len(statuselements))-1].append("numericdp")
		statuselements[(len(statuselements))-1].append(str(data[5]))
		statuselements[(len(statuselements))-1].append(str(data[7]))
	else:
		statuselements[(len(statuselements))-1].append(str(data[0]))
		statuselements[(len(statuselements))-1].append(str(data[3]))
		statuselements[(len(statuselements))-1].append(str(data[5]))
		statuselements[(len(statuselements))-1].append(str(data[7]))
		

#Create get request update statement for feeding numeric values into emoncms
urlstring = ','.join([string for string in numericelements])
postdata = [("json","{"+urlstring+"}"),("apikey","ed450805d09809d49d3fc31c11c72913"),("node","15")]
encoded_urldata = urllib.urlencode(postdata)

#print urlstring
#print postdata
#print encoded_urldata

#Feed numerical datapoints data into emon cms
br.open("http://knx-server03/emoncms/input/post.json?"+encoded_urldata)
output = br.response().read()
print datetime.datetime.now()
print output

#Check if a Status value changed
statuselemetsnewvalues = []
for index, data in enumerate(statuselements):
	#print data[0]
	try:
		[item for item in statuselemetsoldvalues if long(item[0]) == long(data[0]) and item[1] == data[1] and item[2] == data[2] and long(item[3]) == long(data[3])][0]
		#print data
	except:
		#print "fail"
		#print [item for item in statuselemetsoldvalues if long(item[0]) == long(data[0])][0]
		statuselemetsnewvalues.append(data)
		#print ""
		pass

#print tabulate(scrapedata)
#print statuselemetsnewvalues

#Create the insert statement for the changed datapoints
dbquery = """INSERT INTO `datapointchangelog` (datapoint_id, value, state, flags) VALUES (%s, %s, %s, %s ) """

#print(dbquery, statuselemetsnewvalues)


#If something changed log the changes to the mysql db
if len(statuselemetsnewvalues) > 0:
	try:
		# Execute the SQL command
		dbcursor.executemany(dbquery,statuselemetsnewvalues)
		# Commit your changes in the database
		db.commit()
	except:
		# Rollback in case there is any error
		db.rollback()
#print tabulate(scrapedata)


print str(len(statuselemetsnewvalues))+" Records inserted into MySql datapoint changelog table"

#print len(updateelements)
"""

for index, workwith in enumerate(datapoints_response):
        files = open("responsefile"+str(index)+".txt","w+")
        files.write (datapoints_response[index])
        files.close()



print datapoints_response[1]
print "############################################################"
print "third response"
print "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
print datapoints_response[2]
print "############################################################"
print "fourth response"
print "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
print datapoints_response[3]
print "############################################################"
"""

# disconnect from databaseserver
db.close()
