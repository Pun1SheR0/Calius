#!/usr/bin/env python3
"""
Actualiza data.json con los resultados nuevos de EA SPORTS FC.

Lo ejecuta GitHub Actions cada noche. No hay que tocarlo a mano.

Las webs suelen rechazar peticiones desde servidores (error 403). Por eso se
intentan varias vias en orden: primero directa con cabeceras de navegador
real, y si no, a traves de intermediarios publicos. Basta con que una
funcione.

Si ninguna via devuelve partidos, termina con error para que el workflow
salga en rojo y GitHub avise por correo.

Fuente: EGamersWorld - https://egamersworld.com
"""

from __future__ import annotations

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
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://egamersworld.com/fifa",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
}

VIAS = [
    ("directa",    lambda u: u),
    ("r.jina.ai",  lambda u: "https://r.jina.ai/" + u),
    ("allorigins", lambda u: "https://api.allorigins.win/raw?url="
                             + urllib.parse.quote(u, safe="")),
