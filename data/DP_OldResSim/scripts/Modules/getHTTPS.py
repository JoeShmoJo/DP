'''
getHTTPS

Simple module to retrieve an HTTPS webpage with SSL
The default Jython that ships with ResSim does not contain the ssl module,
and I couldn't figure out any way to read webpages with https

this is a poor workaround

Ryan Cahill, July 2018
'''

import sys
import os
import urllib
import urllib.request


def readHTTP(urlStr):
    #content = urllib.urlopen(urlStr)
    content = urllib.request.urlopen(urlStr)
    print("reading url: %s" %urlStr)
    lines = content.readlines()
    print("read %s lines" %len(lines))
    #print(lines)
    #lines = [str(line) + "\n" for line in lines]
    return lines
    
    
if __name__ == "__main__":
    #Assumes that the script is being launched directly (e.g. from command window)
    #Assumes the 1st argument is the url, and the second argument passed to this script is the output .txt file location
    my_url = sys.argv[1]
    outFileName = sys.argv[2]
    #my_url = "https://nwis.waterdata.usgs.gov/usa/nwis/dv?cb_00060=on&format=rdb&site_no=14033500&period=&begin_date=2008-09-26&end_date=2017-10-02"
    #outFileName = "E:/Watersheds/CRT/base/AFDR_NWD_ResSim_2017/scripts/Modules/temp.txt"
    lines = readHTTP(my_url)
    outFile = open(outFileName, 'wb')
    outFile.writelines(lines)
    outFile.close()
    