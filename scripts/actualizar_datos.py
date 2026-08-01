#!/usr/bin/env python3
"""
Actualiza data.json con los resultados nuevos de EA SPORTS FC.

Lo ejecuta GitHub Actions cada noche. No hay que tocarlo a mano.

Decisión de diseño importante: si no reconoce NINGÚN partido, termina con
error. Así el workflow sale en rojo y GitHub avisa por correo. Un scraper que
falla en silencio es peor que uno que no existe, porque la app sigue
mostrando datos viejos como si fueran de hoy.

Fuente: EGamersWorld — https://egamersworld.com
"""

from __future__ import annotations

import json
import os
import re
import sys
import time

import requests

BASE = "https://egamersworld.com/fifa/matches/history"
SALIDA = os.environ.get("SALIDA", "data.json")
PAGINAS = int(os.environ.get("PAGINAS", "6"))
UA = "MarcadorBot/1.0 (+https://github.com)"
PAUSA = 2.5

RE_LINK = re.compile(
    r'/fifa/match/[A-Za-z0-9_-]+/([a-z0-9][a-z0-9-]*?)-vs-([a-z0-9][a-z0-9-]*?)-([A-Za-z0-9_-]{7,})'
)
_T = r'(?:<[^>]*>\s*)*'
RE_GOLES = re.compile(r'Bo\d\s*' + _T + r'(\d{1,2})\s*' + _T + r':\s*' + _T + r'(\d{1,2})')
RE_FECHA = re.compile(r'(\d{2})\.(\d{2})\.(\d{2})')
VENTANA = 4000


def bonito(slug: str) -> str:
    return " ".join(p[:1].upper() + p[1:] for p in slug.split("-") if p)


def extraer(texto: str) -> list[dict]:
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
            date = f"20{y}-{mo}-{d}"

        filas.append({"id": mid, "date": date, "a": bonito(a_slug),
                      "b": bonito(b_slug), "ga": ga, "gb": gb, "note": "EGW"})
    return filas


def main() -> int:
    sesion = requests.Session()
    sesion.headers.update({"User-Agent": UA, "Accept-Language": "es,en"})

    encontrados: list[dict] = []
    for pagina in range(1, PAGINAS + 1):
        url = BASE if pagina == 1 else f"{BASE}?page={pagina}"
        try:
            r = sesion.get(url, timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"[aviso] página {pagina}: {e}", file=sys.stderr)
            break

        filas = extraer(r.text)
        print(f"[info] página {pagina}: {len(filas)} partidos", file=sys.stderr)
        if not filas:
            break
        encontrados.extend(filas)
        time.sleep(PAUSA)

    if not encontrados:
        print("[ERROR] No se ha reconocido ningún partido. La web de origen "
              "probablemente ha cambiado y hay que revisar los patrones.",
              file=sys.stderr)
        return 1

    # Fusionar con lo que ya había, sin perder nada ni duplicar
    try:
        with open(SALIDA, encoding="utf-8") as f:
            datos = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        datos = {"matches": []}

    previos = datos.get("matches", [])
    conocidos = {m.get("id") for m in previos}

    nuevos = [f for f in encontrados if f["id"] not in conocidos]
    # dedupe dentro de la propia tanda
    vistos, limpios = set(), []
    for f in nuevos:
        if f["id"] in vistos:
            continue
        vistos.add(f["id"])
        limpios.append(f)

    datos["matches"] = previos + limpios
    datos["actualizado"] = time.strftime("%Y-%m-%d %H:%M UTC")
    datos["fuente"] = "EGamersWorld — https://egamersworld.com"

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)

    print(f"[ok] {len(limpios)} partidos nuevos. Total: {len(datos['matches'])}.",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
