TIME_MIN = datetime.datetime(1900, 1, 1, 0, 0)
TIME_T_REF = datetime.datetime(1970, 1, 1, 0, 0)
TZ_DIFF = timedelta(seconds=0)
DEBUG = Prefs['debug_level']

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
def createStreamID(streamType):

        if streamType=='liveTV':
                streamID = '1'
        elif streamType=='recording':
                streamID = '2'
        else :
                streamID = '9'

        streamID = streamID + str(getPlatformInt(str(Client.Platform)))

        return streamID

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
def getPlatformInt(platform):

        if platform=='Chrome':
                return 1
        elif platform=='iOS':
                return 2
        elif platform=='tvOS':
                return 2
        elif platform=='Android':
                return 3
        elif platform=='Roku':
                return 4
        elif platform=='Windows':
                return 5
        elif platform=='Linux':
                return 6
        elif platform=='LGTV':
                return 7
        elif platform=='Internet Explorer':
                return 8
        elif platform=='Plex Home Theater':
                return 9
        else:
                return 99
