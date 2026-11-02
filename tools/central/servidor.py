"""Central de Desenvolvimento externa: página local com os jovens do clube (só leitura).

    python tools\\central\\servidor.py            (abre http://127.0.0.1:8626 no navegador)
    python tools\\central\\servidor.py --idade 21 --sem-navegador
    python tools\\central\\servidor.py --demo      (abre uma amostra sem precisar do jogo)

Cada vez que a página pede /dados, o leitor lê o jogo aberto de novo (leitor.py). Nada é escrito
no jogo.
"""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import leitor  # noqa: E402
import demo  # noqa: E402

ASSETS = ROOT / "data" / "brasil" / "telas" / "centro_desenvolvimento" / "assets"
FILES = {
    "/": (HERE / "pagina.html", "text/html; charset=utf-8"),
    "/central.css": (HERE / "central.css", "text/css; charset=utf-8"),
    "/central.js": (HERE / "central.js", "text/javascript; charset=utf-8"),
    "/camisa.png": (ASSETS / "camisa-costas-figueirense-base.png", "image/png"),
    "/emblema.png": (ASSETS / "emblema-centro-desenvolvimento.png", "image/png"),
}
PORT = 8626
HISTORY = ROOT / "workspace" / "central"                    # uma foto por data do jogo (só local)
GROUPS = {
    "tec": ("Heading", "Corner", "Long Shots", "Crossing", "Tackling", "Finishing", "Dribbling", "Throwing",
            "Set Pieces", "Marking", "Penalty", "Passing", "First Touch", "Technique"),
    "men": ("Aggression", "Anticipation", "Bravery", "Composure", "Concentration", "Creativity", "Decision",
            "Determination", "Influence", "Flair", "Positioning", "Off the ball", "Team work", "Work rate"),
    "fis": ("Acceleration", "Agility", "Balance", "Natural fit.", "Strength", "Jumping", "Stamina", "Pace"),
}


def remember(lista, info) -> dict[str, list[dict]]:
    """Guarda a foto de hoje (substitui a do mesmo dia) e devolve a série de cada jovem por UID."""
    HISTORY.mkdir(parents=True, exist_ok=True)
    file = HISTORY / f"historico_{info['time_uid']}.json"
    days = json.loads(file.read_text(encoding="utf-8")) if file.exists() else {}
    days[info["data"]] = {
        str(j.uid): {"hab": j.hab, "pot": j.pot, "time": j.time, "moral": j.moral,
                     "prontidao": j.analise.get("prontidao"), "fase": j.analise.get("fase"),
                     "alvo": j.adjunto.get("alvo"), "nota_funcao": j.analise.get("nota_funcao"),
                     "atributos": j.atributos,
                     **{g: round(sum(j.atributos.get(a, 0) for a in names) / len(names), 1)
                        for g, names in GROUPS.items()}}
        for j in lista}
    file.write_text(json.dumps(days, ensure_ascii=False, indent=0), encoding="utf-8")
    series: dict[str, list[dict]] = {}
    for day in sorted(days):
        for uid, point in days[day].items():
            series.setdefault(uid, []).append({"data": day, **point})
    return series


_BACKGROUND: bytes | None = None


def background() -> bytes:
    """O campo de treino do MD em JPG leve (feito uma vez, na primeira vez que a página pede)."""
    global _BACKGROUND
    if _BACKGROUND is None:
        import io
        from PIL import Image
        image = Image.open(ASSETS / "fundo-centro-treinamento.png").convert("RGB")
        image.thumbnail((1600, 1600))
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=80, optimize=True)
        _BACKGROUND = buffer.getvalue()
    return _BACKGROUND


class Central(BaseHTTPRequestHandler):
    max_age = 19
    demo = False

    def do_GET(self) -> None:
        # Alguns navegadores/proxies locais enviam a URL absoluta na linha do GET.
        path = urlsplit(self.path).path
        if path == "/dados":
            try:
                if self.demo:
                    payload = demo.payload()
                else:
                    lista, info = leitor.jovens(self.max_age)
                    payload = {"schema_version": 2, "info": info, "jovens": [asdict(j) for j in lista],
                               "historico": remember(lista, info)}
                body = json.dumps(payload, ensure_ascii=False)
                self.reply(200, body.encode("utf-8"), "application/json; charset=utf-8")
            except Exception as error:                                   # jogo fechado, etc.
                self.reply(503, json.dumps({"erro": str(error)}).encode("utf-8"), "application/json")
            return
        if path == "/fundo.jpg":
            self.reply(200, background(), "image/jpeg")
            return
        if path in FILES:
            file, kind = FILES[path]
            self.reply(200, file.read_bytes(), kind)
            return
        self.reply(404, f"nao encontrado: {path}".encode("utf-8"), "text/plain; charset=utf-8")

    def reply(self, status: int, body: bytes, kind: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:                               # sem barulho no terminal
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--idade", type=int, default=19)
    parser.add_argument("--sem-navegador", action="store_true")
    parser.add_argument("--demo", action="store_true", help="usa dados demonstrativos sem abrir o jogo")
    parser.add_argument("--porta", type=int, default=PORT)
    args = parser.parse_args()
    Central.max_age = args.idade
    Central.demo = args.demo
    server = ThreadingHTTPServer(("127.0.0.1", args.porta), Central)
    url = f"http://127.0.0.1:{args.porta}/"
    print(f"Central de Desenvolvimento em {url} (Ctrl+C para fechar)")
    if not args.sem_navegador:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
