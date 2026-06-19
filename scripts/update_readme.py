#!/usr/bin/env python3
"""
Fetches the top 3 songs of the week from Last.fm and updates the GitHub profile README.
Run daily via GitHub Actions.
"""
import urllib.request
import urllib.parse
import json
import unicodedata
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

LASTFM_API_KEY    = "3affae9bce83cc5fd8d062d2b61e772d"
LASTFM_USER       = "joojpa"
README_FILE       = Path(__file__).parent.parent / "README.md"

MARKER_START      = "<!-- MUSIC_START -->"
MARKER_END        = "<!-- MUSIC_END -->"
LARGURA           = 67

def largura_real(s):
    total = 0
    for c in s:
        w = unicodedata.east_asian_width(c)
        total += 2 if w in ('W', 'F') else 1
    return total

def linha(texto=""):
    pad = LARGURA - largura_real(texto)
    pad = max(pad, 0)
    return f"│ {texto}{' ' * pad} │"

def buscar_top_semana():
    hoje          = datetime.now().date()
    inicio_semana = hoje - timedelta(days=7)
    inicio = int(datetime(inicio_semana.year, inicio_semana.month, inicio_semana.day, 0, 0, 0).timestamp())
    fim    = int(datetime(hoje.year, hoje.month, hoje.day, 23, 59, 59).timestamp())

    musicas  = []
    artistas = []
    page = 1

    while True:
        params = urllib.parse.urlencode({
            "method": "user.getrecenttracks",
            "user": LASTFM_USER,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            "from": inicio,
            "to": fim,
            "limit": 200,
            "page": page,
        })
        url = f"https://ws.audioscrobbler.com/2.0/?{params}"
        with urllib.request.urlopen(url) as r:
            data = json.loads(r.read())

        tracks = data.get("recenttracks", {}).get("track", [])
        if isinstance(tracks, dict):
            tracks = [tracks]
        if not tracks:
            break

        for t in tracks:
            if not isinstance(t, dict):
                continue
            if not isinstance(t.get("date"), dict):
                continue
            titulo  = t.get("name", "?")
            artista = t.get("artist", {})
            artista = artista.get("#text", "?") if isinstance(artista, dict) else str(artista)
            musicas.append(f"{titulo} — {artista}")
            artistas.append(artista)

        attr = data.get("recenttracks", {}).get("@attr", {})
        if page >= int(attr.get("totalPages", 1)):
            break
        page += 1

    top3    = Counter(musicas).most_common(3)
    top_art = Counter(artistas).most_common(1)[0][0] if artistas else None
    return top3, top_art

def buscar_imagem_artista(artista):
    try:
        params = urllib.parse.urlencode({"q": artista, "limit": 1})
        url = f"https://api.deezer.com/search/artist?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        resultados = data.get("data", [])
        if resultados:
            img = resultados[0].get("picture_xl") or resultados[0].get("picture_big")
            if img:
                return img
    except Exception as e:
        print(f"  ⚠️  Deezer failed: {e}")

    try:
        params = urllib.parse.urlencode({
            "term": artista,
            "media": "music",
            "entity": "musicArtist",
            "limit": 1,
        })
        url = f"https://itunes.apple.com/search?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        results = data.get("results", [])
        if results:
            img = results[0].get("artworkUrl100", "")
            return img.replace("100x100bb", "600x600bb") if img else None
    except Exception as e:
        print(f"  ⚠️  iTunes failed: {e}")

    return None

def truncar(texto, max_largura):
    resultado = ""
    atual = 0
    for c in texto:
        w = 2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1
        if atual + w > max_largura:
            return resultado + "..."
        resultado += c
        atual += w
    return resultado

def gerar_bloco_musica(top, artista_top, imagem_url):
    hoje   = datetime.now().strftime("%m/%d/%Y")
    medals = ["🥇", "🥈", "🥉"]
    max_musica = LARGURA - 6

    BORDA = "─" * (LARGURA + 2)
    terminal_linhas = [
        f"┌{BORDA}┐",
        linha(" $ cat now_playing.txt"),
        f"├{BORDA}┤",
        linha(),
        linha(f"   top 3 this week · updated on {hoje}"),
        linha(),
    ]

    for i, (musica, contagem) in enumerate(top):
        medal  = medals[i]
        sufixo = f" ({contagem}x)"
        texto  = f"  {medal} {truncar(musica, max_musica - len(sufixo) - 4)}{sufixo}"
        terminal_linhas.append(linha(texto))

    terminal_linhas.append(linha())
    terminal_linhas.append(f"└{BORDA}┘")
    terminal = "\n".join(terminal_linhas)

    if imagem_url:
        bloco = (
            "<table><tr><td>\n\n"
            "```\n"
            f"{terminal}\n"
            "```\n\n"
            "</td><td align='center'>\n\n"
            f"**Artist of the Week**\n\n"
            f"**{artista_top}**\n\n"
            f'<img src="{imagem_url}" width="200" style="border-radius:12px"/>\n\n'
            "</td></tr></table>"
        )
    else:
        bloco = "```\n" + terminal + "\n```"

    return bloco

def atualizar_secao(conteudo, marker_start, marker_end, bloco):
    if marker_start not in conteudo or marker_end not in conteudo:
        return conteudo, False
    antes  = conteudo.split(marker_start)[0]
    depois = conteudo.split(marker_end)[1]
    return f"{antes}{marker_start}\n{bloco}\n{marker_end}{depois}", True

def main():
    print("Fetching top 3 of the week...")
    top3, artista_top = buscar_top_semana()

    if not top3:
        print("No scrobbles found.")
        return

    print("Top 3:")
    for musica, contagem in top3:
        print(f"  {musica} ({contagem}x)")
    print(f"  Artist Of The Week: {artista_top}")

    print("Fetching artist image...")
    imagem_url = buscar_imagem_artista(artista_top)
    if imagem_url:
        print(f"  ✅ Image found: {imagem_url}")
    else:
        print("  ⚠️  Image not found, continuing without it.")

    conteudo = README_FILE.read_text(encoding="utf-8")

    conteudo, ok = atualizar_secao(conteudo, MARKER_START, MARKER_END, gerar_bloco_musica(top3, artista_top, imagem_url))
    if not ok:
        print("Music markers not found in README.")

    README_FILE.write_text(conteudo, encoding="utf-8")
    print("README updated!")

if __name__ == "__main__":
    main()
