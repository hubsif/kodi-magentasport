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

dtformat = '%Y-%m-%d %H:%M:%S'

###########
# functions
###########

def build_url(query):
    return _addon_url + '?' + urllib.urlencode(query)

def convertdatetime(dt, sourceformat):
    try:
        return datetime.strptime(dt, sourceformat)
    except TypeError:
        return datetime(*(time.strptime(dt, sourceformat)[0:6]))

def prettydate(dt, addtime=True):    
    if addtime:
        return dt.strftime(xbmc.getRegion("datelong") + ", " + xbmc.getRegion("time").replace(":%S", "").replace("%H%H", "%H"))
    else:
        return dt.strftime(xbmc.getRegion("datelong"))

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
    response = urllib.urlopen("https://www.telekomsport.de/api/v1/navigation").read()
    jsonResult = json.loads(response)
    
    for content in jsonResult['data']['filter']:
        for child in content['children']:
            url = build_url({'mode': child['target_type'], child['target_type']: child['target']})
            if 'BBL' in child['title']:
                icon = 'bbl'
            elif 'Euroleague' in child['title']:
                icon = 'euroleague'
            elif 'DEL' in child['title']:
                icon = 'del'
            elif '3. Liga' in child['title']:
                icon = '3.liga'
            elif 'Frauen-Bundesliga' in child['title']:
                icon = 'frauen-bundesliga'
            li = xbmcgui.ListItem(content['title'] + ' - ' + child['title'])
            li.setArt({'poster': _icons_path + icon + '.png', 'fanart': _fanart_path + icon + '.jpg'})
            xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)
        
    xbmcplugin.endOfDirectory(_addon_handler)
    
elif mode == 'page':
    response = urllib.urlopen("https://www.telekomsport.de/api/v1" + args['page']).read()
    jsonResult = json.loads(response)

    for content in jsonResult['data']['content']:
        for group_element in content['group_elements']:
            if group_element['type'] == 'eventLane':
                url = build_url({'mode': group_element['type'], group_element['type']: group_element['data_url']})
                li = xbmcgui.ListItem(content['title'] if not group_element['title'] else content['title'] + ' - ' + group_element['title'])
                li.setArt({'fanart': jsonResult['data']['metadata']['web']['image']})
                xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)
                            
    xbmcplugin.endOfDirectory(_addon_handler)

elif mode == 'eventLane':
    response = urllib.urlopen("https://www.telekomsport.de/api/v1" + args['eventLane']).read()
    jsonResult = json.loads(response)

    for event in jsonResult['data']['data']:
        if event['target_type'] == 'event':
            url = build_url({'mode': 'event', 'event': event['target']})
            if event['metadata']['title']:
                title = event['title']
            else:
                if event['type'] == 'teamEvent' and 'details' in event['metadata'] and 'home' in event['metadata']['details']:
                    title = event['metadata']['details']['home']['name_full'] + ' - ' + event['metadata']['details']['away']['name_full']
            eventinfo = event['metadata']['description_bold'] + ' - ' + event['metadata']['description_regular']
            li = xbmcgui.ListItem('[B]' + eventinfo +  '[/B][CR]' + title, iconImage='https://www.telekomsport.de' + event['metadata']['images']['editorial'])
            li.setInfo('video', {'plot': prettydate(datetime.utcfromtimestamp(int(event['metadata']['scheduled_start']['utc_timestamp'])))})
            li.setProperty('fanart_image', 'https://www.telekomsport.de' + event['metadata']['images']['editorial'])
            xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(_addon_handler)
        

elif mode == 'event':
    response = urllib.urlopen("https://www.telekomsport.de/api/v1" + args['event']).read()
    jsonResult = json.loads(response)
    
    if jsonResult['data']['content'][0]['group_elements'][0]['type'] == 'noVideo':
        scheduled_start = datetime.utcfromtimestamp(int(jsonResult['data']['content'][0]['group_elements'][0]['data']['metadata']['scheduled_start']['utc_timestamp']))
        if jsonResult['data']['content'][0]['group_elements'][0]['data']['metadata']['state'] == 'pre' and scheduled_start > datetime.now():
            xbmcgui.Dialog().ok(_addon_name, __language__(30001), "", prettydate(scheduled_start))
        else:
            xbmcgui.Dialog().ok(_addon_name, __language__(30002))
        xbmcplugin.endOfDirectory(_addon_handler, succeeded=False)
    else:
        for content in jsonResult['data']['content']:
            if content['group_elements'][0]['type'] == 'eventVideos':
                for eventVideo in content['group_elements'][0]['data']:
                    isLivestream = 'isLivestream' in eventVideo and event['isLivestream'] == 'true'
                    url = build_url({'mode': 'video', 'videoid': eventVideo['videoID'], 'isLivestream': isLivestream})
                    li = xbmcgui.ListItem(eventVideo['title'], iconImage='https://www.telekomsport.de' + eventVideo['images']['editorial'])
                    li.setProperty('fanart_image', 'https://www.telekomsport.de' + eventVideo['images']['editorial'])
                    li.setProperty('IsPlayable', 'true')
                    xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li)

        xbmcplugin.endOfDirectory(_addon_handler)

elif mode == 'video':
    videoid = args['videoid']
    partnerid = '2780'
    unassecret = 'aXHi21able'
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    ident = str(randint(10000000, 99999999)) + str(int(time.time()))
    streamtype = 'live' if args['isLivestream'] == 'true' else 'vod'

    auth = md5.new(videoid + partnerid + timestamp + unassecret).hexdigest()

    url = 'https://streamaccess.unas.tv/hdflash2/' + streamtype + '/' + partnerid + '/' + videoid + '.xml?format=iphone&streamid=' + videoid + '&partnerid=' + partnerid + '&ident=' + ident + '&timestamp=' + timestamp + '&auth=' + auth

    response = urllib.urlopen(url).read()
    
    xmlroot = ET.ElementTree(ET.fromstring(response))
    playlisturl = xmlroot.find('token').get('url')
    auth = xmlroot.find('token').get('auth')
    
    listitem = xbmcgui.ListItem(path=playlisturl + "?hdnea=" + auth)
    xbmcplugin.setResolvedUrl(_addon_handler, True, listitem)
