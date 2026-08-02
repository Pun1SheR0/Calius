#!/usr/bin/env python3
"""
Actualiza data.json con los resultados nuevos de EA SPORTS FC.

Lo ejecuta GitHub Actions cada noche. No hay que tocarlo a mano.

IMPORTANTE: EGamersWorld no pagina por URL (?page=2 devuelve la misma
pagina que ?page=1, confirmado). Este script solo pide la primera pagina:
son los partidos mas recientes, unos 20 por ejecucion. Es la pieza que
mantiene la app al dia, no la que aporta volumen historico -- eso lo hace
un importador aparte contra Liquipedia.

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

CABECERAS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
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


VIAS = [("directa", _v_directa), ("r.jina.ai", _v_jina),
        ("allorigins", _v_allorigins), ("codetabs", _v_codetabs)]

RE_LINK = re.compile(
    r'/fifa/match/[A-Za-z0-9_-]+/([a-z0-9][a-z0-9-]*?)-vs-([a-z0-9][a-z0-9-]*?)-([A-Za-z0-9_-]{7,})'
)
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
        ga, gb = int(goles[-1][0]), int(goles[-1][1])
        if ga == gb:
            continue
        fechas = RE_FECHA.findall(ventana)
        date = ""
        if fechas:
            d, mo, y = fechas[-1]
            date = "20" + y + "-" + mo + "-" + d
        filas.append({"id": mid, "date": date, "a": bonito(a_slug),
                      "b": bonito(b_slug), "ga": ga, "gb": gb, "note": "EGW"})
    return filas


def obtener_partidos(sesion):
    """Prueba cada via hasta que una devuelva partidos. Solo pide la
    primera pagina: paginar mas no aporta nada, esta comprobado."""
    for nombre, construir in VIAS:
        try:
            r = sesion.get(construir(ORIGEN), timeout=45)
            if r.status_code != 200:
                print("[via] " + nombre + ": HTTP " + str(r.status_code), file=sys.stderr)
                continue
            filas = extraer(r.text)
            if filas:
                print("[via] " + nombre + ": OK, " + str(len(filas)) + " partidos", file=sys.stderr)
                return nombre, filas
            print("[via] " + nombre + ": responde pero sin partidos", file=sys.stderr)
        except requests.RequestException as e:
            print("[via] " + nombre + ": " + type(e).__name__, file=sys.stderr)
        time.sleep(2)
    return None, []


def main():
    sesion = requests.Session()
    sesion.headers.update(CABECERAS)

    nombre_via, encontrados = obtener_partidos(sesion)
    if not encontrados:
        print("[ERROR] Ninguna via ha devuelto partidos.", file=sys.stderr)
        return 1

    try:
        with open(SALIDA, encoding="utf-8") as f:
            datos = json.load(f)
    except Exception:
        datos = {"matches": []}

    previos = datos.get("matches", [])
    conocidos = set(m.get("id") for m in previos)
    nuevos = [f for f in encontrados if f["id"] not in conocidos]

    datos["matches"] = previos + nuevos
    datos["actualizado"] = time.strftime("%Y-%m-%d %H:%M UTC")
    datos["via"] = nombre_via
    datos["fuente"] = "EGamersWorld - https://egamersworld.com"

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)

    print("[ok] " + str(len(nuevos)) + " partidos nuevos. Total: " + str(len(datos["matches"])),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
