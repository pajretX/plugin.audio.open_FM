#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Lista stacji w kategorii (Open FM) — Kodi 19+, Python 3

import sys
import urllib.parse

import xbmcgui
import xbmcplugin

import default as ofm


class Main:
    def __init__(self):
        handle = int(sys.argv[1])
        base_url = sys.argv[0]
        params = dict(urllib.parse.parse_qsl(sys.argv[2].lstrip('?')))
        kat_id = params.get('stacje', '')
        slug = params.get('slug', '')

        stations_by_id = ofm.get_stations()
        items = []

        if kat_id == 'all':
            items = sorted(stations_by_id.values(), key=lambda s: s.get('name', '').lower())
        elif slug:
            station_ids = ofm.get_category_stations(slug)
            for sid in station_ids:
                st = stations_by_id.get(str(sid))
                if st:
                    items.append(st)
        else:
            # Fallback dla bezpośredniego id kategorii
            categories = {str(c['id']): c for c in ofm.get_categories()}
            kat = categories.get(kat_id)
            if kat and kat.get('slug'):
                station_ids = ofm.get_category_stations(kat['slug'])
                for sid in station_ids:
                    st = stations_by_id.get(str(sid))
                    if st:
                        items.append(st)

        for st in items:
            name = st.get('name', '')
            if st.get('premium'):
                name += ' [Premium]'

            logo = st.get('logoUrl', '')
            li = xbmcgui.ListItem(label=name)
            li.setArt({
                'thumb': logo,
                'icon': logo or 'DefaultMusicSongs.png',
                'fanart': logo,
                'poster': logo,
            })
            li.setProperty('IsPlayable', 'true')

            # Wsparcie nowoczesnego API Kodi 20+ (MusicInfoTag) oraz Kodi 19 (setInfo)
            if hasattr(li, 'getMusicInfoTag'):
                tag = li.getMusicInfoTag()
                tag.setTitle(name)
                tag.setArtist('Open FM')
            else:
                li.setInfo('music', {'title': name, 'artist': 'Open FM'})

            url = '%s?play=%s' % (base_url, str(st['id']))
            xbmcplugin.addDirectoryItem(handle, url, li, isFolder=False)

        xbmcplugin.setContent(handle, 'songs')
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(handle, succeeded=True)
