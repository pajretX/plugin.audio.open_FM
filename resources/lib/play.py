#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Odtwarzanie stacji (Open FM) — Kodi 19+, Python 3

import sys
import traceback
import urllib.parse

import xbmc
import xbmcgui
import xbmcplugin

import default as ofm

__id__ = 'plugin.audio.open_FM'


class Main:
    def __init__(self):
        handle = int(sys.argv[1])
        try:
            params = dict(urllib.parse.parse_qsl(sys.argv[2].lstrip('?')))
            sid = params.get('play', '')
            if not sid:
                raise Exception('Brak parametru stacji do odtworzenia')

            stations = ofm.get_stations()
            st = stations.get(str(sid))
            if not st:
                raise Exception('Nie odnaleziono stacji o ID: %s' % sid)

            # Obsługa stacji Premium (brak publicznego strumienia bez konta)
            if st.get('premium'):
                xbmc.log('[%s] Stacja %s jest oznaczona jako Premium' % (__id__, sid),
                         level=xbmc.LOGWARNING)
                xbmcgui.Dialog().notification(
                    'Open FM',
                    'Stacja "%s" wymaga subskrypcji Open FM Premium' % st.get('name', ''),
                    xbmcgui.NOTIFICATION_WARNING,
                    4500
                )
                xbmcplugin.setResolvedUrl(handle, succeeded=False, listitem=xbmcgui.ListItem())
                return

            url = ofm.resolve_stream_url(st)
            xbmc.log('[%s] Playing %s (ID %s): %s' % (__id__, st.get('name'), sid, url[:80]),
                     level=xbmc.LOGINFO)

            li = xbmcgui.ListItem(label=st.get('name', ''), path=url)
            logo = st.get('logoUrl', '')
            li.setArt({
                'thumb': logo,
                'icon': logo or 'DefaultMusicSongs.png',
                'fanart': logo,
                'poster': logo
            })
            li.setProperty('IsPlayable', 'true')

            url_type = st.get('urlType', '')
            if url_type == 'aac' or 'streamtheworld.com' in url or url.endswith('.aac'):
                li.setProperty('mimetype', 'audio/aac')
            else:
                li.setProperty('mimetype', 'application/vnd.apple.mpegurl')

            if hasattr(li, 'getMusicInfoTag'):
                tag = li.getMusicInfoTag()
                tag.setTitle(st.get('name', ''))
                tag.setArtist('Open FM')
            else:
                li.setInfo('music', {'title': st.get('name', ''), 'artist': 'Open FM'})

            xbmcplugin.setResolvedUrl(handle, succeeded=True, listitem=li)

            # Bezpieczny fallback dla starszych wydań Kodi lub nietypowych konfiguracji odtwarzacza
            if not xbmc.Player().isPlaying():
                xbmc.Player().play(url, li)

        except Exception:
            xbmc.log('[%s] Błąd odtwarzania stacji: %s' % (__id__, traceback.format_exc()),
                     level=xbmc.LOGERROR)
            xbmcplugin.setResolvedUrl(handle, succeeded=False, listitem=xbmcgui.ListItem())
