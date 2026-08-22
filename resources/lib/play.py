#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Odtwarzanie stacji (Open FM) — Kodi 19+, Python 3

import sys
import traceback

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

__id__ = 'plugin.audio.open_FM'
__addon__ = xbmcaddon.Addon(id=__id__)
sys.path.insert(0, __addon__.getAddonInfo('path') + '/resources/lib')

import default as ofm  # noqa: E402


class Main:
    def __init__(self):
        handle = int(sys.argv[1])
        try:
            sid = sys.argv[2].split('play=')[1].split('&')[0]
            stations = ofm.get_stations()
            st = stations.get(str(sid))
            if not st:
                raise Exception('station %s not found' % sid)

            url = ofm.resolve_stream_url(st['streamUrl'])
            xbmc.log('[%s] resolved (%d chars): %s...' % (__id__, len(url), url[:60]),
                     level=xbmc.LOGINFO)

            li = xbmcgui.ListItem(label=st['name'], path=url)
            li.setArt({'thumb': st.get('logoUrl', ''),
                       'icon': 'DefaultMusicSongs.png'})
            li.setProperty('IsPlayable', 'true')
            li.setProperty('mimetype', 'application/x-mpegurl')
            li.setInfo('music', {'title': st['name']})
            xbmcplugin.setResolvedUrl(handle, succeeded=True, listitem=li)
            xbmc.log('[%s] setResolvedUrl OK' % __id__, level=xbmc.LOGINFO)

            # Fallback: wymuś start odtwarzania bezpośrednio (setResolvedUrl bywa
            # ignorowany przez PlaylistPlayer dla audio-only HLS)
            _p = xbmc.Player()
            _p.play(url, li)
        except Exception:
            xbmc.log('[%s] play ERROR: %s' % (__id__, traceback.format_exc()),
                     level=xbmc.LOGERROR)
            xbmcplugin.setResolvedUrl(handle, succeeded=False,
                                      listitem=xbmcgui.ListItem())
