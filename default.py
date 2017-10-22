# coding=utf-8
# Copyright (C) 2017 hubsif (hubsif@gmx.de)
#
# This program is free software; you can redistribute it and/or modify it under the terms
# of the GNU General Public License as published by the Free Software Foundation;
# either version 2 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program;
# if not, see <http://www.gnu.org/licenses/>.

##############
# preparations
##############

import xbmc, xbmcplugin, xbmcgui, xbmcaddon
import os, sys, re, json, string, random, time
import xml.etree.ElementTree as ET
import urllib
import urllib2
import urlparse
import time
import md5
from datetime import datetime
from random import randint

_addon_id      = 'plugin.video.telekomsport'
_addon         = xbmcaddon.Addon(id=_addon_id)
_addon_name    = _addon.getAddonInfo('name')
_addon_handler = int(sys.argv[1])
_addon_url     = sys.argv[0]
_addon_path    = xbmc.translatePath(_addon.getAddonInfo("path") )
__language__   = _addon.getLocalizedString
_icons_path    = _addon_path + "/resources/icons/"
_fanart_path   = _addon_path + "/resources/fanart/"

xbmcplugin.setContent(_addon_handler, 'movies')

base_url = "https://www.telekomsport.de/api/v1"
oauth_url = "https://accounts.login.idm.telekom.com/oauth2/tokens"
jwt_url = "https://www.telekomsport.de/service/auth/app/login/jwt"
heartbeat_url = "https://www.telekomsport.de/service/heartbeat"
stream_url = "https://www.telekomsport.de/service/player/streamAccess"
main_page = "/navigation"

###########
# functions
###########

# helper functions

def build_url(query):
    return _addon_url + '?' + urllib.urlencode(query)

def prettydate(dt, addtime=True):
    dt = dt + utc_offset()
    if addtime:
        return dt.strftime(xbmc.getRegion("datelong") + ", " + xbmc.getRegion("time").replace(":%S", "").replace("%H%H", "%H"))
    else:
        return dt.strftime(xbmc.getRegion("datelong"))

def utc_offset():
    ts = time.time()
    return (datetime.fromtimestamp(ts) - datetime.utcfromtimestamp(ts))

def get_jwt(username, password):
    data = { "claims": "{'id_token':{'urn:telekom.com:all':null}}", "client_id": "10LIVESAM30000004901TSMAPP00000000000000", "grant_type": "password", "scope": "tsm offline_access", "username": username, "password": password }
    response = urllib.urlopen(oauth_url + '?' + urllib.urlencode(data), "").read()
    jsonResult = json.loads(response)

    if 'access_token' in jsonResult:
        response = urllib2.urlopen(urllib2.Request(jwt_url, json.dumps({"token": jsonResult['access_token']}), {'Content-Type': 'application/json'})).read()
        jsonResult = json.loads(response)
        if 'status' in jsonResult and jsonResult['status'] == "success" and 'data' in jsonResult and 'token' in jsonResult['data']:
            return jsonResult['data']['token']

def auth_media(jwt, videoid):
    try:
        response = urllib2.urlopen(urllib2.Request(heartbeat_url + '/initialize', json.dumps({"media": videoid}), {'xauthorization': jwt, 'Content-Type': 'application/json'})).read()
    except urllib2.HTTPError, error:
        response = error.read()

    try:
        urllib2.urlopen(urllib2.Request(heartbeat_url + '/destroy', "", {'xauthorization': jwt, 'Content-Type': 'application/json'})).read()
    except urllib2.HTTPError, e:
        pass

    jsonResult = json.loads(response)
    if 'status' in jsonResult and jsonResult['status'] == "success":
        return "success"
    elif 'status' in jsonResult and jsonResult['status'] == "error":
        if 'message' in jsonResult:
            return jsonResult['message']
    return __language__(30006)

# plugin call modes

def getMain():
    response = urllib.urlopen(base_url + main_page).read()
    jsonResult = json.loads(response)

    # get currently running games
    response = urllib.urlopen(base_url + jsonResult['data']['main']['target']).read()
    jsonLive = json.loads(response)
    for content in jsonLive['data']['content']:
        if content['title'] == 'Live':
            for group_element in content['group_elements']:
                if group_element['type'] == "eventLane":
                    liveevent = False
                    for data in group_element['data']:
                        if data['metadata']['state'] == 'live':
                            liveevent = True
                    if liveevent:
                        url = build_url({'mode': group_element['type'], group_element['type']: group_element['data_url'], 'onlylive': True})
                        li = xbmcgui.ListItem('[B]' + __language__(30004) + '[/B]')
                        li.setArt({'fanart': jsonLive['data']['metadata']['web']['image']})
                        xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)

    # get sports categories
    def addMainDirectoryItem(content, title):
        url = build_url({'mode': content['target_type'], content['target_type']: content['target']})
        icon = "bla"
        if 'BBL' in content['title']:
            icon = 'bbl'
        elif 'Euroleague' in content['title']:
            icon = 'euroleague'
        elif 'EuroBasket' in content['title']:
            icon = 'eurobasket'
        elif 'DEL' in content['title']:
            icon = 'del'
        elif '3. Liga' in content['title']:
            icon = '3.liga'
        elif 'Frauen-Bundesliga' in content['title']:
            icon = 'frauen-bundesliga'
        elif 'Bayern.tv' in content['title']:
            icon = 'fcbtv'
        elif u'Fußball-Bundesliga' in content['title']:
            icon = 'bundesliga'
        elif 'UEFA Champions League' in content['title']:
            icon = 'uefa'
        elif 'Handball-Bundesliga' in content['title']:
            icon = 'hbl'
        li = xbmcgui.ListItem(title)
        li.setArt({'poster': _icons_path + icon + '.png', 'fanart': _fanart_path + icon + '.jpg'})
        xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)

    for content in jsonResult['data']['filter']:
        if content['children']:
            for child in content['children']:
                addMainDirectoryItem(child, content['title'] + ' - ' + child['title'])
        else:
            addMainDirectoryItem(content, content['title'])

    xbmcplugin.endOfDirectory(_addon_handler)


def getpage():
    response = urllib.urlopen(base_url + args['page']).read()
    jsonResult = json.loads(response)

    count = 0
    for content in jsonResult['data']['content']:
        for group_element in content['group_elements']:
            if group_element['type'] in ['eventLane', 'editorialLane']:
                count += 1

    for content in jsonResult['data']['content']:
        for group_element in content['group_elements']:
            if group_element['type'] in ['eventLane', 'editorialLane']:
                if count <= 1:
                    args['eventLane'] = group_element['data_url']
                    geteventLane()
                else:
                    if content['title'] and group_element['title']:
                        li = xbmcgui.ListItem("[COLOR gold]" + content['title'].upper() + "[/COLOR]")
                        li.setProperty("IsPlayable", "false")
                        xbmcplugin.addDirectoryItem(handle=_addon_handler, url="", listitem=li)
                    title = group_element['title'] if group_element['title'] else "[B]" + content['title'].upper() + "[/B]"
                    if not title.strip():
                        title = __language__(30003)
                    url = build_url({'mode': 'eventLane', 'eventLane': group_element['data_url']})
                    li = xbmcgui.ListItem(title)
                    li.setArt({'fanart': jsonResult['data']['metadata']['web']['image']})
                    xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(_addon_handler)

def geteventLane():
    response = urllib.urlopen(base_url + args['eventLane']).read()
    jsonResult = json.loads(response)

    eventday = None;
    for event in jsonResult['data']['data']:
        if event['target_type'] == 'event':
            scheduled_start = datetime.utcfromtimestamp(int(event['metadata']['scheduled_start']['utc_timestamp']))
            if (eventday is None or (event['metadata']['state'] == "post" and scheduled_start.date() < eventday) or (event['metadata']['state'] != "post" and scheduled_start.date() > eventday)
                and not (event['metadata']['state'] != 'live' and ('onlylive' in args and args['onlylive']))):
                li = xbmcgui.ListItem("[COLOR gold]" + prettydate(scheduled_start, False) + "[/COLOR]")
                li.setProperty("IsPlayable", "false")
                xbmcplugin.addDirectoryItem(handle=_addon_handler, url="", listitem=li)
                eventday = scheduled_start.date()

            url = build_url({'mode': 'event', 'event': event['target']})
            title = __language__(30003)
            if event['metadata']['title']:
                title = event['metadata']['title']
            else:
                if event['type'] in ['teamEvent', 'skyTeamEvent'] and 'details' in event['metadata'] and 'home' in event['metadata']['details']:
                    title = event['metadata']['details']['home']['name_full'] + ' - ' + event['metadata']['details']['away']['name_full']
                elif event['metadata']['description_bold']:
                    title = event['metadata']['description_bold']
            eventinfo = event['metadata']['description_bold'] + ' - ' + event['metadata']['description_regular']
            li = xbmcgui.ListItem('[B]' + title + '[/B] (' + eventinfo + ')', iconImage='https://www.telekomsport.de' + event['metadata']['images']['editorial'])
            li.setInfo('video', {'plot': prettydate(scheduled_start)})
            li.setProperty('fanart_image', 'https://www.telekomsport.de' + event['metadata']['images']['editorial'])

            if event['metadata']['state'] == 'live':
                li.setProperty('IsPlayable', 'true')
                xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li)
            elif not ('onlylive' in args and args['onlylive']):
                xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(_addon_handler)

def getevent():
    response = urllib.urlopen(base_url + args['event']).read()
    jsonResult = json.loads(response)

    if jsonResult['data']['content'][0]['group_elements'][0]['type'] == 'noVideo':
        scheduled_start = datetime.utcfromtimestamp(int(jsonResult['data']['content'][0]['group_elements'][0]['data']['metadata']['scheduled_start']['utc_timestamp']))
        if jsonResult['data']['content'][0]['group_elements'][0]['data']['metadata']['state'] == 'pre' and scheduled_start > datetime.utcnow():
            xbmcgui.Dialog().ok(_addon_name, __language__(30001), "", prettydate(scheduled_start))
        else:
            xbmcgui.Dialog().ok(_addon_name, __language__(30002))
        xbmcplugin.endOfDirectory(_addon_handler, succeeded=False)
    else:
        hasEventVideos = 0
        for content in jsonResult['data']['content']:
            for group_element in content['group_elements']:
                if group_element['type'] == 'eventVideos':
                    for eventVideo in group_element['data']:
                        hasEventVideos += 1

        if jsonResult['data']['content'][0]['group_elements'][0]['type'] == 'player' and (not hasEventVideos or (hasEventVideos == 1 and jsonResult['data']['content'][0]['group_elements'][0]['data'][0]['videoID'] == jsonResult['data']['content'][1]['group_elements'][0]['data'][0]['videoID'])):
            isLivestream = 'islivestream' in jsonResult['data']['content'][0]['group_elements'][0]['data'][0] and jsonResult['data']['content'][0]['group_elements'][0]['data'][0]['islivestream']
            isPay = 'pay' in jsonResult['data']['content'][0]['group_elements'][0]['data'][0] and jsonResult['data']['content'][0]['group_elements'][0]['data'][0]['pay']
            url = build_url({'mode': 'video', 'videoid': jsonResult['data']['content'][0]['group_elements'][0]['data'][0]['videoID'], 'isLivestream': isLivestream, 'isPay': isPay})
            xbmc.Player().play(url)
            xbmcplugin.endOfDirectory(_addon_handler, succeeded=False)
        else:
            for content in jsonResult['data']['content']:
                for group_element in content['group_elements']:
                    if group_element['type'] == 'eventVideos':
                        for eventVideo in group_element['data']:
                            isLivestream = 'isLivestream' in eventVideo and eventVideo['isLivestream']
                            isPay = 'pay' in eventVideo and eventVideo['pay']
                            url = build_url({'mode': 'video', 'videoid': eventVideo['videoID'], 'isLivestream': isLivestream, 'isPay': isPay})
                            li = xbmcgui.ListItem(eventVideo['title'], iconImage='https://www.telekomsport.de' + eventVideo['images']['editorial'])
                            li.setProperty('fanart_image', 'https://www.telekomsport.de' + eventVideo['images']['editorial'])
                            li.setProperty('IsPlayable', 'true')
                            li.setInfo('video', {})
                            xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li)
            xbmcplugin.endOfDirectory(_addon_handler)

def getvideo():
    videoid = args['videoid']

    jwt = None
    if args['isPay'] == 'True':
        if not _addon.getSetting('username'):
            xbmcgui.Dialog().ok(_addon_name, __language__(30007))
            _addon.openSettings()
            return
        else:
            jwt = get_jwt(_addon.getSetting('username'), _addon.getSetting('password'))
            if jwt:
                auth_response = auth_media(jwt, videoid)
                if auth_response != "success":
                    xbmcgui.Dialog().ok(_addon_name, auth_response)
                    return
            else:
                xbmcgui.Dialog().ok(_addon_name, __language__(30005))
                return

    jwt = jwt or 'empty'

    response = urllib2.urlopen(urllib2.Request(stream_url, json.dumps({ 'videoId': videoid}), {'xauthorization': jwt, 'Content-Type': 'application/json'})).read()
    jsonResult = json.loads(response)
    url = 'https:' + jsonResult['data']['stream-access'][0]

    response = urllib.urlopen(url).read()

    xmlroot = ET.ElementTree(ET.fromstring(response))
    playlisturl = xmlroot.find('token').get('url')
    auth = xmlroot.find('token').get('auth')

    listitem = xbmcgui.ListItem(path=playlisturl + "?hdnea=" + auth)
    xbmcplugin.setResolvedUrl(_addon_handler, True, listitem)


##############
# main routine
##############

# urllib ssl fix
import ssl
from functools import wraps
def sslwrap(func):
    @wraps(func)
    def bar(*args, **kw):
        kw['ssl_version'] = ssl.PROTOCOL_TLSv1
        return func(*args, **kw)
    return bar
ssl.wrap_socket = sslwrap(ssl.wrap_socket)

# get arguments
args = dict(urlparse.parse_qsl(sys.argv[2][1:]))
mode = args.get('mode', None)

if mode is None:
    mode = "Main"

locals()['get' + mode]()
