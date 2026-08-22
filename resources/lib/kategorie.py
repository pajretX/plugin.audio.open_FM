#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Lista kategorii (Open FM) — Kodi 19+, Python 3

import sys
import urllib.parse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

import default as ofm  # wspólne funkcje (cache, pobieranie)

__id__ = 'plugin.audio.open_FM'

json_data_stations = ofm.get_stations()
categories = ofm.get_categories_from_page()


class Main:
    def __init__(self):
        handle = int(sys.argv[1])
        for kat in categories:
            li = xbmcgui.ListItem(label=kat['name'])
            li.setArt({'thumb': '', 'icon': 'DefaultFolder.png'})
            url = '%s?stacje=%s' % (sys.argv[0], urllib.parse.quote(str(kat['id'])))
            xbmcplugin.addDirectoryItem(handle, url, li, isFolder=True)

        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(handle, succeeded=True)
