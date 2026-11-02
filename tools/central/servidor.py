"""Central de Desenvolvimento externa: página local com os jovens do clube (só leitura).

    python tools\\central\\servidor.py            (abre http://127.0.0.1:8626 no navegador)
    python tools\\central\\servidor.py --idade 21 --sem-navegador

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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import leitor  # noqa: E402

ASSETS = ROOT / "data" / "brasil" / "telas" / "centro_desenvolvimento" / "assets"
FILES = {
    "/": (HERE / "pagina.html", "text/html; charset=utf-8"),
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
        str(j.uid): {"hab": j.hab, "pot": j.pot,
                     **{g: round(sum(j.atributos.get(a, 0) for a in names) / len(names), 1)
                        for g, names in GROUPS.items()}}
        for j in lista}
    file.write_text(json.dumps(days, ensure_ascii=False, indent=0), encoding="utf-8")
    series: dict[str, list[dict]] = {}
    for day in sorted(days):
        for uid, point in days[day].items():
            series.setdefault(uid, []).append({"data": day, **point})
    return series


class Central(BaseHTTPRequestHandler):
    max_age = 19

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path == "/dados":
            try:
                lista, info = leitor.jovens(self.max_age)
                body = json.dumps({"info": info, "jovens": [asdict(j) for j in lista],
                                   "historico": remember(lista, info)}, ensure_ascii=False)
                self.reply(200, body.encode("utf-8"), "application/json; charset=utf-8")
            except Exception as error:                                   # jogo fechado, etc.
                self.reply(503, json.dumps({"erro": str(error)}).encode("utf-8"), "application/json")
            return
        if path in FILES:
            file, kind = FILES[path]
            self.reply(200, file.read_bytes(), kind)
            return
        self.reply(404, b"nao encontrado", "text/plain")

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
    args = parser.parse_args()
    Central.max_age = args.idade
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Central)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Central de Desenvolvimento em {url} (Ctrl+C para fechar)")
    if not args.sem_navegador:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
