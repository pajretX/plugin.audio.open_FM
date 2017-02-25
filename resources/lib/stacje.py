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

#
__id__       = 'plugin.audio.open_FM';
__settings__ = xbmcaddon.Addon(id=__id__)
__datapath__ = xbmc.translatePath('special://profile/addon_data/%s' % (__id__))

# 
cached_json   = os.path.join(__datapath__, 'stations.json')
with open(cached_json, 'r') as data_file:    
	json_data = json.load(data_file)
# print json_data


class Main: 
	def __init__( self ) :
		# Stations (for category)...
		ID_kat = sys.argv[2].split('=')[1]
		for kanal in json_data['channels'] :
			if kanal['group_id'] == ID_kat :
				# print kanal['logo']['url']
				li  = xbmcgui.ListItem(kanal['name'], iconImage='DefaultMusicSongs.png', thumbnailImage=kanal['logo']['url'])
				url = 'http://stream.open.fm/%s' % ( kanal['id'] )
				xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, li, isFolder=False)

        # Disable sorting...
		xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_NONE )
		
        # End of list...
		xbmcplugin.endOfDirectory( handle=int( sys.argv[ 1 ] ), succeeded=True )	
