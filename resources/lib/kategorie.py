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

__id__       = 'plugin.audio.open_FM';
__settings__ = xbmcaddon.Addon(id=__id__)
__datapath__ = xbmc.translatePath('special://profile/addon_data/%s' % (__id__))

cached_json   = os.path.join(__datapath__, 'stations.json')
with open(cached_json, 'r') as data_file:    
	json_data = json.load(data_file)
# print json_data

#
# Main class
#
class Main:
	def __init__(self):
        # Categories...
		for kategoria in json_data['groups']:
			li  = xbmcgui.ListItem( kategoria['name'])
			url = '%s?stacje=%s' % (sys.argv[0], kategoria['id'])
			xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, li, True)

        # Disable sorting...
		xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_NONE )
		
        # End of list...
		xbmcplugin.endOfDirectory( handle=int( sys.argv[ 1 ] ), succeeded=True )
