#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Open FM for Kodi 19+ (Matrix / Nexus / Omega), Python 3
#
# Funkcje API i pomocnicze:
# - Pobieranie stacji z oficjalnego API Open FM wraz ze stacjami komercyjnymi (standalone)
# - Podpisywanie tokenem strumieni HLS (open.fm CDN)
# - Bezpośrednie strumienie AAC (StreamTheWorld) dla stacji komercyjnych
# - Pobieranie pełnych list stacji dla kategorii (brak ucinania do 10 stacji z karuzeli)

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

import xbmcaddon
import xbmcvfs

__id__ = 'plugin.audio.open_FM'
__addon__ = xbmcaddon.Addon(id=__id__)
__datapath__ = xbmcvfs.translatePath('special://profile/addon_data/%s' % __id__)

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'

API_STATIONS = 'https://open.fm/api/radio/stations'
API_STANDALONE = 'https://open.fm/api/radio/standalone-stations'
API_CATEGORIES = 'https://open.fm/api/radio/categories'
API_CATEGORY = 'https://open.fm/api/radio/category/'
TOKEN_URL = 'https://open.fm/api/user/token?fp='


def http_get(url, timeout=15):
    req = urllib.request.Request(url, headers={
        'Accept': '*/*',
        'User-Agent': USER_AGENT,
    })
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return f.read().decode('utf-8', 'replace')


def get_json_cached(url, cache_file, ttl_seconds=3600):
    """Pobierz JSON z cache na dysku (TTL domyślnie 1h)."""
    if os.path.exists(cache_file):
        try:
            if time.time() - os.path.getmtime(cache_file) < ttl_seconds:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
    data = http_get(url)
    try:
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(data)
    except Exception:
        pass
    return json.loads(data)


def get_stations():
    """Zwraca słownik wszystkich stacji Open FM z uwzględnieniem
    stacji komercyjnych (standalone: Radio ZET, Antyradio itp.)."""
    os.makedirs(__datapath__, exist_ok=True)
    cache = os.path.join(__datapath__, 'stations.json')
    if os.path.exists(cache) and (time.time() - os.path.getmtime(cache) < 3600):
        try:
            with open(cache, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    try:
        stations = json.loads(http_get(API_STATIONS))
    except Exception:
        stations = {}

    try:
        standalone = json.loads(http_get(API_STANDALONE))
        for item in standalone:
            sid = str(item.get('id'))
            if sid in stations:
                stations[sid]['streamUrl'] = item.get('streamUrl')
                stations[sid]['urlType'] = item.get('urlType', 'aac')
                stations[sid]['standalone'] = True
    except Exception:
        pass

    if stations:
        try:
            with open(cache, 'w', encoding='utf-8') as f:
                json.dump(stations, f)
        except Exception:
            pass

    return stations


def get_categories():
    """Zwraca listę kategorii z API Open FM (z usuniętymi emoji)."""
    os.makedirs(__datapath__, exist_ok=True)
    cache = os.path.join(__datapath__, 'categories.json')
    if os.path.exists(cache) and (time.time() - os.path.getmtime(cache) < 86400):
        try:
            with open(cache, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    cats = []
    try:
        raw = json.loads(http_get(API_CATEGORIES))
        for c in raw:
            # usuń emoji z nazw (Kodi nie renderuje ich poprawnie w wielu skórkach)
            clean = re.sub(
                r'[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF'
                r'\u2300-\u23FF\u25A0-\u25FF\u2B00-\u2BFF\u2900-\u297F\uFE0F\u200D]+',
                '', c.get('name', '')).strip()
            cats.append({
                'id': c.get('id'),
                'name': clean or c.get('slug', ''),
                'slug': c.get('slug', '')
            })
    except Exception:
        pass

    if cats:
        try:
            with open(cache, 'w', encoding='utf-8') as f:
                json.dump(cats, f)
        except Exception:
            pass

    return cats


def get_category_stations(slug):
    """Pobiera pełną listę identyfikatorów stacji dla danej kategorii z API."""
    cache_dir = os.path.join(__datapath__, 'categories')
    os.makedirs(cache_dir, exist_ok=True)
    cache = os.path.join(cache_dir, '%s.json' % slug)
    if os.path.exists(cache) and (time.time() - os.path.getmtime(cache) < 86400):
        try:
            with open(cache, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    items = []
    try:
        data = json.loads(http_get(API_CATEGORY + urllib.parse.quote(slug)))
        items = data.get('items', [])
    except Exception:
        pass

    if items:
        try:
            with open(cache, 'w', encoding='utf-8') as f:
                json.dump(items, f)
        except Exception:
            pass

    return items


def resolve_stream_url(station):
    """Zwraca gotowy URL strumienia do odtworzenia.
    - Dla stacji komercyjnych (standalone AAC / StreamTheWorld) zwraca bezpośredni URL.
    - Dla stacji standardowych HLS pobiera podpisany token z API open.fm."""
    stream_url = station.get('streamUrl', '')
    if station.get('standalone') or station.get('urlType') == 'aac' or 'streamtheworld.com' in stream_url:
        return stream_url

    try:
        signed = http_get(TOKEN_URL + urllib.parse.quote(stream_url, safe=''))
        url = json.loads(signed).get('url')
        if url:
            return url
    except Exception:
        pass
    return stream_url


if __name__ == '__main__':
    base_path = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(base_path, 'resources', 'lib'))

    argv2 = sys.argv[2] if len(sys.argv) > 2 else ''
    if 'play=' in argv2:
        import play as plugin
    elif 'stacje=' in argv2:
        import stacje as plugin
    else:
        import kategorie as plugin
    plugin.Main()
