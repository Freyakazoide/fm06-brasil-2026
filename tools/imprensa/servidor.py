r"""Servidor local da Sala de Imprensa — sempre independente do save.

Uso:
    python tools\imprensa\servidor.py
    python tools\imprensa\servidor.py --porta 8629 --sem-navegador
"""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import banco  # noqa: E402
import demo  # noqa: E402
import veiculos  # noqa: E402


FILES = {
    "/": (HERE / "pagina.html", "text/html; charset=utf-8"),
    "/imprensa.css": (HERE / "imprensa.css", "text/css; charset=utf-8"),
    "/imprensa.js": (HERE / "imprensa.js", "text/javascript; charset=utf-8"),
}
PORT = 8629


class PressRoom(BaseHTTPRequestHandler):
    server_version = "FM06PressRoom/1.0"

    def do_GET(self) -> None:
        path = unquote(urlsplit(self.path).path)
        if path == "/dados":
            self._json(200, demo.payload())
            return
        if path == "/banco":
            self._json(200, {"stats": banco.stats(), "situations": banco.bank()})
            return
        if path.startswith("/logos/") and path.endswith(".svg"):
            body = veiculos.logo_svg(path.removeprefix("/logos/").removesuffix(".svg"))
            if body is not None:
                self._reply(200, body, "image/svg+xml; charset=utf-8")
                return
        if path in FILES:
            file, content_type = FILES[path]
            self._reply(200, file.read_bytes(), content_type)
            return
        self._reply(404, b"nao encontrado", "text/plain; charset=utf-8")

    def _json(self, status: int, value: object) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self._reply(status, body, "application/json; charset=utf-8")

    def _reply(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, message: str, *args: object) -> None:
        print(f"[imprensa] {self.address_string()} - {message % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sala de Imprensa do FM06 Brasil")
    parser.add_argument("--porta", type=int, default=PORT)
    parser.add_argument("--sem-navegador", action="store_true")
    args = parser.parse_args()
    problems = banco.validate()
    if problems:
        raise SystemExit("Banco editorial inválido:\n- " + "\n- ".join(problems))
    url = f"http://127.0.0.1:{args.porta}"
    server = ThreadingHTTPServer(("127.0.0.1", args.porta), PressRoom)
    print(f"Sala de Imprensa: {url}")
    print(f"Banco: {banco.stats()}")
    print("Modo demonstração: não lê nem escreve no save.")
    if not args.sem_navegador:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

