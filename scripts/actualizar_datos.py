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
        ga, gb = int(goles[-1][0]), int(goles[-1][1])
        if ga == gb:
            continue
        fechas = RE_FECHA.findall(ventana)
        date = ""
        if fechas:
            d, mo, y = fechas[-1]
            date = "20" + y + "-" + mo + "-" + d
        filas.append({"id": mid, "date": date, "a": bonito(a_slug), "b": bonito(b_slug), "ga": ga, "gb": gb, "note": "EGW"})
    return filas
    def elegir_via(sesion):
    for nombre, construir in VIAS:
        try:
            r = sesion.get(construir(ORIGEN), timeout=45)
            if r.status_code != 200:
                print("[via] " + nombre + ": HTTP " + str(r.status_code), file=sys.stderr)
                continue
            filas = extraer(r.text)
            if filas:
                print("[via] " + nombre + ": OK, " + str(len(filas)) + " partidos", file=sys.stderr)
                return nombre, construir
            print("[via] " + nombre + ": responde pero sin partidos (" + str(len(r.text)) + " bytes)", file=sys.stderr)
        except requests.RequestException as e:
            print("[via] " + nombre + ": " + type(e).__name__, file=sys.stderr)
        time.sleep(2)
    return None

def main():
    sesion = requests.Session()
    sesion.headers.update(CABECERAS)

    elegida = elegir_via(sesion)
    if not elegida:
        print("[ERROR] Ninguna via ha devuelto partidos.", file=sys.stderr)
        return 1
    nombre, construir = elegida
    print("[info] usando la via " + nombre, file=sys.stderr)

    encontrados = []
    for pagina in range(1, PAGINAS + 1):
        url = ORIGEN if pagina == 1 else ORIGEN + "?page=" + str(pagina)
        try:
            r = sesion.get(construir(url), timeout=45)
            r.raise_for_status()
        except requests.RequestException as e:
            print("[aviso] pagina " + str(pagina) + ": " + str(e), file=sys.stderr)
            break
        filas = extraer(r.text)
        print("[info] pagina " + str(pagina) + ": " + str(len(filas)) + " partidos", file=sys.stderr)
        if not filas:
            break
        encontrados.extend(filas)
        time.sleep(PAUSA)

    if not encontrados:
        print("[ERROR] No se ha reconocido ningun partido.", file=sys.stderr)
        return 1

    try:
        with open(SALIDA, encoding="utf-8") as f:
            datos = json.load(f)
    except Exception:
        datos = {"matches": []}

    previos = datos.get("matches", [])
    conocidos = set(m.get("id") for m in previos)

    vistos = set()
    limpios = []
    for f in encontrados:
        if f["id"] in conocidos or f["id"] in vistos:
            continue
        vistos.add(f["id"])
        limpios.append(f)

    datos["matches"] = previos + limpios
    datos["actualizado"] = time.strftime("%Y-%m-%d %H:%M UTC")
    datos["via"] = nombre
    datos["fuente"] = "EGamersWorld - https://egamersworld.com"

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)

    print("[ok] " + str(len(limpios)) + " partidos nuevos. Total: " + str(len(datos["matches"])), file=sys.stderr)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
