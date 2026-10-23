#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Lista kategorii (Open FM) — Kodi 19+, Python 3

import sys
import urllib.parse

import xbmcgui
import xbmcplugin

import default as ofm


class Main:
    def __init__(self):
        handle = int(sys.argv[1])
        base_url = sys.argv[0]

        # 1. Pozycja specjalna: Wszystkie stacje (A-Z)
        li_all = xbmcgui.ListItem(label='[ Wszystkie stacje (A-Z) ]')
        li_all.setArt({'icon': 'DefaultMusicPlaylists.png', 'thumb': 'DefaultMusicPlaylists.png'})
        url_all = '%s?stacje=all' % base_url
        xbmcplugin.addDirectoryItem(handle, url_all, li_all, isFolder=True)

        # 2. Kategorie z API Open FM
        categories = ofm.get_categories()
        for kat in categories:
            li = xbmcgui.ListItem(label=kat['name'])
            li.setArt({'icon': 'DefaultFolder.png', 'thumb': 'DefaultFolder.png'})
            url = '%s?stacje=%s&slug=%s' % (
                base_url,
                urllib.parse.quote(str(kat['id'])),
                urllib.parse.quote(kat['slug'])
            )
            xbmcplugin.addDirectoryItem(handle, url, li, isFolder=True)

        xbmcplugin.setContent(handle, 'files')
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(handle, succeeded=True)
