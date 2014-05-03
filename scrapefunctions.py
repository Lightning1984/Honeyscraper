def checksession(): #Check if we have a working login session
	global l_loginvalid
	if "csession_id" in globals() and "l_localeid" in globals():
		parameters = [
		("SessionID" , csession_id),
		("LocaleID" , l_localeid)
		]
		posturldata = urllib.urlencode(parameters) #Encode the parameters in the proper format for posting
		br.open('http://'+l_controllerip+'/standard/mainframe.php',posturldata)
	else:
		br.open('http://'+l_controllerip+'/standard/mainframe.php')
	l_checksession_response = br.response().read()
	l_soup = BeautifulSoup(l_checksession_response)
	if (len(l_soup.findAll("frame"))) < 2:
		l_loginvalid = True
	else:
		l_loginvalid = False
	return l_checksession_response

def createsession(): #Function to create a valid session ID
	global csession_response_code
	global csession_id
	l_createsession = ('http://'+l_controllerip+'/standard/login/session.php')
	br.open(l_creatsession)
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
	#Of course we want to keep the response
	datapoints_response.append(unidecode(br.response().read().decode("UTF-8")))
	return

def checkadditionalpage():
	#define function to check if there is another page
	#Now it might be time for the second page, thanks to Honeywell quite a P i t A
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
	l_logout_response = br.response().read()
	return l_logout_response
