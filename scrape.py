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

# Parse some commandline switches
parser = argparse.ArgumentParser(description='Screen scrape data from Honeywell Excel Web controller')
parser.add_argument('-i','--ip', help='The IP of the controller to scrape', required=True)
args = parser.parse_args()

# Browser
br = mechanize.Browser()

# Cookie Jar
cj = cookielib.LWPCookieJar()
br.set_cookiejar(cj)

# Honeywell Controller IP
l_controllerip = args.ip
# Login Credentials
l_username = "SystemAdmin"
l_password = "qqqqq"

# Other Variables
l_localeid = "1033" #This is the language setting of the controller
c_session_expected_response = "4194561"

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

def checksession(csession_id, l_localeid): #Check if we have a working login session
        parameters = [
        ("SessionID" , csession_id),
        ("LocaleID" , l_localeid)
        ]
        posturldata = urllib.urlencode(parameters) #Encode the paraters in the proper format for posting


        br.open('http://'+l_controllerip+'/standard/mainframe.php')

        login_response.append(br.response().read())

creatsession = ('http://'+l_controllerip+'/standard/login/session.php')
br.open(creatsession)
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
("LoginSessionID" , csession_id),
("LoginUserNameMD5" , l_username_md5),
("LoginPasswordMD5" , l_password_concat_md5),
("LoginCommand" , "Login"),
("LoginUserName" , l_username),
("LoginPassword" , l_password)
]
posturldata = urllib.urlencode(parameters) #Encode the paraters in the proper Format for posting
#This request will log us in
br.open('http://'+l_controllerip+'/standard/datapoints/datapoints.php',posturldata)
#Keep the response just in case
login_response.append(br.response().read())


#Create the parameter set to get the first Page of Datapoints

parameters = [
("SessionID" , csession_id),
("LocaleID" , l_localeid)
]
posturldata = urllib.urlencode(parameters) #Encode the paraters in the proper format for posting
#This request will give us the first set of data
br.open('http://'+l_controllerip+'/standard/datapoints/datapoints.php',posturldata)
#Of course we want to keep the response
datapoints_response.append(unidecode(br.response().read().decode("UTF-8")))

#Now it might be time for the second page, thanks to Honeywell quite a P i t A
pagenum = 1
#define function to check if there is another page
def checkadditionalpage():
        global pagenum
        soup = BeautifulSoup(datapoints_response[(pagenum-1)])
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
#define function to get additional pages
def getadditionalpage(pagenum):
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

        posturldata = urllib.urlencode(parameters) #Encode the paraters in the proper Format for posting
        posturldata = posturldata.replace("%2A","*") #The Asterisk should not be encoded though
        #print posturldata

        br.open('http://'+l_controllerip+'/standard/datapoints/datapoints.php',posturldata)
        global datapoints_response
        datapoints_response.append(unidecode(br.response().read().decode("UTF-8")))
        checkadditionalpage()
        return

#lets see if there is more pages to fetch, if so retrieve them
checkadditionalpage()

#We have finished reading the data, its time to close the session
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

login_response.append(br.response().read())
"""
print "first response"
print "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
print datapoints_response[0]
print "############################################################"
print "second response"
print "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
"""
scrapedata = extractdata(datapoints_response)
#for i in scrapedata:
#       print i

print tabulate(scrapedata)
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
