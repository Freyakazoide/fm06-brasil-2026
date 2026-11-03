r"""Servidor local da Sala de Imprensa — no modo demo, independente do save; com --jogo, só leitura.

Uso:
    python tools\imprensa\servidor.py
    python tools\imprensa\servidor.py --jogo        (elenco e agenda do FM06 aberto, só leitura)
    python tools\imprensa\servidor.py --porta 8629 --sem-navegador
"""

from __future__ import annotations

import argparse
import json
import threading
import time
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import banco  # noqa: E402
import demo  # noqa: E402
import noticias  # noqa: E402
import ponte  # noqa: E402
import veiculos  # noqa: E402


FILES = {
    "/": (HERE / "pagina.html", "text/html; charset=utf-8"),
    "/imprensa.css": (HERE / "imprensa.css", "text/css; charset=utf-8"),
    "/imprensa.js": (HERE / "imprensa.js", "text/javascript; charset=utf-8"),
}
PORT = 8629


class NewsWatcher:
    """--jogo: lê a caixa de entrada a cada 2 s; a notícia que passa a lida vira pauta "agora" e a
    página se atualiza (ou abre no navegador, se não estiver aberta)."""

    def __init__(self, url: str) -> None:
        self.url, self.read, self.events = url, None, []
        self.last_poll, self.opened_at = 0.0, 0.0

    def run(self) -> None:
        jogo = None
        while True:
            time.sleep(2)
            try:
                import leitor
                jogo = jogo or leitor.Jogo()
                items = noticias.inbox(jogo)
            except Exception:                                   # jogo fechado ou carregando
                jogo, self.read = None, None
                continue
            read_now = {n["serie"] for n in items if n["lida"]}
            if self.read is None:                               # 1ª leitura: só a base
                self.read = read_now
                continue
            fresh = [n for n in items if n["lida"] and n["serie"] not in self.read]
            self.read = read_now
            if not fresh:
                continue
            for item in sorted(fresh, key=lambda n: n["serie"]):
                self.events.insert(0, item)
            del self.events[10:]
            with PressRoom.lock:
                PressRoom.cache = None
            if time.time() - self.last_poll > 5 and time.time() - self.opened_at > 8:
                self.opened_at = time.time()
                webbrowser.open(self.url)


class PressRoom(BaseHTTPRequestHandler):
    server_version = "FM06PressRoom/1.0"
    live_club: str | None = None                                # --jogo: nome do clube humano
    watcher: NewsWatcher | None = None
    cache: tuple[float, dict] | None = None
    lock = threading.Lock()

    @classmethod
    def data(cls) -> dict:
        """Demo, ou o jogo aberto (leitura cara: guarda por 2 minutos; sem jogo, volta ao demo avisando)."""
        if not cls.live_club:
            return demo.payload()
        with cls.lock:
            if cls.cache and time.monotonic() - cls.cache[0] < 120:
                return cls.cache[1]
            try:
                value = ponte.live_payload(cls.live_club, cls.watcher.events if cls.watcher else [])
            except Exception as error:                          # jogo fechado ou leitura falhou
                value = demo.payload()
                value["info"]["notice"] = f"FM06 não lido ({error}). Mostrando a demonstração."
                return value
            cls.cache = (time.monotonic(), value)
            return value

    def do_GET(self) -> None:
        path = unquote(urlsplit(self.path).path)
        if path == "/dados":
            self._json(200, self.data())
            return
        if path == "/evento":
            watcher = self.watcher
            if watcher:
                watcher.last_poll = time.time()
            self._json(200, {"noticias": len(watcher.events) if watcher else 0,
                             "serie": watcher.events[0]["serie"] if watcher and watcher.events else None})
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
    parser.add_argument("--jogo", action="store_true", help="lê o elenco do FM06 aberto (só leitura)")
    parser.add_argument("--clube", default="Figueirense", help="nome do clube humano, para os veículos")
    args = parser.parse_args()
    problems = banco.validate()
    if problems:
        raise SystemExit("Banco editorial inválido:\n- " + "\n- ".join(problems))
    url = f"http://127.0.0.1:{args.porta}"
    server = ThreadingHTTPServer(("127.0.0.1", args.porta), PressRoom)
    print(f"Sala de Imprensa: {url}")
    print(f"Banco: {banco.stats()}")
    if args.jogo:
        PressRoom.live_club = args.clube
        PressRoom.watcher = NewsWatcher(url)
        threading.Thread(target=PressRoom.watcher.run, daemon=True).start()
        print(f"Modo jogo: lê o elenco do {args.clube} no FM06 aberto, sem gravar nada.")
        print("Ao abrir uma notícia na caixa de entrada do jogo, a pauta dela aparece aqui.")
    else:
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

