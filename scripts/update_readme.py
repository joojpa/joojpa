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

LASTFM_API_KEY = "3affae9bce83cc5fd8d062d2b61e772d"
LASTFM_USER    = "joojpa"
README_FILE    = Path(__file__).parent.parent / "README.md"

MARKER_START = "<!-- TERMINAL_START -->"
MARKER_END   = "<!-- TERMINAL_END -->"
LARGURA      = 69

def largura_real(s):
    total = 0
    for c in s:
        w = unicodedata.east_asian_width(c)
        total += 2 if w in ('W', 'F') else 1
    return total

def linha(texto=""):
    pad = LARGURA - largura_real(texto) - 1
    pad = max(pad, 0)
    return f"│ {texto}{' ' * pad}│"

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

def gerar_terminal(top, artista_top):
    hoje = datetime.now().strftime("%m/%d/%Y")
    medals = ["🥇", "🥈", "🥉"]
    max_musica = LARGURA - 8

    BORDA = "─" * LARGURA
    linhas = [
        f"┌{BORDA}┐",
        linha(" joojpa@github  ~  [session: active]"),
        f"├{BORDA}┤",
        linha(),
        linha(" $ whoami"),
        linha("  ┌───────────────────────────────────────────────────────────────┐"),
        linha("  │  João Alvarez · Software Engineer · Sorocaba, SP. BRASILLL     │"),
        linha("  │  Computer Engineer — Univesp · 1th semester                    │"),
        linha("  │  Cybersecurity and Sofware Development                         │"),
        linha("  └───────────────────────────────────────────────────────────────┘"),
        linha(),
        linha(" $ cat stack.conf"),
        linha(),
        linha(" [cloud]               AWS · Azure"),
        linha(" [containers]          Docker"),
        linha(" [backend]             Node.js · SpringBoot · Python"),
        linha(" [frontend]            React · Next.js · TailwindCSS"),
        linha(" [database]            PostgreSQL · MySQL · MongoDB"),
        linha(" [languages]           TypeScript · Python · Java"),
        linha(),
        linha(" $ cat current_focus.txt"),
        linha(),
        linha(" learning cybersec fundamentals · development"),
        linha(),
        linha(" $ cat hobbies.txt"),
        linha(),
        linha(" games · anime · movies · music · learning new things"),
        linha(),
        linha(" $ cat now_playing.txt"),
        linha(),
        linha(f"   top 3 this week · updated on {hoje}"),
        linha(f"   Artist of the Week: {artista_top}"),
        linha(),
    ]

    for i, (musica, contagem) in enumerate(top):
        medal  = medals[i]
        sufixo = f" ({contagem}x)"
        texto  = f"   {medal} {truncar(musica, max_musica - len(sufixo) - 4)}{sufixo}"
        linhas.append(linha(texto))

    linhas += [
        linha(),
        linha(" $ ./connect.sh"),
        linha(),
        linha(" > github:    https://github.com/joojpa"),
        linha(" > linkedin:  https://linkedin.com/in/joojpa"),
        linha(" > email:     joojpaz@gmail.com"),
        linha(),
        linha(" $ _"),
        f"└{BORDA}┘",
    ]

    return "\n".join(linhas)

def gerar_mini_terminal_artista(artista_top, imagem_url):
    LARGURA_MINI = 28
    BORDA = "─" * LARGURA_MINI

    def linha_mini(texto=""):
        pad = LARGURA_MINI - largura_real(texto) - 1
        pad = max(pad, 0)
        return f"│ {texto}{' ' * pad}│"

    titulo = truncar(artista_top, LARGURA_MINI - 4)

    linhas = [
        f"┌{BORDA}┐",
        linha_mini(" $ cat artist.txt"),
        f"├{BORDA}┤",
        linha_mini(),
        linha_mini(" Artist of the Week"),
        linha_mini(f" {titulo}"),
        linha_mini(),
        f"└{BORDA}┘",
    ]
    texto_terminal = "\n".join(linhas)

    bloco = "```\n" + texto_terminal + "\n```"
    if imagem_url:
        bloco += f'\n\n<p align="center"><img src="{imagem_url}" width="180" style="border-radius:12px"/></p>'
    return bloco

def gerar_bloco(terminal, imagem_url, artista_top):
    mini_terminal = gerar_mini_terminal_artista(artista_top, imagem_url)
    bloco = (
        "<table><tr>"
        "<td valign='top' style='vertical-align: top;'>\n\n"
        "```\n"
        f"{terminal}\n"
        "```\n\n"
        "</td>"
        "<td valign='top' align='center' style='vertical-align: top;'>\n\n"
        f"{mini_terminal}\n\n"
        "</td></tr></table>"
    )
    return bloco

def atualizar_readme(bloco):
    conteudo = README_FILE.read_text(encoding="utf-8")

    if MARKER_START not in conteudo or MARKER_END not in conteudo:
        print("Markers not found in README.")
        return False

    antes  = conteudo.split(MARKER_START)[0]
    depois = conteudo.split(MARKER_END)[1]
    novo   = f"{antes}{MARKER_START}\n{bloco}\n{MARKER_END}{depois}"
    README_FILE.write_text(novo, encoding="utf-8")
    print("README updated!")
    return True

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

    terminal = gerar_terminal(top3, artista_top)
    bloco    = gerar_bloco(terminal, imagem_url, artista_top)
    atualizar_readme(bloco)

if __name__ == "__main__":
    main()
