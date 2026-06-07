#!/usr/bin/env python3
"""
Busca o top 3 da semana no Last.fm e atualiza o README.md do perfil GitHub.
Rodado pelo GitHub Actions diariamente.
"""
import urllib.request
import urllib.parse
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

LASTFM_API_KEY = "3affae9bce83cc5fd8d062d2b61e772d"
LASTFM_USER    = "joojpa"
README_FILE    = Path(__file__).parent.parent / "README.md"

MARKER_START = "<!-- MUSIC_START -->"
MARKER_END   = "<!-- MUSIC_END -->"
LARGURA      = 69  # largura interna da caixa (entre │ e │)

def buscar_top_semana():
    hoje         = datetime.now().date()
    inicio_semana = hoje - timedelta(days=7)
    inicio = int(datetime(inicio_semana.year, inicio_semana.month, inicio_semana.day, 0, 0, 0).timestamp())
    fim    = int(datetime(hoje.year, hoje.month, hoje.day, 23, 59, 59).timestamp())

    musicas = []
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

        attr = data.get("recenttracks", {}).get("@attr", {})
        if page >= int(attr.get("totalPages", 1)):
            break
        page += 1

    return Counter(musicas).most_common(3)

def linha(texto=""):
    """Formata uma linha dentro da caixa com padding correto."""
    # Emojis ocupam 2 colunas no terminal — ajusta a contagem
    visivel = len(texto.encode('utf-16-le')) // 2
    pad = LARGURA - visivel - 2  # -2 por causa dos espaços laterais
    pad = max(pad, 0)
    return f"│  {texto}{' ' * pad} │"

def gerar_bloco(top):
    hoje   = datetime.now().strftime("%d/%m/%Y")
    medals = ["🥇", "🥈", "🥉"]

    linhas = [
        "```",
        linha(f"$ cat now_playing.txt"),
        linha(),
        linha(f"  top 3 da semana · atualizado em {hoje}"),
        linha(),
    ]

    for i, (musica, contagem) in enumerate(top):
        medal = medals[i]
        texto = f"  {medal} {musica} ({contagem}x)"
        # trunca se muito longo
        while len(texto.encode('utf-16-le')) // 2 > LARGURA - 4:
            texto = texto[:-4] + "..."
        linhas.append(linha(texto))

    linhas += [
        linha(),
        "```",
    ]
    return "\n".join(linhas)

def atualizar_readme(bloco):
    conteudo = README_FILE.read_text(encoding="utf-8")

    if MARKER_START not in conteudo or MARKER_END not in conteudo:
        print("Marcadores não encontrados no README.")
        return False

    antes  = conteudo.split(MARKER_START)[0]
    depois = conteudo.split(MARKER_END)[1]
    novo   = f"{antes}{MARKER_START}\n{bloco}\n{MARKER_END}{depois}"
    README_FILE.write_text(novo, encoding="utf-8")
    print("README atualizado!")
    return True

def main():
    print("Buscando top 3 da semana...")
    top = buscar_top_semana()

    if not top:
        print("Nenhum scrobble encontrado.")
        return

    print("Top 3:")
    for musica, contagem in top:
        print(f"  {musica} ({contagem}x)")

    bloco = gerar_bloco(top)
    atualizar_readme(bloco)

if __name__ == "__main__":
    main()
