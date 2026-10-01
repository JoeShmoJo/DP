#Dowloads ESP data from NWRFC website and saves to DSS
#siteIDs is the list used to query sites for download,
#  matching with a regular expression
#The urls are looked up from an Excel sheet that has
#  one sheet for each 'flavor' of ESP data (natural, 
#  unadjusted, and water supply).  All of the data
#  types are downloaded for each site (i.e., all of the 
#  natural, unadjusted, and water supply data)
#Data are saved using a standard convention,. e.g,
# //ANAW1N/FLOW/01JUL2019/6HOUR/C:001949|NATURAL/


# Revisions:
#2019-09-30 RSW
# - modified to use java from the "V" drive, was previously pointed to personal "D" drive

### Establishing Java Settings ########################################
#Used by dssrip package

options( java.parameters = "-Xms64m" ) #Increasing java JVM heap size for memory limits (not sure this actually helps)


if(R.Version()$arch=="x86_64"){
  # use 64-bit .jar and .dll
  
  #resourceDir should be created in the main script that sources this module
  #baseJavaDir = "D:\\Programs\\java64"
  baseJavaDir = "D:\\ESP Set up\\java64"
  
  cat(sprintf("\n\nLoading 64-bit Java from the following directory:\n\t%s\n\n", baseJavaDir ))
  
  options(dss_location=baseJavaDir )
  options(dss_jre_location= paste0(baseJavaDir ,"\\java") )
  
  Sys.setenv(JAVA_HOME= paste0(baseJavaDir, "\\java") )
  
} else {
  stop("\n\nThis script needs to be ran using 64-bit R\n\n")
}

### Packages ############

library(dssrip)
library(readr)
library(lubridate)
library(XLConnect)
library(dplyr)
library(reshape2)

### Config ##############
cat("\n\nBeginning ESP Download\n\n")

#base directory, contains 'rfcLinkFile' Excel file.  Data 
#  will be saved here
#saveLocation <- "D:\\CWMS\\script\\esp_download"
saveLocation = commandArgs(trailingOnly=TRUE) #Reading input location from file
# outFileName = commandArgs(trailingOnly=TRUE)

# cat(sprintf("\nArgument passed to script:\t%s", saveLocation))


# has all URLs and CSV file names for all sites and ESP configurations
rfcLinkFile <- "rfc_esp_links.xlsm" 

siteIDs <- c("DETO",
             "FOSO",
             "ALBO",
             "JFFO",
             "WTLO",
             "GPRO",
             "FRNO",
             "EUGO",
             "GOSO",
             "DORO",
             "LOPO",
             "FALO",
             "HCRO",
             "COTO",
             "MNRO",
			 "HARO",
			 "JASO",
			 "MCZO",
			 "CGRO",
			 "BLUO",
			 "CGRO",
			 "TRBO",
			 "MEHO",
			 "LSMO",
			 "SPRO",
			 "VIDO",
			 "WSLO",
			 "CANO",
			 "WLSO",
			 "SUVO",
			 "CORO",
			 "PHIO",
			 "AURO",
			 "MCMO",
			 "SLMO")

#can be '0','5', or '10', representing forecasts generated using
#  0, 5, and 10 days of short-term weather forecasts.
espDays <- "10" 

### Setup #############
rfcLinkFileName <- sprintf("%s\\scripts\\esp_download\\%s",dirname(dirname(saveLocation)),rfcLinkFile)
#rfcLinkFileName <- sprintf("%s\\%s",saveLocation,rfcLinkFile)
#if(!file_test("-f",saveLocation)) rfcLinkFileName <- sprintf("%s\\%s",dirname(saveLocation),rfcLinkFile)
cat(sprintf("\nLoading Excel with URL Links:\t%s", rfcLinkFileName))
rfcLinkWb <- loadWorkbook(rfcLinkFileName)

rfcLinks <- list()
#RSW, 8/8/2019
#Per conversation with Keving Berghoff of the NWRFC, natural
#  is the best option for ESP.watersupply is legacy, unadjusted has no routing.
#  
for(esp_config in c("natural")){ 
  # for(esp_config in c("natural","watersupply","unadjusted")){ #uncomment and comment above to dl all available feeds
  rfcLinks[[esp_config]] <- readWorksheet(object = rfcLinkWb, sheet = esp_config)
  rfcLinks[[esp_config]]$esp_config <- esp_config
}
rfcLinks <- bind_rows(rfcLinks)

### Functions #######################
# cat("\nEstablishing Functions")

"%!in%" <- function(x, y) !(x %in% y) #Not in operator

#Extracts from left side of character(similar to Excel function)
left <- function(text, nchars) substring(text, 1, nchars)

#Extracts from right side of character (similar to Excel function)
right <- function(text, nchars) substring(text, nchar(text)-nchars+1, nchar(text))

getAllURLs <- function(siteID,filterString=NULL){
  #returns the subset of the url link dataframe containing the
  #  csv file's name, url, and the ESP configuration
  out <- rfcLinks[grepl(paste0(siteID,collapse="|"),rfcLinks$csvFileName),]
  if(!is.null(filterString)) out <- out[grepl(filterString,out$csvFileName),]
  return(out)
}

#read the ESP data to dataframe given url
readESPCSV <- function(siteURL)  data.frame(read_csv(file = url(siteURL), skip = 6))

#returns the csv file's name given the NWRFC url
getCSVFromURL <- function(siteURL) rfcLinks$csvFileName[rfcLinks$url==siteURL]

#e.g., returns 'natural', 'watersupply', or 'unadjusted'
getESPConfigFromURL <- function(siteURL) rfcLinks$esp_config[rfcLinks$url==siteURL]

addYMD <- function(inDF,dateColName){
  #given an input dataframe, adds columns for the year, month, and day
  inDF$year <- year(inDF[, dateColName])
  inDF$month <- month(inDF[, dateColName])
  inDF$day <- day(inDF[, dateColName])
  return(inDF)
}

getRawDataList <- function(urlList)   #Makes plotly plot of ESP datasets for comparison
  sapply(urlList,readESPCSV, simplify=F)

createTemplateTSC <- function(rawDataList){
  #Derives a TimeSeriesContainer object from the raw ESP data list
  #  where all that needs to be done is update the pathname
  #  and values - timestamps should be uniform across each 
  #  ESP trace
  
  #intializing HEC java objects
  tsc <- .jnew("hec/io/TimeSeriesContainer") #new TSC object
  hecStartTime <- .jnew("hec/heclib/util/HecTime")
  hecEndTime <- .jnew("hec/heclib/util/HecTime")

  #copmuting HEC times and interval (minutes) of timestep
  times = rawDataList[[1]]$FCST_VALID_TIME_GMT
  hecStartTime$set(format(times[1],"%d%b%Y %H:%M"))
  hecEndTime$set(format(times[length(times)],"%d%b%Y %H:%M"))
  hecTimes <- seq(hecStartTime$value(),hecEndTime$value(),length.out=length(times))
  interval <- unique(diff(times))/60
  
  #assigning to attributes of tsc object
  tsc$times = hecTimes
  tsc$values = rep(0,length(times))
  tsc$interal = interval #minutes
  tsc$startTime = hecStartTime$value()
  tsc$endTime = hecEndTime$value()
  tsc$numberValues = length(times)
  tsc$units = "CFS"
  tsc$type = "PER-AVER"
  tsc$parameter <- "FLOW" #Assuming always want this to be flow
  return(tsc)
}

formDSSPath <- function(colName,siteURL){
  #Forms an appropriate DSS file name from the URL and the column name
  #  in the ESP dataframe (e.g., 'X1952')
  #output (e.g.): //ALF/FLOW/01JUL2019/6HOUR/C:001949|WATER_SUPPLY/
  siteID <- strsplit(getCSVFromURL(siteURL),"_")[[1]][1] #B part
  wy <- as.numeric(right(colName,4)) #wy in F part
  esp_config = getESPConfigFromURL(siteURL) #esp type in F part
  sprintf("//%s/FLOW//6HOUR/C:%06d|%s/",siteID,wy,toupper(esp_config) )
}


getPathPart <- function(path,part){ #gets A-F part from DSS path
  partIndex <- which(toupper(part) == LETTERS)
  strsplit(path,"/")[[1]][partIndex+1]
}

updateTSCfromESP <- function(tsc,values,colName,siteURL){
  #Updates the values and path component of time series container for saving
  path <- formDSSPath(colName,siteURL)
  tsc$values <- values*1000 #converting from kcfs to cfs
  tsc$fullName <- path
  tsc$location  <- getPathPart(path,"A")
  tsc$watershed <- getPathPart(path,"B")
  tsc$version <- getPathPart(path,"F")
  return(tsc)
}

saveToDSS <- function(rawDataList,saveLocation,espDays){
  #From raw data list, saves the list of ESP dataframes to file
  #  If saveLocation is a file, saves there.  saveLocation can also
  #  be a directory, in which case a default file name is written provided
  #  the espDays  argument is assigned
  outFileName <- saveLocation
  if( !(toupper(right(saveLocation,3))=="DSS") ) #If the save locatation is a directory, creating a new path name
    outFileName = sprintf("%s\\rfc_esp_flows_%sday.dss",saveLocation,espDays)
 
  dssFile <- opendss(outFileName)
  templateTsc <- createTemplateTSC(rawDataList)
  #Iterating through each list element (list element)
  for( k in 1:length(rawDataList) ){
    #Iterating through each ESP trace (column in df)
    for( colName in names(rawDataList[[k]]) ){
      if(colName=="FCST_VALID_TIME_GMT") next #this is the datetime column
      tsc <- updateTSCfromESP(tsc = templateTsc, #update tsc object with data for this ESP trace
                              values = rawDataList[[k]][,colName],
                              colName = colName,
                              siteURL = names(rawDataList)[k]) 
      hm <- .jnew("hec/hecmath/TimeSeriesMath") #new HecMath object
      hm <- hm$createInstance(tsc) #converting tsc to hecmath, since
      dssFile$write(hm)            #  DSS is more coorperative with save as hecmath
    }
  }
  dssFile$close()
}

## Saving ###########

urlList <- getAllURLs(siteIDs,espDays)

# cat(sprintf("Downloading and processing the following URLs:\n\t%s",
            # paste0(urlList$url,collapse="\n\t")))

# cat(sprintf("\n\nBegin Download Data\t%s\n\n",Sys.time()))
rawDataList <- getRawDataList(urlList$url)   #Reading data into a list
# cat(sprintf("\n\nBegin Saving Data\t%s\n\n",Sys.time()))
saveToDSS(rawDataList = rawDataList, saveLocation = saveLocation,espDays=espDays)
# cat("\n\nDone Download ESP\n\n")

