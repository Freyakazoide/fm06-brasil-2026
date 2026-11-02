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


class Central(BaseHTTPRequestHandler):
    max_age = 19

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path == "/dados":
            try:
                lista, info = leitor.jovens(self.max_age)
                body = json.dumps({"info": info, "jovens": [asdict(j) for j in lista]}, ensure_ascii=False)
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
