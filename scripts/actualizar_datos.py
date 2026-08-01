#!/usr/bin/env python3
import json
import os
import re
import sys
import time
import urllib.parse

import requests

ORIGEN = "https://egamersworld.com/fifa/matches/history"
SALIDA = os.environ.get("SALIDA", "data.json")
PAGINAS = int(os.environ.get("PAGINAS", "5"))
PAUSA = 3.0

CABECERAS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://egamersworld.com/fifa",
    "Upgrade-Insecure-Requests": "1",
}

def _v_directa(u):
    return u

def _v_jina(u):
    return "https://r.jina.ai/" + u

def _v_allorigins(u):
    return "https://api.allorigins.win/raw?url=" + urllib.parse.quote(u, safe="")

def _v_codetabs(u):
    return "https://api.codetabs.com/v1/proxy?quest=" + urllib.parse.quote(u, safe="")

VIAS = [("directa", _v_directa), ("r.jina.ai", _v_jina), ("allorigins", _v_allorigins), ("codetabs", _v_codetabs)]

RE_LINK = re.compile(r'/fifa/match/[A-Za-z0-9_-]+/([a-z0-9][a-z0-9-]*?)-vs-([a-z0-9][a-z0-9-]*?)-([A-Za-z0-9_-]{7,})')
_T = r'(?:<[^>]*>\s*)*'
RE_GOLES = re.compile(r'Bo\d\s*' + _T + r'(\d{1,2})\s*' + _T + r':\s*' + _T + r'(\d{1,2})')
RE_FECHA = re.compile(r'(\d{2})\.(\d{2})\.(\d{2})')
VENTANA = 4000

def bonito(slug):
    return " ".join(p[:1].upper() + p[1:] for p in slug.split("-") if p)

def extraer(texto):
    filas = []
    for m in RE_LINK.finditer(texto):
        a_slug, b_slug, mid = m.groups()
        ventana = texto[max(0, m.start() - VENTANA):m.start()]
        goles = RE_GOLES.findall(ventana)
        if not goles:
            continue
        ga, gb = int(goles[-1][0]), int(goles
