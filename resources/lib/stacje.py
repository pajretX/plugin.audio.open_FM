#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Imports
#
import os 
import sys 
import xbmc 
import xbmcgui 
import xbmcplugin 
import urllib,urllib2 
import xbmcaddon
import json

# static
stream = 'http://stream.open.fm/'

__settings__ = xbmcaddon.Addon(id='plugin.audio.open_FM')
TMP_LOC = xbmc.translatePath( os.path.join( __settings__.getAddonInfo('path'), 'resources', 'tmp','temp_data' ) )
json_data=open(TMP_LOC).read()
#w = unicode(json_data, "utf-8")
#w.encode( "utf-8" )
dane = json.loads(json_data)
print dane

class Main: 
	def __init__( self ) :
		ID_kat = sys.argv[2].split('=')[1]
		for kanal in dane['channels']:
			if kanal['group_id'] == ID_kat:
				li = xbmcgui.ListItem(kanal['name'], thumbnailImage=kanal['logo']['url'])
				xbmcplugin.addDirectoryItem(int(sys.argv[1]), stream+kanal['id'], li, isFolder=False)
				
			xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_NONE)
			xbmcplugin.endOfDirectory(handle=int(sys.argv[1]), succeeded=True)				
