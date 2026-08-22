#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Open FM for Kodi 19+ (Matrix / Omega), Python 3
#
# Kluczowa zmiana względem starej wersji:
# strumienie open.fm wymagają podpisanego tokenu. Token pobiera się z:
#   https://open.fm/api/user/token?fp=<streamUrl>
# a zwracany URL (z parametrem ?t=...) jest jednorazowy/krótkotrwały.

import json
import os
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
API_CATEGORIES = 'https://open.fm/_next/data'          # nieużywane bezpośrednio
PAGE_URL = 'https://open.fm/'
TOKEN_URL = 'https://open.fm/api/user/token?fp='


def http_get(url):
    req = urllib.request.Request(url, headers={
        'Accept': '*/*',
        'User-Agent': USER_AGENT,
    })
    with urllib.request.urlopen(req, timeout=15) as f:
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
    with open(cache_file, 'w', encoding='utf-8') as f:
        f.write(data)
    return json.loads(data)


def get_stations():
    os.makedirs(__datapath__, exist_ok=True)
    cache = os.path.join(__datapath__, 'stations.json')
    # API zwraca słownik {id: station}; sortujemy po nazwie przy wyświetlaniu
    return get_json_cached(API_STATIONS, cache)


def get_categories_from_page():
    """Kategorie są osadzone w __NEXT_DATA__ na stronie głównej."""
    import re
    cache = os.path.join(__datapath__, 'categories.json')
    if os.path.exists(cache) and time.time() - os.path.getmtime(cache) < 3600:
        with open(cache, 'r', encoding='utf-8') as f:
            return json.load(f)
    html = http_get(PAGE_URL)
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>',
        html, re.S)
    cats = []
    if m:
        d = json.loads(m.group(1))
        raw = d['props']['pageProps']['fallback']['categories']
        for c in raw:
            # usuń emoji z nazw (Kodi nie renderuje ich — pojawiają się jako prostokąty)
            clean = re.sub(
                r'[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF'
                r'\u2300-\u23FF\u25A0-\u25FF\u2B00-\u2BFF\u2900-\u297F\uFE0F\u200D]+',
                '', c['name']).strip()
            cats.append({'id': c['id'], 'name': clean, 'slug': c['slug'],
                         'stations': c['stations']})
    with open(cache, 'w', encoding='utf-8') as f:
        json.dump(cats, f)
    return cats


def resolve_stream_url(stream_url):
    """Podpisz URL streamu tokenem z API open.fm. Zwraca gotowy URL do odtwarzania."""
    try:
        signed = http_get(TOKEN_URL + urllib.parse.quote(stream_url, safe=''))
        url = json.loads(signed).get('url')
        if url:
            return url
    except Exception:
        pass
    return stream_url  # fallback — może zadziała w niektórych sieciach


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
