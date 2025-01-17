# -*- coding: utf-8 -*-

import xbmc, xbmcaddon, xbmcgui, xbmcplugin, xbmcvfs
import os, sys, re, string, socket, unicodedata, shutil, time, platform, json
import urllib.parse, urllib.error, urllib.request

def normalize_string(txt):
    return unicodedata.normalize('NFKD', txt)

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonname__    = __addon__.getAddonInfo('name')
__addonversion__ = __addon__.getAddonInfo('version')
__icon__         = __addon__.getAddonInfo('icon')
__language__     = __addon__.getLocalizedString
__platform__     = platform.system() + " " + platform.release()
__profile__      = xbmc.translatePath( normalize_string(__addon__.getAddonInfo('profile') ))
__temp__         = xbmc.translatePath( normalize_string(os.path.join( __profile__, 'temp') ))

sys.path.append( os.path.join( __profile__, "lib") )

self_host = "http://api.betaseries.com"
self_apikey = "5a85a0adc953"
self_apiver = "2.4"
self_team_pattern = re.compile(r".*-([^-]+)$")
self_notify = __addon__.getSetting('notify') == 'true'

TEAMS = (
    # SD[0]              HD[1]
    ("lol|sys|dim",      "dimension"),
    ("asap|xii|fqm|imm", "immerse|orenji"),
    ("excellence",       "remarkable"),
    ("2hd|xor",          "ctu"),
    ("tla",              "bia"))

LANGUAGES = (
    # [0]  [1]
    ("br", "pt"),
    ("gr", "el"))

def other_team(team, team_from, team_to):
    # get other team using TEAMS table
    for x in TEAMS:
        if len(re.findall(x[team_from], team)) > 0:
            return x[team_to]
    # return team if not found
    log("other team not found")
    return team

def normalize_lang(lang, lang_from, lang_to):
    # normalize lang using LANGUAGES table
    for x in LANGUAGES:
        if len(re.findall(x[lang_from], lang)) > 0:
            return x[lang_to]
    # return lang if not found
    return lang

def log(txt, level=xbmc.LOGDEBUG):
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message, level=level)

def set_user_agent():
    json_query = json.loads(xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }'))
    try:
        major = str(json_query['result']['version']['major'])
        minor = str(json_query['result']['version']['minor'])
        name = "Kodi" if int(major) >= 14 else "XBMC"
        version = "%s %s.%s" % (name, major, minor)
    except:
        log("could not get app version")
        version = "XBMC"
    return "Mozilla/5.0 (compatible; " + __platform__ + "; " + version + "; " + __addonid__ + "/" + __addonversion__ + ")"

def get_params(string=""):
  param=[]
  if string == "":
    paramstring=sys.argv[2]
  else:
    paramstring=string 
  if len(paramstring)>=2:
    params=paramstring
    cleanedparams=params.replace('?','')
    if (params[len(params)-1]=='/'):
      params=params[0:len(params)-2]
    pairsofparams=cleanedparams.split('&')
    param={}
    for i in range(len(pairsofparams)):
      splitparams={}
      splitparams=pairsofparams[i].split('=')
      if (len(splitparams))==2:
        param[splitparams[0]]=splitparams[1]
                                
  return param

def get_url(url, referer=self_host):
    req_headers = {
    'User-Agent': self_user_agent,
    'Cache-Control': 'no-store, no-cache, must-revalidate',
    'Pragma': 'no-cache',
    'Referer': referer}
    request = urllib.request.Request(url, headers=req_headers)
    opener = urllib.request.build_opener()
    try:
        response = opener.open(request)
        contents = response.read()
        return contents
    except urllib.error.HTTPError as e:
        log('HTTPError = ' + str(e.code), xbmc.LOGERROR)
        if e.code == 400:
            return False
    except urllib.error.URLError as e:
        log('URLError = ' + str(e.reason), xbmc.LOGERROR)
    except Exception:
        import traceback
        log('generic exception: ' + traceback.format_exc(), xbmc.LOGERROR)
    # when error occured
    if self_notify:
        xbmc.executebuiltin((u'Notification(%s,%s,%s,%s)' % (__addonname__, __language__(30008), 750, __icon__)).encode('utf-8', 'ignore'))
    return False

def download_subtitle(url, ext, subversion, referer):
    # name of temp file for download
    local_tmp_file = os.path.join(__temp__, "betaseries." + ext)
    log("downloading url : %s" % (url))
    socket.setdefaulttimeout(15)
    content = get_url(url, referer)
    if content:
        local_file_handle = open(local_tmp_file, "w" + "b")
        local_file_handle.write(content)
        local_file_handle.close()
        log("file extension is : %s" % (ext))
        if ext in ['zip','rar']:
            files = os.listdir(__temp__)
            init_filecount = len(files)
            log("number of files : %s" % (init_filecount))
            filecount = init_filecount
            log("extracting zip file : %s" % (local_tmp_file))
            xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + __temp__ +")")
            waittime  = 0
            while (filecount == init_filecount) and (waittime < 20): # nothing yet extracted
                time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
                files = os.listdir(__temp__)
                filecount = len(files)
                waittime = waittime + 1
            # if max waittime reached
            if waittime == 20:
                log("error unpacking files in : %s" % (__temp__))
            else:
                log("unpacked files in : %s" % (__temp__))
                time.sleep(1)
                files = os.listdir(__temp__)
                log("looking for %s" % (subversion))
                for filename in files:
                    log("checking file %s" % (filename))
                    if normalize_string(filename) == subversion:
                        filepath = os.path.normpath(os.path.join(__temp__, filename))
                        log("selected file : %s" % (filename))
                        return filepath
        else:
            log("selected file : %s" % (subversion))
            return local_tmp_file
    else:
        return False

def search_subtitles(search):
    subtitles = []
    log("entering search_subtitles()")
    if search['mode'] == "movie":
        log("movies not supported!")
        return False
    # get video file name
    dirsync = __addon__.getSetting('dirsync') == 'true'
    if dirsync:
        # get directory name as filename
        filename = os.path.basename(os.path.dirname(search['path'])).lower()
    else:
        # or use filename
        filename = os.path.basename(search['path']).lower()
        # and remove file extension
        filename = re.sub(r"\.[^.]+$", "", filename)
    filename = normalize_string(filename)
    log("after filename = %s" % (filename))
    # if file, check if valid tvshow
    if search['mode'] == "file" and not re.search(r"(?i)(s[0-9]+e[0-9]+|[0-9]+x?[0-9]{2,})", filename):
        log("not a tvshow or badly named!")
        return False
    # get subtitle team
    subteams = []
    subteams.append(filename.replace(".","-"))
    if len(subteams[0]) > 0:
        # get team name (everything after "-")
        subteams[0] = self_team_pattern.match("-" + subteams[0]).groups()[0].lower()
        # find equivalent teams, if any
        tmp = other_team(subteams[0],0,1)
        if len(tmp) > 0 and tmp != subteams[0]:
            subteams.append(tmp)
        # find other equivalent teams, if any
        tmp = other_team(subteams[0],1,0)
        if len(tmp) > 0 and tmp != subteams[0]:
            subteams.append(tmp)
    log("after subteams = %s" % (subteams))
    # configure socket
    socket.setdefaulttimeout(10)
    # define default url to get betaseries episode id from filename
    episodeurl = "%s/episodes/scraper?file=%s&key=%s&v=%s" % (self_host, urllib.parse.quote(filename), self_apikey, self_apiver)
    # check video type
    if search['mode'] == "tvshow":
        # get playerid
        json_query = '{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}'
        playerid = json.loads(xbmc.executeJSONRPC(json_query))['result'][0]['playerid']
        # get tvshowid
        json_query = '{"jsonrpc": "2.0", "method": "Player.GetItem", "params": {"playerid": ' + str(playerid) + ', "properties": ["tvshowid"]}, "id": 1}'
        tvshowid = json.loads(xbmc.executeJSONRPC (json_query))['result']['item']['tvshowid']
        # check result
        if tvshowid > 0:
            # get tvdbid
            json_query = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": {"tvshowid": ' + str(tvshowid) + ', "properties": ["imdbnumber"]}, "id": 1}'
            tvdbid_result = json.loads(xbmc.executeJSONRPC(json_query))
            # if we have tvdbid, work with ids
            if 'result' in tvdbid_result:
                # get betaseries show id from tvdbid
                tvdbid = tvdbid_result['result']['tvshowdetails']['imdbnumber']
                showurl = "%s/shows/display?thetvdb_id=%s&key=%s&v=%s" % (self_host, tvdbid, self_apikey, self_apiver)
                try:
                    showid = json.loads(get_url(showurl))["show"]["id"]
                except:
                    log("could not parse data or fetch url for showid, cannot continue")
                    return False
                log("after showid = %s" % (showid))
                # then get betaseries episode id
                episodeurl = "%s/episodes/search?show_id=%s&number=S%#02dE%#02d&key=%s&v=%s" % (self_host, showid, int(search['season']), int(search['episode']), self_apikey, self_apiver)
    try:
        episodeid = json.loads(get_url(episodeurl))["episode"]["id"]
        log("after episodeid = %s" % (episodeid))
    except:
        log("error or episode not found!")
        return False
    # then get subtitles list
    listurl = "%s/subtitles/episode?id=%s&key=%s&v=%s" % (self_host, episodeid, self_apikey, self_apiver)
    try:
        data = json.loads(get_url(listurl))["subtitles"]
    except:
        log("could not parse data or fetch url, cannot continue")
        return False
    # for each release version
    log("parsing data after urlopen")
    log("--------------------------")
    for subtitle in data:
        # get filename
        subfile = normalize_string(subtitle["file"])
        log("after subfile = %s" % (subfile))
        # get file extension
        ext = subfile.split('.')[-1]
        # get season number from data
        season = int(subtitle["episode"]["season"])
        log("after season = %s" % (season))
        # get episode number from data
        episode = int(subtitle["episode"]["episode"])
        log("after episode = %s" % (episode))
        # get names of files contained in zip file, if any
        if len(subtitle["content"]) > 0:
            content = subtitle["content"]
        # or put filename in content
        else:
            content = [subtitle["file"]]
        log("after content = %s" % (content))
        # for each file in content
        for subversion in content:
            log("-------------")
            # subtitle file name
            subversion = normalize_string(subversion)
            log("after subversion = %s" % (subversion))
            # subtitle download url
            link = subtitle["url"]
            log("after link = %s" % (link))
            try:
                # normalize lang
                lang2 = {
                    "VO": "en",
                    "VF": "fr",
                    "VOVF": "xx",
                }[subtitle["language"]]
            except:
                log("unsupported language")
                continue 
            # get note
            if 0 <= int(subtitle["quality"]) <= 5:
                note = int(subtitle["quality"])
            else:
                note = 0
            log("after note = %s" % (note))
            # check if file is a subtitle
            if not len(re.findall(r"(?i)\.(srt|ssa|ass|sub)$", subversion)):
                log("not a subtitle : %s" % (subversion))
                continue
            # if from a zip file
            if len(content) > 1:
                # check if file is for correct season and episode
                search_string = r"(?i)(s%#02de%#02d|%d%#02d|%dx%#02d)" % (season, episode, season, episode, season, episode)
                if not re.search(search_string, subversion):
                    log("file not matching episode : %s" % (subversion))
                    continue
                # get subtitle file lang
                langs = re.search(r"(?i)[ _.-](english|french|eng|fre|en|fr|vo|vf)[ _.-]", subversion)
                # or get zip file lang
                if langs == None:
                    langs = lang2
                else:
                    langs = langs.group(1).lower()
                log("after zip langs = %s" % (lang2))
                try:
                    lang2 = {
                        "french": 'fr',
                        "english": 'en',
                        "fre": 'fr',
                        "eng": 'en',
                        "fr": 'fr',
                        "en": 'en',
                        "vf": 'fr',
                        "vo": 'en'
                    }[langs]
                except:
                    log("unsupported language")
                    continue
                log("after zip lang2 = %s" % (lang2))
            try:
                # get full language name
                lang = xbmc.convertLanguage(lang2, xbmc.ENGLISH_NAME)
            except:
                log("unsupported language")
                continue
            # if lang = user gui language
            if lang == search['uilang']:
                # put this file on top
                uilang = True
            else:
                uilang = False
            log("after lang = %s, lang2 = %s" % (lang, lang2))
            # check sync
            sync = False
            team = False
            for (key, subteam) in enumerate(subteams):
                # if team corresponds
                if len(subteam) > 0 and len(re.findall(r"(?i)[ _.-](" + subteam + ")[ _.-]", subversion)) > 0:
                    # set sync tag
                    sync = True
                    # if videofile team matches subfile team
                    if key == 0:
                        team = True
            log("after sync = %s" % (sync))
            # check if this is for hearing impaired
            if len(re.findall(r"(?i)[ _.-](CC|HI)[ _.-]", subversion)) > 0:
                cc = True
            else:
                cc = False
            log("after cc = %s" % (cc))
            # if language allowed by user
            if lang2 in search['langs']:
                # add subtitle to list
                subtitles.append({'uilang':uilang,'ext':ext,'filename':subversion,'link':link,'lang':lang,'lang2':lang2,"cc":cc,"sync":sync,"note":note,"team":team})
                log("subtitle added : %s" % (subversion))
        log("--------------------------")
    if subtitles:
        # get settings for sorting
        uifirst = __addon__.getSetting('uifirst') == 'true'
        ccfirst = __addon__.getSetting('ccfirst') == 'true'
        # sort accordingly
        log("sorting by filename asc")
        subtitles.sort(key=lambda x: [x['filename']])
        if not ccfirst:
            log("sorting by cc last")
            subtitles.sort(key=lambda x: [x['cc']])
        log("sorting by note best")
        subtitles.sort(key=lambda x: [x['note']], reverse=True)
        log("sorting by lang asc")
        subtitles.sort(key=lambda x: [x['lang']])
        if ccfirst:
            log("sorting by cc first")
            subtitles.sort(key=lambda x: [not x['cc']])
        if uifirst:
            log("sorting by uilang first")
            subtitles.sort(key=lambda x: [not x['uilang']])
        log("sorting by sync first")
        subtitles.sort(key=lambda x: [not x['sync']])
        log("sorting by team first")
        subtitles.sort(key=lambda x: [not x['team']])
        log("sorted subtitles = %s" % (subtitles))
        # for each subtitle
        for item in subtitles:
            # xbmc list item format
            listitem = xbmcgui.ListItem(label=item["lang"], label2=item["filename"])
            listitem.setArt({ 'icon': str(item["note"]), 'thumb': item["lang2"]})
            # setting sync / CC tag
            listitem.setProperty("sync", 'true' if item["sync"] else 'false')
            listitem.setProperty("hearing_imp", 'true' if item["cc"] else 'false')
            # adding item to GUI list
            url = "plugin://%s/?action=download&link=%s&ext=%s&filename=%s" % (__addonid__, item["link"], item["ext"], urllib.parse.quote(item["filename"]))
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)
    else:
        if self_notify:
            xbmc.executebuiltin((u'Notification(%s,%s,%s,%s)' % (__addonname__, __language__(30010), 750, __icon__)).encode('utf-8', 'ignore'))
        log("nothing found")
    log("end of search_subtitles()")

# start of script

# clean up
if os.path.exists(__temp__):
    log("deleting temp tree...")
    shutil.rmtree(__temp__.encode("utf-8","ignore"))
log("recreating temp dir...")
xbmcvfs.mkdirs(__temp__)

# define user-agent
self_user_agent = set_user_agent()

# get params
params = get_params()

# called when user is searching for subtitles
if params['action'] == 'search':
    item = {}
    item['tvshow']  = normalize_string(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))
    item['year']    = xbmc.getInfoLabel("VideoPlayer.Year")
    item['season']  = xbmc.getInfoLabel("VideoPlayer.Season")
    item['episode'] = xbmc.getInfoLabel("VideoPlayer.Episode")
    item['path']    = urllib.parse.unquote(normalize_string(xbmc.Player().getPlayingFile()))
    item['uilang']  = xbmc.getLanguage()
    item['langs']   = []
    # get user preferred languages for subtitles
    for lang in urllib.parse.unquote(normalize_string(params['languages'])).split(","):
        item['langs'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_1))
    # remove rar:// or stack://
    if ( item['path'].find("rar://") > -1 ):
        item['path'] = os.path.dirname(item['path'][6:])
    elif ( item['path'].find("stack://") > -1 ):
        stackPath = item['path'].split(" , ")
        item['path'] = stackPath[0][8:]
    # show item data in debug log
    log("after item = %s" % (item))
    # find playing mode
    if len(item['tvshow']) > 0: item['mode'] = "tvshow"
    elif item['year'] != "": item['mode'] = "movie"
    else: item['mode'] = "file"
    # search for subtitles
    search_subtitles(item)

# called when user clicks on a subtitle
elif params['action'] == 'download':
    # download link
    sub = download_subtitle(params["link"], params["ext"], urllib.parse.unquote(params["filename"]), self_host)
    if sub:
        # xbmc handles moving and using the subtitle
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub,listitem=listitem,isFolder=False)

xbmcplugin.endOfDirectory(int(sys.argv[1]))
