#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import xbmcaddon
import urllib2

# intro
__plugin__  = "Open FM"
__author__  = "pajretX"
__date__    = "21.01.2017"
__version__ = "2.0.1"
__settings__ = xbmcaddon.Addon(id='plugin.audio.open_FM')

# dane
url=[
    'http://open.fm/',
    'http://open.fm/js/openfm2-min.js',
    'http://open.fm/api/static/stations/stations_new.json']
# log mark
pif = urllib2.Request(url[0])
paf = urllib2.Request(url[1])
pif.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0')
paf.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0')
respTrace1 = urllib2.urlopen(pif)
respTrace2 = urllib2.urlopen(paf)
traceMark1 = respTrace1.read()
traceMark2 = respTrace2.read()
respTrace1.close()
respTrace2.close()

del traceMark1, traceMark2

# get data
getData = urllib2.Request(url[2])
getData.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0')
response = urllib2.urlopen(getData)
urlContent = response.read()
response.close()

TMP_LOC = xbmc.translatePath( os.path.join( __settings__.getAddonInfo('path'), 'resources', 'tmp','temp_data' ) )
temp_data = open(TMP_LOC, 'w')
temp_data.write(urlContent)
temp_data.close()

LIB_DIR = xbmc.translatePath( os.path.join( __settings__.getAddonInfo('path'), 'resources', 'lib' ) )
sys.path.append (LIB_DIR)

if ( "stacje" in sys.argv[ 2 ] ):
	import stacje as plugin

else :
	import kategorie as plugin

plugin.Main()
