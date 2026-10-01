# Finalize.py
# 1. Create a text file with some forecast metadata
# 2. Get user selected plot files and save to a temp folder with the text file
# 3. Zip up temp folder
# 4. Open Windows Explorer to zip file location

# Contact Eric Chow <eric.y.chow@usace.army.mil> with comments and/or questions

# Reference: Ryan Larsen's Teams post (reply to Ann Bannitt)
#            and JavaDocs

from hec2.rts.script import Forecast
from javax import swing
import javax.swing.JOptionPane as JOP
from javax.swing import JFrame
import os, sys
import shutil
from datetime import datetime
import subprocess

#testing imports per Art's 2022-10-04 email
#from hec.rss.client import RSS     # ImportError: No module named rss
#from hec.rss.model import RssSystem # ImportError: No module named rss


SelectedFcst = Forecast.getSelectedForecast()
SelectedFcstName = SelectedFcst.getName()
FcstRunNames = SelectedFcst.getForecastRunNames()
ForecastRunTimeWindow = SelectedFcst.getRunTimeWindow()

FcstFolder = Forecast.getForecastFolder(SelectedFcstName)
split = FcstFolder.rsplit('/')
split = split[: -3]
WtrshdFolder = ''
for x in split:
    WtrshdFolder = WtrshdFolder + x + '/'

# print(SelectedFcst)
# print(SelectedFcstName)
# print(FcstRunNames)
# print(ForecastRunTimeWindow)
# print('Forecast Lookback Time: %s' % ForecastRunTimeWindow.getLookbackTime())
# print('Forecast Start Time: %s' % ForecastRunTimeWindow.getStartTime())
# print('Forecast End Time: %s' % ForecastRunTimeWindow.getEndTime())

# print(FcstFolder)
# print(WtrshdFolder)
# print(PlotFolder)


# Select plot files
chooser = swing.JFileChooser('Z:/')
chooser.setMultiSelectionEnabled(1)
val = chooser.showDialog(None,"Select the Plot files");
# print(chooser.getSelectedFiles())
filelist = chooser.getSelectedFiles().tolist()
filelistlength = len(filelist)
filelistrange = range(0,filelistlength)
for x in filelistrange: filelist[x] = str(filelist[x])
# print(filelist)

split = filelist[0].rsplit('\\')
split = split[: -1]
PlotFolder = ''
for x in split:
    PlotFolder = PlotFolder + x + '/'
# print(PlotFolder)

ZipFolder = PlotFolder + 'temp/'
os.mkdir(ZipFolder)

# Get user input to add to text file
frame = JFrame("User Dialog")
comments = JOP.showInputDialog(frame, "Enter comments:")

textfilepath = ZipFolder + 'readme.txt'




with open(textfilepath, 'w') as f:
    f.write('Forecast Name: %s' % SelectedFcstName)
    f.write('\n')
    f.write('Forecast Run Name: %s' % FcstRunNames)
    f.write('\n')
    f.write('Forecast Lookback Time: %s' % ForecastRunTimeWindow.getLookbackTime())
    f.write('\n')
    f.write('Forecast Start Time: %s' % ForecastRunTimeWindow.getStartTime())
    f.write('\n')
    f.write('Forecast End Time: %s' % ForecastRunTimeWindow.getEndTime())
    f.write('\n')
    f.write('User Comments: %s' % comments)

for f in filelist:
    shutil.copy(f, ZipFolder)

dt_string = datetime.now().strftime("%Y-%m-%d_%H%M")
output_filename = PlotFolder + dt_string
shutil.make_archive(output_filename, 'zip', ZipFolder)

shutil.rmtree(ZipFolder)

OpenFolder = PlotFolder.replace('/','\\')
subprocess.Popen('explorer %s' % OpenFolder)