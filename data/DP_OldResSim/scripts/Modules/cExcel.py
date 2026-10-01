'''
cExcel Module
Contains code to deal with Excel
'''

from jxl import Workbook
from jxl.write import Number, Label, DateTime

################################################################################
# STATIC INPUT

################################################################################
# CLASS DEFINITIONS

# END OF CLASS DEFINITIONS
################################################################################
# FUNCTION DEFINITIONS
def insertCell(sheet, colNum, rowNum,  val):
	# insert a cell into the worksheet at the specified row and column number
	# Indexes using these methods are off by one (e.g. index 2,5 refers to cell C6)
	rInd = rowNum-1
	cInd = colNum-1
	if isinstance(val,str) or isinstance(val, unicode):
		# we have a string, make a label type cell
		cel = Label(rInd,cInd, val)
	else: #assume a number
		cel = Number(rInd,cInd, val)
	sheet.addCell(cel)
	return None