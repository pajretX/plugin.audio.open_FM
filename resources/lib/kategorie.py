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
import xbmcaddon
import json, urllib2
__settings__ = xbmcaddon.Addon(id='plugin.audio.open_FM')
TMP_LOC = xbmc.translatePath( os.path.join( __settings__.getAddonInfo('path'), 'resources', 'tmp','temp_data' ) )
json_data=open(TMP_LOC).read()
#w = unicode(json_data, "utf-8")
#w.encode( "utf-8" )
dane = json.loads(json_data)
print dane
#
# Main class
#
class Main:
	def __init__(self):
        #
        # Kategorie
        #
		for kategoria in dane['groups']:
			li=xbmcgui.ListItem( kategoria['name'])
			u=sys.argv[0]+"?stacje"+"="+(kategoria['id'])
			xbmcplugin.addDirectoryItem(int(sys.argv[1]),u,li,True)

        # Disable sorting...
		xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_NONE )
		
        # End of list...
		xbmcplugin.endOfDirectory( handle=int( sys.argv[ 1 ] ), succeeded=True )
