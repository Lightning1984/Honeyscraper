def extractdata(inputhtml):
        from bs4 import BeautifulSoup
        import re
        from unidecode import unidecode

        #file = open ('responsefile1.txt', 'r')
        #soup = BeautifulSoup(file)

        """
        Data Format:
        DatapointID
        Name
        Description
        Value
        Unit
        Event State
        Type
        Alarm+Fault+Override+OutOfService (binary coded)
        """

        #Create our matrix string array
        matrixarray = [[]]

        #prepare our compiled regex filters
        regcompile1 = re.compile('\'(.*?)\'')
        regcompile2 = re.compile('\>.(.*?).\<')
        regcompile3 = re.compile('value=\"(.*?)\"')
        regcompile4 = re.compile('title=\"(.*?)\"')
        regcompile5 = re.compile('(checked=\"\")')

        for count, data in enumerate(inputhtml):
                #The ingredients of the soup are being added from the inputhtml
                soup = BeautifulSoup(data)
                #Gets us all rows that have the two colors of the datatable out of the soup
                datapointrows = soup.findAll("tr", {'bgcolor' : re.compile('^#FFFFFF$|^#D8E8F5$')})
                if count > 0: #We need a new column before we can start adding further stuff
                        matrixarray.append([])

                #iterate through the Data and extract all data
                for index, datapointrow in enumerate(datapointrows):
                        tablecells = datapointrow.find_all("td")
                        temparray = regcompile1.findall((str(tablecells[1]))) #Export DatapointID and Name from 2nd column
                        matrixarray[(len(matrixarray))-1].append(temparray[0]) #Write Datapoint ID to array
                        matrixarray[(len(matrixarray))-1].append(temparray[2]) #Write Internal Name to array
                        matrixarray[(len(matrixarray))-1].append(regcompile2.findall((unidecode(str(tablecells[2]).decode("UTF-8"))))[0]) #Export and write description from 3rd column to array
                        temparray = (str(regcompile3.findall(str(tablecells[3]))[0])).split() #Export Value and Unit from 4th column
                        matrixarray[(len(matrixarray))-1].append(temparray[0]) #Write Value to array
                        try:    #don't abort if there is no Unit
                                matrixarray[(len(matrixarray))-1].append(temparray[1]) #Write Unit to array in case it exists
                        except:
                                matrixarray[(len(matrixarray))-1].append("") #Write empty cell to array to keep all items in the same position
                                pass #Just ignore the error and continue in the loop
                        matrixarray[(len(matrixarray))-1].append(regcompile3.findall(str(tablecells[4]))[0]) #Export and write event state from 4th column to array
                        matrixarray[(len(matrixarray))-1].append(regcompile4.findall(str(tablecells[5]))[0]) #Export and write datapointe type from 5th column to array
                        statusreturncode = 0b0 #Clean the responsecode variable before using it
                        for count in range(6, 10):
                                match = regcompile5.search(str(tablecells[count]))
                                if match:
                                        statusreturncode |= ((1<<3)>>count-6)
                        matrixarray[(len(matrixarray))-1].append(statusreturncode)
                        if index < (len(datapointrows)-1): #Add a new row to the array if further columns are to follow
                                matrixarray.append([])
                """
                for i in matrixarray:
                        print i
                """
        return matrixarray

if __name__=='__main__':
   print extractdata()
