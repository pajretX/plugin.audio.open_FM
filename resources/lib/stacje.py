#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Lista stacji w kategorii (Open FM) — Kodi 19+, Python 3

import sys
import urllib.parse

import xbmcaddon
import xbmcgui
import xbmcplugin

import default as ofm

__id__ = 'plugin.audio.open_FM'

stations_by_id = ofm.get_stations()
categories = {str(c['id']): c for c in ofm.get_categories_from_page()}


class Main:
    def __init__(self):
        handle = int(sys.argv[1])
        kat_id = urllib.parse.unquote(sys.argv[2].split('stacje=')[1].split('&')[0])
        kat = categories.get(kat_id)
        items = []
        if kat:
            for sid in kat['stations']:
                st = stations_by_id.get(str(sid))
                if not st:
                    continue
                items.append(st)

        for st in items:
            li = xbmcgui.ListItem(label=st['name'])
            li.setArt({'thumb': st.get('logoUrl', ''), 'icon': 'DefaultMusicSongs.png'})
            url = '%s?play=%s' % (sys.argv[0], str(st['id']))
            xbmcplugin.addDirectoryItem(handle, url, li, isFolder=False)

        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(handle, succeeded=True)
