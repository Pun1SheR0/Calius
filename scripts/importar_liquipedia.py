#!/usr/bin/env python3
"""
Importa el historico de partidos de EA SPORTS FC desde Liquipedia.

Es un trabajo de UNA SOLA VEZ (backfill), no la actualizacion nocturna.
Recorre solo los torneos de la temporada actual (FC 26), lee el texto
fuente de cada uno por la API oficial del wiki, y extrae los partidos
de las plantillas {{Match|...}}. Solo se guardan partidos de los
ultimos N meses (4 por defecto).

Uso:
    python importar_liquipedia.py --limit 15          # prueba
    python importar_liquipedia.py --debug-pagina "FC_Pro_26/World_Championship"
    python importar_liquipedia.py                      # barrido completo
    python importar_liquipedia.py --meses 3            # ultimos 3 meses
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

import requests

WIKI = "easportsfc"
API = f"https://liquipedia.net/{WIKI}/api.php"

# Solo torneos de la version actual del juego (FC 26). Mucho mas acotado
# que "Finished Tournaments" (1.578 paginas desde 2011): esta categoria
# la llevan todos los torneos de esta temporada, confirmado en varias
# paginas reales (eSerie_A/2026, eLPF/2026, EChampions_League/2026).
CATEGORIA = "Category:EA SPORTS FC 26 Competitions"

# Liquipedia exige un User-Agent identificable con URL de contacto.
UA = "CaliusMarcador/1.0 (+https://github.com/Pun1SheR0/Calius)"
PAUSA = 2.1  # 1 peticion cada 2s como minimo; margen extra por seguridad

SALIDA = os.environ.get("SALIDA", "data.json")
PROGRESO = os.environ.get("PROGRESO", "liq_progreso.json")


class LiquipediaAPI:
    def __init__(self):
        self.sesion = requests.Session()
        self.sesion.headers.update({
            "User-Agent": UA,
            "Accept-Encoding": "gzip",
        })
        self._ultima = 0.0

    def _esperar(self):
        transcurrido = time.time() - self._ultima
        if transcurrido < PAUSA:
            time.sleep(PAUSA - transcurrido)
        self._ultima = time.time()

    def get(self, **params) -> dict:
        """Si Liquipedia responde 429 (limite de peticiones), no es
        necesariamente por nosotros: los runners de GitHub Actions
        comparten IP con miles de proyectos ajenos. Se espera y se
        reintenta en vez de rendirse al primer golpe."""
        params["format"] = "json"
        for intento in range(4):
            self._esperar()
            r = self.sesion.get(API, params=params, timeout=30)
            if r.status_code == 429:
                espera = int(r.headers.get("Retry-After", 30 * (intento + 1)))
                print(f"[aviso] 429 de Liquipedia, esperando {espera}s (intento {intento + 1}/4)",
                      file=sys.stderr)
                time.sleep(espera)
                continue
            r.raise_for_status()
            return r.json()
        r.raise_for_status()
        return r.json()

    def listar_torneos(self, limite: int | None = None) -> list[str]:
        titulos: list[str] = []
        cmcontinue = None
        while True:
            params = {
                "action": "query", "list": "categorymembers",
                "cmtitle": CATEGORIA, "cmlimit": "500", "cmtype": "page",
            }
            if cmcontinue:
                params["cmcontinue"] = cmcontinue
            data = self.get(**params)
            miembros = data.get("query", {}).get("categorymembers", [])
            titulos.extend(m["title"] for m in miembros)
            print(f"[categoria] {len(titulos)} torneos listados...", file=sys.stderr)

            if limite and len(titulos) >= limite:
                return titulos[:limite]

            cmcontinue = data.get("continue", {}).get("cmcontinue")
            if not cmcontinue:
                return titulos

    def wikitext(self, titulo: str) -> str | None:
        data = self.get(
            action="query", prop="revisions", titles=titulo,
            rvslots="main", rvprop="content",
        )
        paginas = data.get("query", {}).get("pages", {})
        for p in paginas.values():
            if "missing" in p:
                return None
            revs = p.get("revisions")
            if not revs:
                return None
            return revs[0]["slots"]["main"]["*"]
        return None


RE_OPONENTE = re.compile(r'opponent(\d)\s*=\s*\{\{\s*\w*Opponent\s*\|(.*?)\}\}', re.S)
RE_FECHA = re.compile(r'([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})')


def encontrar_bloques_match(texto: str) -> list[str]:
    bloques = []
    for m in re.finditer(r'\{\{\s*Match\s*[\|\n]', texto):
        inicio = m.start()
        profundidad = 0
        i = m.start()
        while i < len(texto) - 1:
            if texto[i:i + 2] == '{{':
                profundidad += 1
                i += 2
                continue
            if texto[i:i + 2] == '}}':
                profundidad -= 1
                i += 2
                if profundidad == 0:
                    bloques.append(texto[inicio:i])
                    break
                continue
            i += 1
    return bloques


def parsear_oponente(bloque_interno: str) -> tuple[str, str | None]:
    partes = bloque_interno.split('|')
    nombre = partes[0].strip() if partes else ''
    score = None
    for p in partes[1:]:
        p = p.strip()
        if p.startswith('score='):
            score = p[len('score='):].strip()
    return nombre, score


def dentro_de_ventana(fecha_iso: str, cutoff_iso: str) -> bool:
    """Compara fechas ISO como texto: funciona porque YYYY-MM-DD ordena
    igual como cadena que como fecha. Sin fecha -> se descarta: mejor
    perder algun partido raro que colar algo de fuera de temporada."""
    return bool(fecha_iso) and fecha_iso >= cutoff_iso


def parsear_match(bloque: str, torneo: str, cutoff_iso: str) -> dict | None:
    opos = {}
    for idx, interno in RE_OPONENTE.findall(bloque):
        opos[idx] = parsear_oponente(interno)

    if '1' not in opos or '2' not in opos:
        return None
    n1, s1 = opos['1']
    n2, s2 = opos['2']
    if not n1 or not n2:
        return None

    try:
        g1, g2 = int(s1), int(s2)
    except (TypeError, ValueError):
        return None
    if g1 == g2:
        return None

    fm = RE_FECHA.search(bloque)
    date = ''
    if fm:
        mes, dia, anio = fm.groups()
        try:
            t = time.strptime(f"{mes} {dia} {anio}", "%B %d %Y")
            date = time.strftime("%Y-%m-%d", t)
        except ValueError:
            pass

    if not dentro_de_ventana(date, cutoff_iso):
        return None

    return {"a": n1, "b": n2, "ga": g1, "gb": g2, "date": date,
            "note": f"Liquipedia: {torneo}"}


def id_estable(titulo: str, indice: int, m: dict) -> str:
    """ID reproducible: mismo torneo + mismo partido -> mismo id siempre,
    para que reejecutar el importador nunca duplique."""
    import hashlib
    base = f"{titulo}#{indice}#{m['a']}#{m['b']}#{m['ga']}#{m['gb']}"
    return "liq-" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


def cargar_progreso() -> set[str]:
    try:
        with open(PROGRESO, encoding="utf-8") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def guardar_progreso(hechos: set[str]) -> None:
    with open(PROGRESO, "w", encoding="utf-8") as f:
        json.dump(sorted(hechos), f)


def cargar_data() -> dict:
    try:
        with open(SALIDA, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"matches": []}


def guardar_data(datos: dict) -> None:
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                     help="probar solo con N torneos (recomendado: 15 la primera vez)")
    ap.add_argument("--debug-pagina", type=str, default=None,
                     help="vuelca el wikitext crudo de una pagina y sale, sin procesar nada mas")
    ap.add_argument("--meses", type=int, default=4,
                     help="solo partidos de los ultimos N meses (por defecto 4)")
    args = ap.parse_args()

    cutoff = time.strftime("%Y-%m-%d", time.gmtime(time.time() - args.meses * 30 * 86400))
    print(f"[info] solo se guardan partidos desde {cutoff} en adelante", file=sys.stderr)

    api = LiquipediaAPI()

    if args.debug_pagina:
        wt = api.wikitext(args.debug_pagina)
        if wt is None:
            print(f"[debug] pagina no encontrada: {args.debug_pagina}", file=sys.stderr)
            return 1
        print(wt[:6000])
        return 0

    print("[info] listando torneos terminados...", file=sys.stderr)
    titulos = api.listar_torneos(limite=args.limit)
    print(f"[info] {len(titulos)} torneos a procesar", file=sys.stderr)

    hechos = cargar_progreso()
    pendientes = [t for t in titulos if t not in hechos]
    if len(pendientes) < len(titulos):
        print(f"[info] reanudando: {len(titulos) - len(pendientes)} ya procesados antes",
              file=sys.stderr)

    datos = cargar_data()
    conocidos = {m.get("id") for m in datos.get("matches", [])}

    total_nuevos = 0
    sin_match = 0
    con_error = 0

    for n, titulo in enumerate(pendientes, 1):
        try:
            wt = api.wikitext(titulo)
        except requests.RequestException as e:
            print(f"[aviso] {titulo}: {type(e).__name__}, se reintentara en la proxima ejecucion",
                  file=sys.stderr)
            con_error += 1
            continue

        if wt is None:
            hechos.add(titulo)
            continue

        bloques = encontrar_bloques_match(wt)
        if not bloques:
            sin_match += 1

        nuevos_aqui = 0
        for i, bloque in enumerate(bloques):
            m = parsear_match(bloque, titulo, cutoff)
            if not m:
                continue
            mid = id_estable(titulo, i, m)
            if mid in conocidos:
                continue
            datos.setdefault("matches", []).append({"id": mid, **m})
            conocidos.add(mid)
            nuevos_aqui += 1
            total_nuevos += 1

        hechos.add(titulo)

        print(f"[{n}/{len(pendientes)}] {titulo}: {len(bloques)} bloques, "
              f"+{nuevos_aqui} nuevos", file=sys.stderr)
        if n % 20 == 0:
            guardar_progreso(hechos)
            guardar_data(datos)

    guardar_progreso(hechos)
    datos["actualizado"] = time.strftime("%Y-%m-%d %H:%M UTC")
    guardar_data(datos)

    print(f"\n[resumen] torneos procesados: {len(pendientes)}", file=sys.stderr)
    print(f"[resumen] partidos nuevos importados: {total_nuevos}", file=sys.stderr)
    print(f"[resumen] total en data.json: {len(datos.get('matches', []))}", file=sys.stderr)
    print(f"[resumen] torneos sin ningun Match reconocido: {sin_match}", file=sys.stderr)
    print(f"[resumen] torneos con error de red (reintentar): {con_error}", file=sys.stderr)

    if sin_match > len(pendientes) * 0.5 and len(pendientes) > 5:
        print("\n[AVISO] mas de la mitad de los torneos no dieron ningun partido.",
              file=sys.stderr)
        print("Antes de lanzar el barrido completo, usa --debug-pagina con uno de",
              file=sys.stderr)
        print("esos torneos para ver si el formato real difiere del esperado.",
              file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
