# -*- coding: cp1252 -*-
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
import utilities as u
import os

PREFIX = '/video/wmc2plex'
NAME = 'PlexWMC'
ART = 'art-default.jpg'
REC_ICON = 'record_icon.png'
PLAY_ICON = 'play_icon.png'
CHANNEL_ICON = 'channels.png'
TIMER_ICON = 'timers_icon.png'
SETTINGS_ICON = 'settings_icon.png'
RECORDEDTV_ICON = 'recordedtv_icon.png'
DEL_ICON = 'del_icon.png'
SERVERWMC_IP = Prefs['serverwmc_ip']
SERVERWMC_PORT = Prefs['serverwmc_port']
SERVERWMC_ADDR = (SERVERWMC_IP, int(SERVERWMC_PORT))
VERSION = '0.8.2'
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
        u.getTimeDif()
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
        oc.add(DirectoryObject(key = Callback(SubMenu, menu='Channels'), title='Channels', thumb=R(CHANNEL_ICON)))
        oc.add(DirectoryObject(key = Callback(GetTimers), title='Scheduled Recordings', thumb=R(TIMER_ICON)))
        oc.add(DirectoryObject(key = Callback(GetRecordings), title='Recorded TV', thumb=R(RECORDEDTV_ICON)))

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
                        #channelImageFile = channelArray[5].split('/')[-1]
                        channelImageFile = channelArray[5]
                        if channelImageFile=='':
                                channelImageFile = R(ART)
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
                                CreateChannel, url=channelURL, chID=channelID, title=channelTitle, thumb=Thumb),
                                title=channelTitle, summary=Summary, thumb=Thumb))

        return oc

####################################################################################################
@route(PREFIX + '/CreateChannel/{chID}')
def CreateChannel(url, chID, title, thumb):

        oc = ObjectContainer(title2=title, no_cache=True)

        #closeLiveStream()

        # Get Start and end datetime and convert to seconds
        startDt = u.getTimeS(datetime.datetime.utcnow())
        endDt = int(startDt + (timedelta(days=EPGDAYS)).total_seconds())

        # build request string
        sendCommand = 'GetEntries|{0}|{1}|{2}'.format(chID, startDt, endDt)

        # Connect and get channel/program info
        resultsArray = socketClient(sendCommand, '')

        if DEBUG=='Verbose':
                Log.Debug('----------CreateChannel Function----------')
                Log.Debug(resultsArray)

        # Loop through resultsArray to build Channel objects
        if len(resultsArray) > 1:
                for result in resultsArray:
                        infoArray = result.split('|')
                        programID = infoArray[0] + '-' + infoArray[16]
                        programName = infoArray[1]
                        programStartDt24 = u.getDateTime24(infoArray[3])
                        programEndDt24 = u.getDateTime24(infoArray[4])
                        programStartDt12 = u.getDateTime12(infoArray[3], format='datetime')
                        programEndDt12 = u.getDateTime12(infoArray[4], format='time')
                        programAirTime = '(' + programStartDt12 + ' - ' + programEndDt12 + ') '
                        programOverview = infoArray[5]
                        if infoArray[14]=='None':
                                programImage = R(thumb)
                        else:
                                programImage = infoArray[14]
                        programEpisodeTitle = infoArray[15]
                        try:
                                programRating = u.getRating(infoArray[8])
                        except:
                                programRating = 'NR'
                        programTitle = programAirTime + programName

                        if DEBUG=='Verbose':
                                Log.Debug(programID + ',' + programTitle + ',' + programStartDt24 + ',' + programEndDt24 +
                                        ',' + programOverview + ',' + programRating)
                        if programStartDt24 <= u.getDateTime24(startDt) <= programEndDt24:
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
        else:
                oc.add(
                        CreateListing(
                                url=url,
                                chID=chID,
                                chName=title,
                                programID='99',
                                title='No EPG Info Available',
                                name='No EPG Info Available',
                                summary='No EPG Info Available.  Check WMC for more info.',
                                startTime = 1423072800,
                                endTime = 1423072800 + DURATION,
                                thumb=R(PLAY_ICON),
                                nowPlaying=True
                                ))

        return oc

####################################################################################################
@route(PREFIX + '/CreateListing/{chID}')
def CreateListing(url, chID, chName, programID, title, name, summary, thumb, startTime, endTime, nowPlaying=False):

        if nowPlaying:
                listing = DirectoryObject(
                        key=Callback(getProgramPage, url=url, chID=chID, chName=chName, programID=programID, title=title, name=name,
                                     summary=summary, startTime=startTime, endTime=endTime, itemType='nowplaying'
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

        if DEBUG == 'Verbose':
                Log.Debug('----------CreateListing Function----------')
                Log.Debug(title + ', ' + url + ', ' + str(thumb))

        return listing

####################################################################################################
def getListingInfo(chID, progItem, infoType='Upcoming', startDt='', endDt=''):

        # Get Start and end datetime and convert to seconds
        if infoType != 'singleItem':
                startDt = u.getTimeS(datetime.datetime.utcnow())
                endDt = int(startDt + (timedelta(days=EPGDAYS)).total_seconds())

        # build request string
        sendCommand = 'GetEntries|{0}|{1}|{2}'.format(chID, startDt, endDt)

        # Connect and get channel/program info
        resultsArray = socketClient(sendCommand, '')

        if DEBUG=='Verbose':
                Log.Debug('----------getListingInfo Function----------')
                Log.Debug(resultsArray)

        # Loop through results array and build Channel info objects
        if len(resultsArray) > 1:
                count = 0
                for result in resultsArray:
                        count += 1
                        infoArray = result.split('|')
                        # only get now playing item
                        if count in (1,2) and infoType in ('nowPlaying', 'upNext'):
                                programID = infoArray[0] + '-' + infoArray[16]
                                programName = infoArray[1]
                                programStartDt = u.getDateTime12(infoArray[3], format='datetime')
                                programEndDt = u.getDateTime12(infoArray[4], format='time')
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
                                programStartDt = u.getDateTime12(infoArray[3], format='datetime')
                                programEndDt = u.getDateTime12(infoArray[4], format='time')
                                programAirTime = '(' + programStartDt + ' - ' + programEndDt + ') '
                                programOverview = infoArray[5]
                                programImage = infoArray[14]
                                programEpisodeTitle = infoArray[15]
                                try:
                                        programRating = u.getRating(infoArray[8])
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

        else:
                progData = 'No Listing Info : Update WMC Guide Data and/or check WMC logs for details.'

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
                        u.getDateTime12(startDateTime, format='datetime'),
                        u.getDateTime12(endDateTime)
                )

                programSummary = unicode(infoArray[7], 'UTF-8')

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
@route(PREFIX + '/getLiveStream')
def getLiveStream(channelID):

        # Currently not used.  Open and closing of streams is being handled on swmc side.
        newStream = False
        # Build channel stream variables *leading 1 denotes liveTV*
        streamID = u.createStreamID(streamType='liveTV')

        StreamInfo = socketClient('GetPlexLiveStreamInfo', '')
        Log.Debug(StreamInfo)
        if len(StreamInfo) > 1 :
                for info in StreamInfo:
                        infoArray = info.split('|')
                        if infoArray[0] != '':
                                activeStreamID = infoArray[0]
                        else:
                                activeStreamID = ''
                        if infoArray[1]==channelID and activeStreamID==streamID:
                                liveStreamUrl = infoArray[2]
                        elif infoArray[1]!=channelID and activeStreamID==streamID:
                                closeLiveStream()
                                newStream = True
                        else:
                                liveStreamUrl = ''

                        Log.Debug(status + ' - ' + str(activeStreamID))
        else:
                newStream = True

        # Build Command string
        command = "OpenLiveStream|" + channelID + "|" + GETSTREAMINFO

        # connect and retrieve channel stream path
        if DEBUG == 'Normal' or DEBUG == 'Verbose':
                Log.Debug('START STREAM -----------------------------------------------------------')

        if newStream:
                responses = socketClient(command, streamID)
                liveStreamUrl = responses[0]

        if DEBUG == 'Verbose':
                Log.Debug('----------getLiveStream Function----------')
                Log.Debug(streamID + ' - ' + liveStreamUrl)

        return liveStreamUrl

####################################################################################################
@route(PREFIX + '/getRecordingStream')
def getRecordingStream(recordingID):

        # Currently not used.  Open and closing of streams is being handled on swmc side.
        newStream = False
        # Build channel stream variables *leading 2 denotes Recording*
        streamID = u.createStreamID(streamType='recording')

        StreamInfo = socketClient('GetPlexLiveStreamInfo', '')
        Log.Debug(StreamInfo)
        if len(StreamInfo) > 1 :
                for info in StreamInfo:
                        infoArray = info.split('|')
                        if infoArray[0] != '':
                                activeStreamID = infoArray[0]
                        else:
                                activeStreamID = ''
                        if infoArray[1]==recordingID and activeStreamID==streamID:
                                recordingStreamUrl = infoArray[2]
                        elif infoArray[1]!=recordingID and activeStreamID==streamID:
                                closeLiveStream()
                                newStream = True
                        else:
                                recordingStreamUrl = ''

                        Log.Debug(status + ' - ' + str(activeStreamID))
        else:
                newStream = True

        # Build Command string
        command = "OpenRecordingStream|" + recordingID + "|" + GETSTREAMINFO

        # connect and retrieve channel stream path
        if DEBUG == 'Normal' or DEBUG == 'Verbose':
                Log.Debug('START STREAM -----------------------------------------------------------')

        if newStream:
                responses = socketClient(command, streamID)
                recordingStreamUrl = responses[0]

        if DEBUG == 'Verbose':
                Log.Debug('----------getRecordingStream Function----------')
                Log.Debug(streamID + ' - ' + recordingStreamUrl)

        return recordingStreamUrl

####################################################################################################
@route(PREFIX + '/getProgramPage')
def getProgramPage(chID, chName, programID, title, name, summary, startTime, endTime, duration =0, url='', itemType=''):

        oc = ObjectContainer(title2=title, no_cache=True)

        if duration==0:
                programDuration = (int(endTime) - int(startTime)) * 1000
        else:
                programDuration = duration
        if DEBUG=='Verbose':
                Log.Debug('----------getProgramPage Function----------')
                Log.Debug(str(endTime) + ' - ' + str(startTime) + ' = ' + str(programDuration))

        if itemType=='nowplaying':
                #url = getLiveStream(channelID=chID)
                oc.add(CreateVCO(url=url, title='Play : ' + title, summary=summary, duration=DURATION)
                )

                oc.add(DirectoryObject(
                        key=Callback(recordProgram, chID=chID, chName=chName, programID=programID, name=name, startTime=startTime, endTime=endTime),
                        title='Record : ' + title,
                        summary=summary,
                        thumb=R(REC_ICON)
                        )
                )
        elif itemType=='recordings':
                #url = getRecordingStream(recordingID=programID)
                oc.add(CreateVCO(url=url, title='Play : '  + title, summary=summary, duration=programDuration)
                )

                oc.add(DirectoryObject(
                        key=Callback(deleteRecording, recordingID=programID, recordingName=name),
                        title='Delete : ' + title,
                        summary=summary,
                        thumb=R(DEL_ICON)
                        )
                )
        else:
                oc.add(DirectoryObject(
                        key=Callback(recordProgram, chID=chID, chName=chName, programID=programID, name=name, startTime=startTime, endTime=endTime),
                        title='Record : ' + title,
                        summary=summary,
                        thumb=R(REC_ICON)
                        )
                )

        return oc

####################################################################################################
@route(PREFIX + '/createVCO/{title}')
def CreateVCO(url, title, summary, duration, container=False):

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

        urlExtension = os.path.splitext(url)[1][1:]

        if DEBUG=='Verbose':
                Log.Debug('----------createVCO Function----------')
                Log.Debug('ServerWMC Quality : ' + VID_QUALITY)
                Log.Debug('Video Resolution : ' + str(video_resolution))
                Log.Debug('Bitrate : ' + str(bitrate))
                Log.Debug('Duration : ' + str(duration))
                Log.Debug('Extension : ' + str(urlExtension))
                Log.Debug(url)

        mo = MediaObject(
                parts = [PartObject(key=url)],
                container = "mpegts",
                video_resolution = video_resolution,
                bitrate = bitrate,
                video_codec = "mpeg2video",
                audio_codec = "AC3",
                optimized_for_streaming = True
                )

        vco = VideoClipObject(
                rating_key=url,
                key=Callback(CreateVCO, url=url, title=title, summary=summary, duration=duration, container=True),
                title=title,
                summary=summary,
                duration=int(duration),
                thumb=R(PLAY_ICON),
                items=[
                        mo
                        ]
                )

        if container:
                return ObjectContainer(objects=[vco])
        else:
                return vco

####################################################################################################
@route(PREFIX + '/getrecordings')
def GetRecordings():

        oc = ObjectContainer(title2='Recorded TV', no_cache=True)

        # Connect and Get list of recordings
        resultsArray = socketClient('GetRecordings', '')
        Log.Debug('----------GetRecordings Function----------')
        if DEBUG == 'Verbose':
                Log.Debug(resultsArray)

        for result in resultsArray:
                infoArray = result.split('|')
                programID = infoArray[0]
                programName = infoArray[1]
                programURL = infoArray[2]
                programSummary = L(infoArray[5])
                programChannel = infoArray[6]
                programImage = infoArray[7]
                startDtTime = infoArray[9]
                endDtTime = int(infoArray[9]) + int(infoArray[10])
                duration = int(infoArray[11])
                airedDate = u.getDateTime12(infoArray[21], format='date')

                if DEBUG=='Verbose':
                        Log.Debug(programName + ', ' + programImage +', ' + programSummary +', ' + programChannel + ', ' + programImage)
                        Log.Debug(str(startDtTime) + ' - ' + str(endDtTime))

                oc.add(DirectoryObject(
                        key=Callback(getProgramPage, chID='', chName=programChannel, programID=programID, title=programName, name=programName,
                                     summary=programSummary, startTime=startDtTime, endTime=endDtTime, url=programURL, itemType='recordings'
                        ),
                        title=programName,
                        summary='(Aired: ' + str(airedDate) + ') ' + programSummary,
                        thumb=programImage
                ))

                if DEBUG == 'Verbose':
                        Log.Debug(infoArray)

        return oc

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
                u.getEntryID(programID=programID),  # ScheduleEntry ID
                'False',  # force prepad bool
                'False'   # force postpad bool
        )

        message = 'You have successfully scheduled {0} to be recorded on {1} at {2} on {3}.'.format(
                name,
                chName,
                u.getDateTime12(startTime, format='time'),
                u.getDateTime12(startTime, format='date')
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
        u.getDateTime12(startTime, format='date')
        )

        responses = socketClient(command, '')
        if DEBUG == 'Verbose':
                Log.Debug('----------cancelTimer----------')
                Log.Debug('Send Command:' + command)
                Log.Debug(responses)
                Log.Debug(message)
        return ObjectContainer(header='Cancelled', message=message)

####################################################################################################
def deleteRecording(recordingID, recordingName):

        command = 'DeleteRecording|{0}'.format(
                recordingID
        )

        responses = socketClient(command, '')
        message = 'You have successfully deleted {0}.'.format(
                recordingName
        )
        if DEBUG == 'Verbose':
                Log.Debug('----------deleteRecording----------')
                Log.Debug('Send Command:' + command)
                Log.Debug(responses)
                Log.Debug(message)

        return ObjectContainer(header='Deleted', message=message)

####################################################################################################
def closeLiveStream():
        # Currently not used.  Open and closing of streams is being handled on swmc side.
        # Close Stream
        command = "CloseLiveStream"
        socketClient(command, u.createStreamID(streamType='liveTV'))

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
        Log.Debug(Request.Headers)

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
                resultsArray.decode(encoding='UTF-8', errors='strict')

        except:
                Log.Error('Trying to connect to ' + ''.join(SERVERWMC_IP) + ':'
                          + ''.join(SERVERWMC_PORT) + ' ServerWMC: Not detected. Check IP and Port.')
        finally:
                # Release socket
                sock.shutdown(2)
                sock.close()

        return resultsArray

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
