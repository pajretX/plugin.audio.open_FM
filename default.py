#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import xbmcaddon
import urllib2
import time


# intro
__plugin__   = "Open FM"
__author__   = "pajretX"
__date__     = "21.01.2017"
__version__  = "2.0.1"
__id__       = 'plugin.audio.open_FM'
__settings__ = xbmcaddon.Addon(id=__id__)
__datapath__ = xbmc.translatePath('special://profile/addon_data/%s' % (__id__))

# Libraries (internal)
lib_dir = xbmc.translatePath(os.path.join( __settings__.getAddonInfo('path'), 'resources', 'lib'))
sys.path.append (lib_dir)
from utils import HTTPCommunicator

# Check cached JSON data...
if not os.path.exists(__datapath__) :
	os.makedirs(__datapath__)

cached_json = os.path.join(__datapath__, 'stations.json')
if not os.path.exists(cached_json) or time.time() - os.path.getmtime(cached_json) > 60 * 60 :		# no cached JSON file or 1h stale
	# dane
	url=[
		'http://open.fm/',
		'http://open.fm/js/openfm2-min.js',
		'http://open.fm/api/static/stations/stations_new.json']
	
	# log mark
	# print HTTPCommunicator().get(url[0]);
	# print HTTPCommunicator().get(url[1]);

	# Download and store...
	contents = HTTPCommunicator().get(url[2]);
	file = open(cached_json, 'w')
	file.write(contents)
	file.close()

if ( "stacje" in sys.argv[ 2 ] ):
	import stacje as plugin

else :
	import kategorie as plugin

plugin.Main()
