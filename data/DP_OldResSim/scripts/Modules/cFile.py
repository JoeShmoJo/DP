'''
cFile Module
Contains code to manipulate files
'''

import logging, os, sys
################################################################################
# STATIC INPUT

################################################################################
# CLASS DEFINITIONS

# END OF CLASS DEFINITIONS
################################################################################
# FUNCTION DEFINITIONS

def ensure_dir(f):
	# creates any necessary directories found in "f", if they don't exist
	# e.g. f = "C:/RAFT/GIS/foo/bar", foo and bar folders will be created
	d = os.path.dirname(f)
	if not os.path.exists(d):
		os.makedirs(d)
	return None

def fileOpenReadClose(txtFileName):
	# function that opens a text file and reads the lines
	if not os.path.exists(txtFileName): 
		errMsg = "File does not exist: \n%s" %txtFileName
		raise AssertionError, errMsg
	txtFile = open(txtFileName, 'r')
	txtLines = txtFile.readlines()
	txtFile.close()
	return txtLines
	
def stripOutCommentLines(txtLines):
	# function to strip out comment lines from read file
	newLines = []
	for txtLine in txtLines :
			line = txtLine.strip()
			if len(line) == 0 : pass               # skip blank lines
			elif line.count(",") == len(line) : pass # CSV file with only commas
			elif line.startswith("#") : pass       # commented line
			elif line.startswith('"#') : pass      # commented line
			elif line.startswith('",') : pass      # commented line
			else : 
				#strip out any inline comments
				if "#" in line:
					cmtIdx = line.find("#") #returns -1 if not found
					line = line[:cmtIdx].strip()
				newLines.append(line)
	return newLines
	
def checkIfFileOpen(filePath):
	# Check if the file is open
	try:
		myfile = open(filePath, "r+") # or "a+", whatever you need
		myfile.close()
		return True
	except IOError, FileNotFoundException:
		return False
		
def printMsgToFile(msg, txtFileName):
	# function that saves the text in msg (string) to txtFileName
	outFile = open(txtFileName, 'w')
	outFile.write(msg)
	outFile.close()
	return None