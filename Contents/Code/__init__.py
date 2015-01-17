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
REC_ICON = 'record_icon.png'
PLAY_ICON = 'play_icon.png'
CHANNEL_THUMB = 'channels.jpg'
TIMER_THUMB = 'timers.jpg'
SERVERWMC_IP = Prefs['serverwmc_ip']
SERVERWMC_PORT = Prefs['serverwmc_port']
SERVERWMC_ADDR = (SERVERWMC_IP, 9080)
VERSION = '0.6.0'
MACHINENAME = socket.gethostname()
IDSTREAMINT = 0
GETSTREAMINFO = 'IncludeStreamInfo'
TIME_MIN = datetime.datetime(1900, 1, 1, 0, 0)
TIME_T_REF = datetime.datetime(1970, 1, 1, 0, 0)
TZ_DIFF = timedelta(seconds=0)
EPGDAYS = int(Prefs['serverwmc_epg_days'])
DEBUG = Prefs['debug_level']
VID_QUALITY = Prefs['serverwmc_quality']
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

        socketClient('GetServerVersion', '')

        oc = ObjectContainer(title1=NAME,no_cache=True)

        # Settings
        oc.add(PrefsObject(title='Settings', thumb=R('icon-settings.png')))

        # Channels
        oc.add(DirectoryObject(key = Callback(SubMenu, menu='Channels'), title='Channels', thumb=R(CHANNEL_THUMB)))
        oc.add(DirectoryObject(key = Callback(GetTimers), title='Scheduled Recordings', thumb=R(TIMER_THUMB)))

        return oc

####################################################################################################
@route(PREFIX +'/SubMenu/{menu}')
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
                        channelImageFile = channelArray[5].split('/')[-1]
                        if channelImageFile=='':
                                channelImageFile = ART
                except:
                        channelImageFile = ART
                channelNumber = channelArray[2]
                channelName = channelArray[8]
                channelTitle = channelName + '(' + channelNumber + ')'
                channelURL = channelArray[9]
                Thumb = channelImageFile
                summaryData = getListingInfo(chID=channelID, progItem='programName', infoType='nowPlaying')
                summaryData = summaryData + ' : ' + getListingInfo(chID=channelID, progItem='programOverview', infoType='nowPlaying')
                Summary='Now Playing : ' + summaryData

                if DEBUG=='Normal' or DEBUG=='Verbose':
                        Log.Debug(channelImageFile + ' - ' + channelArray[5])
                        Log.Debug(channelTitle + ', ' + channelURL + ', ' + channelImageFile + ', '
                                  + channelNumber + ', ' + channelName)

                if menu=='Channels':
                        oc.add(DirectoryObject(key=Callback(
                                CreateChannel, url=channelURL, chID=channelID, title=channelTitle, thumb=R(Thumb)),
                                title=channelTitle, summary=Summary, thumb=R(Thumb)))

        return oc

####################################################################################################
@route(PREFIX + '/CreateChannel/{chID}')
def CreateChannel(url, chID, title, thumb):

        oc = ObjectContainer(title2=title, no_cache=True)

        # Get Start and end datetime and convert to seconds
        startDt = getTimeS(datetime.datetime.utcnow())
        endDt = int(startDt + (timedelta(days=EPGDAYS)).total_seconds())

        # build request string
        sendCommand = 'GetEntries|{0}|{1}|{2}'.format(chID, startDt, endDt)

        # Connect and get channel/program info
        resultsArray = socketClient(sendCommand, '')

        if DEBUG=='Verbose':
                Log.Debug('----------CreateChannel Function----------')
                Log.Debug(resultsArray)

        # Loop through resultsArray to build Channel objects
        for result in resultsArray:
                infoArray = result.split('|')
                programID = infoArray[0] + '-' + infoArray[16]
                programName = infoArray[1]
                programStartDt24 = getDateTime24(infoArray[3])
                programEndDt24 = getDateTime24(infoArray[4])
                programStartDt12 = getDateTime12(infoArray[3], format='datetime')
                programEndDt12 = getDateTime12(infoArray[4], format='time')
                programAirTime = '(' + programStartDt12 + ' - ' + programEndDt12 + ') '
                programOverview = infoArray[5]
                if infoArray[14]=='None':
                        programImage = R(thumb)
                else:
                        programImage = infoArray[14]
                programEpisodeTitle = infoArray[15]
                try:
                        programRating = getRating(infoArray[8])
                except:
                        programRating = 'NR'
                programTitle = programAirTime + programName

                if DEBUG=='Verbose':
                        Log.Debug(programID + ',' + programTitle + ',' + programStartDt24 + ',' + programEndDt24 +
                                ',' + programOverview + ',' + programRating)
                if programStartDt24 <= getDateTime24(startDt) <= programEndDt24:
                        oc.add(
                                CreateListing(
                                        url=url,
                                        chID=chID,
                                        chName=title,
                                        programID=programID,
                                        title=programTitle,
                                        name=programName,
                                        summary=programOverview,
                                        startTime = infoArray[3],
                                        endTime = infoArray[4],
                                        thumb=programImage,
                                        nowPlaying=True
                                        ))
                else:
                        oc.add(
                                CreateListing(
                                        url=url,
                                        chID=chID,
                                        chName=title,
                                        programID=programID,
                                        title=programTitle,
                                        name=programName,
                                        summary=programOverview,
                                        startTime = infoArray[3],
                                        endTime = infoArray[4],
                                        thumb=programImage
                                        ))

        return oc

####################################################################################################
@route(PREFIX + '/CreateListing/{chID}')
def CreateListing(url, chID, chName, programID, title, name, summary, thumb, startTime, endTime, nowPlaying=False):

        # check preferences for DLNA playback - *put in for future use, currently uses DLNA no matter what*
        if Prefs['serverwmc_playback']=='DLNA':
                if nowPlaying:
                        listing = DirectoryObject(
                                key=Callback(getProgramPage, url=url, chID=chID, chName=chName, programID=programID, title=title, name=name,
                                             summary=summary, startTime=startTime, endTime=endTime, nowPlaying=True
                                ),
                                title=title,
                                summary=summary,
                                thumb=thumb
                                )

                else:
                        listing = DirectoryObject(
                                key=Callback(getProgramPage, chID=chID, chName=chName, programID=programID, title=title, name=name,
                                             summary=summary, startTime=startTime, endTime=endTime
                                ),
                                title=title,
                                summary=summary,
                                thumb=thumb
                                )

        else:
                pass  # place holder for future use

        if DEBUG == 'Verbose':
                Log.Debug('----------CreateListing Function----------')
                Log.Debug(title + ', ' + url + ', ' + str(thumb))

        return listing

####################################################################################################
def getListingInfo(chID, progItem, infoType='Upcoming', startDt='', endDt=''):

        # Get Start and end datetime and convert to seconds
        if infoType != 'singleItem':
                startDt = getTimeS(datetime.datetime.utcnow())
                endDt = int(startDt + (timedelta(days=EPGDAYS)).total_seconds())

        # build request string
        sendCommand = 'GetEntries|{0}|{1}|{2}'.format(chID, startDt, endDt)

        # Connect and get channel/program info
        resultsArray = socketClient(sendCommand, '')

        if DEBUG=='Verbose':
                Log.Debug('----------getListingInfo Function----------')
                Log.Debug(resultsArray)

        # Loop through results array and build Channel info objects
        count = 0
        for result in resultsArray:
                count += 1
                infoArray = result.split('|')
                # only get now playing item
                if count in (1,2) and infoType in ('nowPlaying', 'upNext'):
                        programID = infoArray[0] + '-' + infoArray[16]
                        programName = infoArray[1]
                        programStartDt = getDateTime12(infoArray[3], format='datetime')
                        programEndDt = getDateTime12(infoArray[4], format='time')
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
                elif infoType == 'singleItem':
                        programID = infoArray[0] + '-' + infoArray[16]
                        programName = infoArray[1]
                        programStartDt = getDateTime12(infoArray[3], format='datetime')
                        programEndDt = getDateTime12(infoArray[4], format='time')
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

        return progData

####################################################################################################
@route(PREFIX + '/GetTimers')
def GetTimers():

        oc = ObjectContainer(title2='Scheduled Recordings', no_cache=True)

        # Connect and Get list of recordings
        resultsArray = socketClient('GetTimers', '')

        if DEBUG == 'Verbose':
                Log.Debug('----------GetTimers----------')
                Log.Debug(resultsArray)

        for result in resultsArray:
                infoArray = result.split('|')
                timerID = infoArray[0]
                chID = infoArray[1]
                startDateTime = infoArray[2]
                endDateTime = infoArray[3]
                pvr_timer_state = infoArray[4]
                if not 'series' in infoArray[5]:
                        programName = infoArray[5]
                else:
                        programName = infoArray[5].split(':')[1]
                programID = infoArray[15]
                SeriesTimerID = infoArray[16]
                programImage = getListingInfo(
                        chID=chID, progItem='programImage', infoType='singleItem', startDt=startDateTime, endDt=endDateTime
                )

                if len(SeriesTimerID) > 1:
                        programName = programName + ' (Series)'

                programInfo = '{0} - Airing : {1} - {2}'.format(
                        programName,
                        getDateTime12(startDateTime, format='datetime'),
                        getDateTime12(endDateTime)
                )

                programSummary = getListingInfo(
                        chID=chID, progItem='programOverview', infoType='singleItem', startDt=startDateTime, endDt=endDateTime
                )

                if DEBUG == 'Verbose':
                        Log.Debug(infoArray)

                oc.add(DirectoryObject(
                        key=Callback(cancelTimer, timerID=timerID, programName=programInfo, startTime=startDateTime),
                        title=programInfo,
                        summary=programSummary,
                        thumb=programImage
                        )
                )

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
@route(PREFIX + '/getProgramPage')
def getProgramPage(chID, chName, programID, title, name, summary, startTime, endTime, url='', nowPlaying=False):

        oc = ObjectContainer(title2=title, no_cache=True)

        if nowPlaying:
                oc.add(CreateVCO(url=url, title=title, summary=summary)
                )

                oc.add(DirectoryObject(
                        key=Callback(recordProgram, chID=chID, chName=chName, programID=programID, name=name, startTime=startTime, endTime=endTime),
                        title=title,
                        summary=summary,
                        thumb=R(REC_ICON)
                        )
                )
        else:
                oc.add(DirectoryObject(
                        key=Callback(recordProgram, chID=chID, chName=chName, programID=programID, name=name, startTime=startTime, endTime=endTime),
                        title=title,
                        summary=summary,
                        thumb=R(REC_ICON)
                        )
                )

        return oc

####################################################################################################
@route(PREFIX + '/createVCO/{title}')
def CreateVCO(url, title, summary, container=False):

        if VID_QUALITY=='1080':
                video_resolution = 1080
                bitrate = 20000
        elif VID_QUALITY=='720':
                video_resolution = 720
                bitrate = 7000
        elif VID_QUALITY=='480':
                video_resolution = 480
                bitrate = 3000
        else:
                video_resolution = 1080
                bitrate = 20000

        if DEBUG=='Verbose':
                Log.Debug('ServerWMC Quality : ' + VID_QUALITY)
                Log.Debug('Video Resolution : ' + str(video_resolution))
                Log.Debug('Bitrate : ' + str(bitrate))
                Log.Debug(url)

        vco = VideoClipObject(
                rating_key=url,
                key=Callback(CreateVCO, url=url, title=title, summary=summary, container=True),
                title=title,
                summary=summary,
                duration=DURATION,
                thumb=R(PLAY_ICON),
                items=[
                        MediaObject(
                                parts = [PartObject(key=url)],
                                container = "mpegts",
                                video_resolution = video_resolution,
                                bitrate = bitrate,
                                video_codec = "mpeg2video",
                                audio_codec = "AC3",
                                optimized_for_streaming = True
                                )
                        ]
                )

        if container:
                return ObjectContainer(objects=[vco])
        else:
                return vco

####################################################################################################
def recordProgram(chID, chName, programID, name, startTime, endTime):

        command = 'SetTimer|{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}|{8}|{9}|{10}|{11}|{12}'.format(
                '-1', # => epg based timer
                chID, # Channel ID
                startTime, # Start date and time of listing
                endTime,  # End date and time of listing
                str(pvr_time_state.pvr_timer_state_new),
                name, # name of listing
                '0',  #XBMc Priotiry (not used)
                '2', # pre padding in minutes
                '3',  # post padding in minutes
                'false',  # XBMC bIsRepeating (not used)
                getEntryID(programID=programID),  # ScheduleEntry ID
                'False',  # force prepad bool
                'False'   # force postpad bool
        )

        message = 'You have successfully scheduled {0} to be recorded on {1} at {2} on {3}.'.format(
                name,
                chName,
                getDateTime12(startTime, format='time'),
                getDateTime12(startTime, format='date')
        )

        responses = socketClient(command, '')
        if DEBUG == 'Verbose':
                Log.Debug('----------recordProgram----------')
                Log.Debug('Send Command:' + command)
                Log.Debug(responses)
                Log.Debug(message)
        return ObjectContainer(header='Recording', message=message)

####################################################################################################
def cancelTimer(timerID, programName, startTime):

        command = 'CancelTimer|{0}'.format(
                timerID
        )

        message = 'You have successfully cancelled the scheduled recording for {0} on {1}.'.format(
        programName,
        getDateTime12(startTime, format='date')
        )

        responses = socketClient(command, '')
        if DEBUG == 'Verbose':
                Log.Debug('----------cancelTimer----------')
                Log.Debug('Send Command:' + command)
                Log.Debug(responses)
                Log.Debug(message)
        return ObjectContainer(header='Cancelled', message=message)

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
                
                # build request string
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
                        Log.Debug('Send Command : {0}'.format(sendCommand))
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
def getDateTime12(time, format='time'):

        today = datetime.datetime.utcnow()
        today = today + TZ_DIFF
        today = today.strftime('%d')
        time_t = timedelta(seconds=int(time))
        time_t = TIME_T_REF + time_t
        time_t = time_t + TZ_DIFF
        time_tDay = time_t.strftime('%d')
        if today == time_tDay and format != 'date':
                time_t = time_t.strftime('%I:%M %p')
        else:
                if format=='datetime':
                        time_t = time_t.strftime('%m/%d %I:%M %p')
                elif format=='date':
                        time_t = time_t.strftime('%m/%d')
                elif format=='time':
                        time_t = time_t.strftime('%I:%M %p')

        return time_t

####################################################################################################
def getDateTime24(time):

        today = datetime.datetime.utcnow()
        today = today + TZ_DIFF
        today = today.strftime('%d')
        time_t = timedelta(seconds=int(time))
        time_t = TIME_T_REF + time_t
        time_t = time_t + TZ_DIFF
        time_tDay = time_t.strftime('%d')
        if today == time_tDay:
                time_t = time_t.strftime('%H:%M')
        else:
                time_t = time_t.strftime('%m/%d %H:%M')

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

####################################################################################################
def getEntryID(programID):

        entryID = programID.split('-')
        entryID = entryID[0]
        Log.Debug(entryID)
        return entryID

####################################################################################################
class pvr_time_state(enumerate):

        pvr_timer_state_new = 0         # @brief a new, unsaved timer
        pvr_timer_state_scheduled = 1   # @brief the timer is scheduled for recording
        pvr_timer_state_recording = 2   # @brieg the timer is currently recording
        pvr_timer_state_completed = 3   # @brief the recording completed successfully
        pvr_timer_state_aborted = 4     # @brief recording started, but was aborted
        pvr_timer_state_cancelled = 5   # @bried the timer was scheduled, but cancelled
        pvr_timer_state_conflict_ok = 6 # @brief the scheduled timer conflicts with another one but will be recorded
        pvr_timer_state_conflict_nok = 7# @brief the scheduled timer conflicts with another one and won't be recorded
        pvr_timer_state_error = 8       # @brief the timer is scheduled, but can't be recorded for some reason

####################################################################################################
class recordingState_wmc(enumerate):

        none = 0
        scheduled = 1
        initializing = 2
        recording = 3
        recorded = 4
        deleted = 5


