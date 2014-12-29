####################################################################################################
# project: wmc2plex plugin
# description: Plugin for Plex to allow viewing of liveTV, EPG, and the scheduling/viewing of
#             recordings via ServerWMC
# Author : Scott Alphonso ---
# Credits: Thank you KrustyReturns(Vic) for creating ServerWMC and the help with creating this plugin
####################################################################################################


import socket
import datetime
from datetime import timedelta
import os
import os.path

PREFIX = '/video/wmc2plex'
NAME = 'PlexWMC'
ART = 'art-default.jpg'
SERVERWMC_IP = Prefs['serverwmc_ip']
SERVERWMC_PORT = Prefs['serverwmc_port']
SERVERWMC_ADDR = (SERVERWMC_IP, 9080)
VERSION = '0.3.1'
MACHINENAME = socket.gethostname()
IDSTREAMINT = 0
GETSTREAMINFO = 'IncludeStreamInfo'
TIME_MIN = datetime.datetime(1900, 1, 1, 0, 0)
TIME_T_REF = datetime.datetime(1970, 1, 1, 0, 0)
TZ_DIFF = timedelta(seconds=0)
EPGDAYS = int(Prefs['serverwmc_epg_days'])
DEBUG = Prefs['debug_level']
STREAMID = 0
DURATION = 14400000



####################################################################################################
def Start():

        # Get time zone hour difference in seconds
        getTimeDif()
        ObjectContainer.art = R(ART)
        ObjectContainer.title1 = NAME

####################################################################################################
@handler(PREFIX, NAME, ART)
def MainMenu():

        Log.Debug(Core.bundle_path)

        GetInfo()

        response = socketClient('GetServerVersion', '')
                      
        oc = ObjectContainer(title1=NAME,no_cache=True)

        # Settings
        oc.add(PrefsObject(title='Settings', thumb=R('icon-settings.png')))

        # Channels
        oc.add(DirectoryObject(key = Callback(SubMenu, menu='Channels'), title='Channels'))
        oc.add(DirectoryObject(key = Callback(GetRecordings), title='Recordings'))  # used for testing, not functional

        return oc
	
####################################################################################################
@route(PREFIX +'/submenu/{title}')
def SubMenu(menu):

        oc = ObjectContainer(title2=menu, no_cache=True)

        # Connect and Get Channel List
        resultsArray = socketClient('GetChannels', '')

        if DEBUG == 'Verbose':
                Log.Debug('----------SubMenu Function----------')
                Log.Debug(resultsArray)

        # Loop through resultsArray to build Channel objects
        for result in resultsArray:
                channelArray = result.split('|')
                channelID = channelArray[0]
                try:
                        channelImageFile = channelArray[5].split('/')[-1]  # 'file://' + channelArray[5].split('@')[-1]
                except:
                        channelImageFile = ''
                channelNumber = channelArray[2]
                channelName = channelArray[8]
                channelTitle = channelName + '(' + channelNumber + ')'
                channelURL = channelArray[9]
                Thumb = channelImageFile
                summaryData = getChannelInfo(chID=channelID, progItem='programName', infoType='nowPlaying')
                summaryData = summaryData + ' : ' + getChannelInfo(chID=channelID, progItem='programOverview', infoType='nowPlaying')
                Summary='Now Playing : ' + summaryData

                if DEBUG=='Normal' or DEBUG=='Verbose':
                        Log.Debug(channelImageFile + ' - ' + channelArray[5])
                        Log.Debug(channelTitle + ', ' + channelURL + ', ' + channelImageFile + ', '
                                  + channelNumber + ', ' + channelName)

                if menu=='Channels':
                        oc.add(CreateCO(url=channelURL, chID=channelID, title=channelTitle, summary=Summary, thumb=R(Thumb)))
                                                      
        return oc

####################################################################################################
@route(PREFIX + '/CreateCO')
def CreateCO(url, chID, title, summary, thumb, container=False):

        # check preferences for DLNA playback - *put in for future use currently uses DLNA no matter what*
        co = SeasonObject(
                rating_key=url,
                key=Callback(CreateChannel, url=url, chID=chID, title=title, summary=summary, thumb=thumb),
                title=title,
                summary=summary,
                thumb=thumb
                )

        if DEBUG == 'Verbose':
                Log.Debug('----------CreateCO Function----------')
                Log.Debug(title + ', ' + url + ', ' + str(thumb))

        return co

####################################################################################################
@route(PREFIX + '/CreateChannel')
def CreateChannel(url, chID, title, summary, thumb, include_container=False):

        oc = ObjectContainer(title2=title, no_cache=True)

        # Get Start and end datetime and convert to seconds
        startDt = getTimeS(datetime.datetime.utcnow())
        endDt = int(startDt + (timedelta(days=EPGDAYS)).total_seconds())
 
        # build request string
        sendCommand = 'GetEntries|{0}|{1}|{2}'.format(chID, startDt, endDt)

        # Connect and get channel/program info
        resultsArray = socketClient(sendCommand, '')

        if DEBUG=='Normal' or DEBUG=='Verbose':
                Log.Debug('Request sent: ' + sendCommand)
        if DEBUG=='Verbose':
                Log.Debug('----------CreateChannel Function----------')
                Log.Debug(resultsArray)

        # Loop through resultsArray to build Channel objects
        for result in resultsArray:             
                infoArray = result.split('|')
                programID = infoArray[0] + '-' + infoArray[16]
                programName = infoArray[1]
                programStartDt = getDateTime(infoArray[3], start=True)
                programEndDt = getDateTime(infoArray[4])
                programAirTime = '(' + programStartDt + ' - ' + programEndDt + ') '
                programOverview = infoArray[5]
                programImage = infoArray[14]
                programEpisodeTitle = infoArray[15]
                try:
                        programRating = getRating(infoArray[8])
                except:
                        programRating = 'NR'
                programName = programAirTime + programName

                if DEBUG=='Verbose':
                        Log.Debug(programID + ',' + programName + ',' + programStartDt + ',' + programEndDt +
                                ',' + programOverview + ',' + programRating)
                if getDateTime(startDt) >= programStartDt <= programEndDt:
                        oc.add(
                                CreateEO(
                                        url=url,
                                        title=programName,
                                        summary=programOverview,
                                        thumb=programImage,
                                        nowPlaying=True
                                        ))
                else:
                        oc.add(
                                CreateEO(
                                        url=url,
                                        title=programName,
                                        summary=programOverview,
                                        thumb=programImage
                                        ))
                                                              
        return oc

####################################################################################################
@route(PREFIX + '/CreateEO')
def CreateEO(url, title, summary, thumb, nowPlaying=False):

        # check preferences for DLNA playback - *put in for future use, currently uses DLNA no matter what*
        if Prefs['serverwmc_playback']=='DLNA':
                if nowPlaying:
                        eo = EpisodeObject(
                                rating_key=title,
                                key=Callback(CreateEO, url=url, title=title, summary=summary, thumb=thumb),
                                title=title,
                                summary=summary,
                                duration=DURATION,
                                thumb=thumb,
                                items=[
                                        MediaObject(
                                                parts = [PartObject(key=url)],
                                                container = 'mpegts',
                                                video_resolution = 1080,
                                                bitrate = 20000,
                                                video_codec = 'mpeg2video',
                                                audio_codec = 'AC3',
                                                optimized_for_streaming = True
                                                )
                                        ]
                                )
                else:
                        eo = EpisodeObject(
                                rating_key=title,
                                key=Callback(CreateEO, url=url, title=title, summary=summary, thumb=thumb),
                                title=title,
                                summary=summary,
                                duration=DURATION,
                                thumb=thumb,
                                items=[
                                        MediaObject(
                                                parts = [PartObject(key=url)],
                                                container = 'mpegts',
                                                video_resolution = 1080,
                                                bitrate = 20000,
                                                video_codec = 'mpeg2video',
                                                audio_codec = 'AC3',
                                                optimized_for_streaming = True
                                                )
                                        ]
                                )
        else:
                pass  # place holder for future use

        if DEBUG == 'Verbose':
                Log.Debug('----------CreateEO Function----------')
                Log.Debug(title + ', ' + url + ', ' + str(thumb))

        return eo
        
####################################################################################################
def getChannelInfo(chID, progItem, infoType='Upcoming'):
        
        # Get Start and end datetime and convert to seconds
        startDt = getTimeS(datetime.datetime.utcnow())
        endDt = int(startDt + (timedelta(days=EPGDAYS)).total_seconds())
 
        # build request string
        sendCommand = 'GetEntries|{0}|{1}|{2}'.format(chID, startDt, endDt)

        # Connect and get channel/program info
        resultsArray = socketClient(sendCommand, '')

        if DEBUG=='Normal' or DEBUG=='Verbose':
                Log.Debug('Request sent: ' + sendCommand)
        if DEBUG=='Verbose':
                Log.Debug('----------getChannelInfo Function----------')
                Log.Debug(resultsArray)

        # Loop through results array and build Channel info objects
        count = 0
        for result in resultsArray:
                count += 1
                infoArray = result.split('|')
                # only get no playing item
                if count==1 and infoType=='nowPlaying':                        
                        programID = infoArray[0] + '-' + infoArray[16]
                        programName = infoArray[1]
                        programStartDt = getDateTime(infoArray[3], start=True)
                        programEndDt = getDateTime(infoArray[4])
                        programAirTime = '(' + programStartDt + ' - ' + programEndDt + ') '
                        programOverview = infoArray[5]
                        programImage = infoArray[14]
                        programEpisodeTitle = infoArray[15]
                        try:
                                programRating = getRating(infoArray[8])
                        except:
                                programRating = 'NR'
                        programName = programAirTime + programName

                        if DEBUG == 'Verbose':
                                Log.Debug(programID + ',' + programName + ',' + programStartDt + ',' + programEndDt +
                                         ',' + programOverview + ',' + programRating)

                        if progItem == 'programID' : progData=programID,
                        elif progItem == 'programName' : progData=programName,
                        elif progItem == 'programStartDt' : progData=programStartDt,
                        elif progItem == 'programEndDt' : progData=programEndDt,
                        elif progItem == 'programOverview' : progData=programOverview,
                        elif progItem == 'programImage' : progData=programImage,
                        elif progItem == 'programEpisodeTitle' : progData=programEpisodeTitle
                        else : progItem = ''
                        break
                elif count==2 and infoType == 'upNext':
                        programID = infoArray[0] + '-' + infoArray[16]
                        programName = infoArray[1]
                        programStartDt = getDateTime(infoArray[3], start=True)
                        programEndDt = getDateTime(infoArray[4])
                        programAirTime = '(' + programStartDt + ' - ' + programEndDt + ') '
                        programOverview = infoArray[5]
                        programImage = infoArray[14]
                        programEpisodeTitle = infoArray[15]
                        try:
                                programRating = getRating(infoArray[8])
                        except:
                                programRating = 'NR'
                        programName = programAirTime + programName

                        if DEBUG == 'Verbose':
                                Log.Debug(programID + ',' + programName + ',' + programStartDt + ',' + programEndDt +
                                         ',' + programOverview + ',' + programRating)

                        if progItem == 'programID' : progData=programID,
                        elif progItem == 'programName' : progData=programName,
                        elif progItem == 'programStartDt' : progData=programStartDt,
                        elif progItem == 'programEndDt' : progData=programEndDt,
                        elif progItem == 'programOverview' : progData=programOverview,
                        elif progItem == 'programImage' : progData=programImage,
                        elif progItem == 'programEpisodeTitle' : progData=programEpisodeTitle
                        else : progItem = ''
                        break
                elif count>2:
                        break
                else:
                        pass

        progData = str(progData[0])

        if DEBUG == 'Normal' or DEBUG == 'Verbose':
                        Log.Debug(progData)

        if infoType == 'nowPlaying' or infoType == 'upNext':
                return progData
        else:
                return progData

####################################################################################################
@route(PREFIX + '/getrecordings')
def GetRecordings():

        oc = ObjectContainer(title2='Recordings', no_cache=True)

        # Connect and Get list of recordings
        resultsArray = socketClient('GetRecordings', '')

        fn = R('test.txt')
        Log.Debug('====================File :' + str(fn))
        test = os.open(fn, os.O_RDWR|os.O_TRUNC|os.O_CREAT)
        os.write(test, 'This is a test.')
        os.close(test)

        if DEBUG == 'Normal' or DEBUG == 'Verbose':
                Log.Debug(resultsArray)
        
        return oc

####################################################################################################
@route(PREFIX + '/getChannelStream')
def getChannelStream(channelID):

        # Build channel stream variables
        channelStream = ''
        streamID = createStreamID(STREAMID)

        # Build Command string
        command = "OpenLiveStream|" + channelID + "|" + GETSTREAMINFO

        # connect and retrieve channel stream path
        if DEBUG == 'Normal' or DEBUG == 'Verbose':
                Log.Debug('START STREAM -----------------------------------------------------------')
                
        responses = socketClient(command, streamID)
        for response in responses:
                streamArray = response.split(',')
                channelStream = streamArray[0]

        if DEBUG == 'Verbose':
                Log.Debug('----------getChannelStream Function----------')
                Log.Debug(channelStream)
     
        return channelStream

####################################################################################################
def closeChannelStream(streamID):

        # Close Stream
        command = "CloseLiveStream"
        channelStream = socketClient(command, streamID)
        
####################################################################################################
@route(PREFIX + '/GetInfo')
def GetInfo():
        Log.Debug(str(Request.Headers))
        Log.Debug('wmc2plexVersion:'+VERSION)
        Log.Debug('PlatformOS:'+Platform.OS)
        Log.Debug('MACHINENAME:'+MACHINENAME)
        Log.Debug('PlatformCPU:'+Platform.CPU)
        Log.Debug('PlatformHasSilverlight:'+str(Platform.HasSilverlight))
        Log.Debug('ClientPlatform:'+str(Client.Platform))
        Log.Debug('ClientPlatform:'+str(Client.Protocols))
        Log.Debug('SettingsServerWMC_IP:'+str(Prefs["serverwmc_ip"]))
        Log.Debug('ServerWMC_ADDR:'+str(SERVERWMC_ADDR))

####################################################################################################
def socketClient(command, streamID):

        # Create the Socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
                # Connect to endpoint
                sock.connect(SERVERWMC_ADDR)

                if DEBUG == 'Normal' or DEBUG == 'Verbose':
                        Log.Debug('Connection to ' + ''.join(SERVERWMC_IP) + ':'
                                  + ''.join(SERVERWMC_PORT) + ' ServerWMC successfull.')
                
                # build request string - switch Mediabrowser to Plex when done
                sendCommand = 'Plex^@{1}@{2}|{0}<Client Quit>'.format(command, MACHINENAME, streamID)
                
                # send command string to server
                sock.sendall(sendCommand)
                
                # use this array to accumulate server response
                allData =[]
                
                # keep getting results from server until zero bytes are read
                while True:
                        data = sock.recv(4096)
                        if not data: break
                        allData.append(data)
                response = ''.join(allData)

                # Clean up response
                if response.endswith('<EOF>'):
                        response = response.replace('<EOF>', '')
                if response.endswith('<EOL>'):
                        response = response[:-5]
 
                if DEBUG=='Verbose':
                        Log.Debug('----------socketClient Function----------')
                        Log.Debug('Recieved: {0}'.format(response))

                # Convert response string to array
                resultsArray = response.split('<EOL>')

        except:
                Log.Error('Trying to connect to ' + ''.join(SERVERWMC_IP) + ':'
                          + ''.join(SERVERWMC_PORT) + ' ServerWMC: Not detected. Check IP and Port.')
        finally:
                # Release socket
                sock.shutdown(2)
                sock.close()

        return resultsArray

####################################################################################################
@indirect
def playVideo(url):
        return IndirectResponse(VideoClipObject, key=url)

####################################################################################################
def getRating(rating):
        if rating == 'UsaY': rating='TV-Y'
        elif rating == 'UsaY7': rating='TV-Y7'
        elif rating == 'UsaG': rating='G'
        elif rating == 'UsaPG': rating='PG'
        elif rating == 'UsaTV14': rating='TV-14'
        elif rating == 'UsaMA': rating='TV-MA'
        else: rating = 'NR'

        return rating

####################################################################################################
def getTimeS(time):

        time_t = time.replace(microsecond=0)
        time_t = time_t - TIME_T_REF
        time_t = int(time_t.total_seconds())

        return time_t

####################################################################################################
def getDateTime(time, start=False):

        today = datetime.datetime.utcnow()
        today = today.strftime('%d')
        time_t = timedelta(seconds=int(time))
        time_t = TIME_T_REF + time_t
        time_t = time_t + TZ_DIFF
        time_tDay = time_t.strftime('%d')
        if today == time_tDay:
                time_t = time_t.strftime('%I:%M')
        else:
                if start:
                        time_t = time_t.strftime('%m/%d %I:%M')
                else:
                        time_t = time_t.strftime('%I:%M')

        return time_t

####################################################################################################
def createStreamID(streamID):

        global STREAMID
        newStreamID = streamID + 1
        STREAMID = newStreamID
        return newStreamID

####################################################################################################
def getTimeDif():

        global TZ_DIFF
        localTime = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
        utcTime = datetime.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        TZ_DIFF = (localTime - utcTime).total_seconds()
        TZ_DIFF = datetime.timedelta(0,TZ_DIFF)
        if DEBUG == 'Verbose':
                Log.Debug('----------TIME ZONE DIFF----------')
                Log.Debug(TZ_DIFF)
