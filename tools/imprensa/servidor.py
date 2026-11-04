r"""Servidor local da Sala de Imprensa — no modo demo, independente do save; com --jogo, lê o jogo e grava só a moral.

Uso:
    python tools\imprensa\servidor.py
    python tools\imprensa\servidor.py --jogo        (elenco e agenda do FM06 aberto; a resposta mexe na moral)
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
sys.path[:0] = [str(HERE), str(HERE.parent / "re")]

import banco  # noqa: E402
import central  # noqa: E402
import demo  # noqa: E402
import efeitos  # noqa: E402
import estado  # noqa: E402
import noticias  # noqa: E402
import ponte  # noqa: E402
import repercussao  # noqa: E402
import chamada_remota as cr  # noqa: E402
import laco  # noqa: E402
import texto_noticia  # noqa: E402
import veiculos  # noqa: E402


ASSETS = HERE.parents[1] / "data" / "brasil" / "telas" / "centro_desenvolvimento" / "assets"
FILES = {
    "/": (HERE / "pagina.html", "text/html; charset=utf-8"),
    "/imprensa.css": (HERE / "imprensa.css", "text/css; charset=utf-8"),
    "/imprensa.js": (HERE / "imprensa.js", "text/javascript; charset=utf-8"),
    "/noticias": (HERE / "noticias.html", "text/html; charset=utf-8"),
    "/noticias.js": (HERE / "noticias.js", "text/javascript; charset=utf-8"),
    "/noticias.css": (HERE / "noticias.css", "text/css; charset=utf-8"),
    # a Central de Notícias usa o visual da Central de Desenvolvimento
    "/central.css": (HERE.parent / "central" / "central.css", "text/css; charset=utf-8"),
    "/emblema.png": (ASSETS / "emblema-centro-desenvolvimento.png", "image/png"),
}
TEXTS_PER_TICK = 8                                              # textos lidos por volta, só com o jogo parado
PORT = 8629


_BACKGROUND: bytes | None = None


def background() -> bytes:
    """O campo de treino da Central de Desenvolvimento em JPG leve (feito uma vez)."""
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


class NewsWatcher:
    """--jogo: lê a caixa de entrada a cada 2 s; a notícia que passa a lida vira pauta "agora" e a
    página se atualiza (ou abre no navegador, se não estiver aberta)."""

    def __init__(self, url: str, exclusive: bool = False, extra: frozenset[str] = frozenset(),
                 every: bool = False) -> None:
        self.url, self.read, self.events = url, None, []
        self.last_poll, self.opened_at = 0.0, 0.0
        self.exclusive, self.count, self.squad, self.career = exclusive, None, None, None
        self.extra, self.every = extra, every                   # every: --exclusivo-todas
        self.since = None                                       # só notícias chegadas depois de ligar

    def know_squad(self) -> bool:
        """Elenco e carreira, lidos uma vez por jogo aberto; False se o jogo estiver no meio de uma mudança."""
        if self.squad is None:
            import leitor
            try:
                jovens, info = leitor.jovens(max_age=99)
            except Exception:
                return False
            self.squad = {j.uid for j in jovens}
            self.career = estado.save_id(info.get("clube_nome") or PressRoom.live_club, info.get("time_uid"))
        return True

    def missing_texts(self, items: list[dict]) -> list[int]:
        known = estado.texts(self.career)
        return [n for n in sorted(items, key=lambda n: -n["serie"]) if central.text_key(n) not in known]

    def wanted(self, items: list[dict]) -> list[dict]:
        if not self.exclusive:
            return []
        test = noticias.exclusive_any if self.every else lambda n: noticias.exclusive(n, self.squad, self.extra)
        return [n for n in items if n["serie"] > self.since and test(n)]

    def with_game_parked(self, jogo, items: list[dict]) -> list[dict]:
        """Captura e textos numa pausa só da thread principal do jogo (laco.py); sem trabalho, não
        para o jogo. Se ela não parar a tempo, fica para a próxima volta."""
        if not self.know_squad() or not (self.wanted(items) or self.missing_texts(items)):
            return []
        pid, handle = cr.game()
        try:
            with laco.parked(pid, handle):
                taken = self.capture(jogo, handle, items)
                gone = {n["serie"] for n in taken}
                self.fill_texts(jogo, handle, [n for n in items if n["serie"] not in gone])
                return taken
        except TimeoutError:
            return []
        finally:
            cr.kernel32.CloseHandle(handle)

    def fill_texts(self, jogo, handle, items: list[dict]) -> None:
        """Central de Notícias: lê manchete e corpo (função do jogo) das notícias que ainda não têm,
        algumas por volta. Uma falha só adia para a próxima volta."""
        new = {}
        for news in self.missing_texts(items)[:TEXTS_PER_TICK]:
            try:
                new[central.text_key(news)] = texto_noticia.text_of(jogo, handle, news["serie"])
            except (Exception, SystemExit) as error:
                print(f"[imprensa] texto da notícia {news['serie']} não lido: {error}")
                break
        if new:
            estado.add_texts(self.career, new)

    def capture(self, jogo, handle, items: list[dict]) -> list[dict]:
        """--exclusivo: guarda a notícia de imprensa do elenco (com manchete e corpo, montados pelo
        próprio jogo) e a tira da caixa do jogo. Sem texto, a notícia não sai. Qualquer falha desliga
        o modo (a caixa do jogo nunca fica pela metade por insistência)."""
        taken = []
        for item in self.wanted(items):
            try:
                item = {**item, **texto_noticia.text_of(jogo, handle, item["serie"])}
                if not item["manchete"]:
                    raise RuntimeError("manchete vazia")
                estado.add_capture(self.career, item, None)                # guardada antes de sair do jogo
                removed = noticias.remove(jogo, item["serie"])
                if any(n["serie"] == item["serie"] for n in noticias.inbox(jogo)):
                    raise RuntimeError("continua na caixa depois da remoção")
            except (Exception, SystemExit) as error:
                self.exclusive = False
                print(f"[imprensa] modo exclusivo desligado: notícia {item['serie']}: {error}")
                break
            estado.add_capture(self.career, item, removed)
            print(f"[imprensa] notícia {item['serie']} ({item['classe']}) tirada da caixa do jogo: só na Sala")
            taken.append({**item, "exclusiva": True})
        return taken

    def run(self) -> None:
        while True:                                             # o observador nunca morre por um erro
            try:
                self.watch()
            except Exception as error:
                print(f"[imprensa] observador: {error!r}; recomeçando")
                self.read, self.count, self.squad = None, None, None

    def watch(self) -> None:
        jogo = None
        while True:
            time.sleep(2)
            try:
                import leitor
                jogo = jogo or leitor.Jogo()
                items = noticias.inbox(jogo)
            except Exception:                                   # jogo fechado ou carregando
                jogo, self.read, self.count, self.squad, self.since = None, None, None, None, None
                continue
            taken = []
            if self.since is None:
                self.since = max((n["serie"] for n in items), default=0)
            if self.count == len(items):                            # caixa parada há 2 s: jogo ocioso
                taken = self.with_game_parked(jogo, items)
            self.count = len(items) - len(taken)
            read_now = {n["serie"] for n in items if n["lida"]}
            if self.read is None:                               # 1ª leitura: só a base
                self.read = read_now
                continue
            fresh = [n for n in items if n["lida"] and n["serie"] not in self.read] + taken
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
    effects = False                                             # --jogo sem --sem-efeitos: moral no jogo
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
            value = dict(self.data())                           # a resposta gravada não espera o cache
            career = value["info"].get("career", "demo")
            value["estado"] = estado.load(career)
            for key, answer in list(value["estado"]["respostas"].items()):   # respostas de antes do §8.8
                if "repercussao" not in answer:
                    value["estado"] = self._repercussion(career, key, value["estado"])
            value["info"] = {**value["info"], "mode_effects": bool(self.effects and self.live_club)}
            self._json(200, value)
            return
        if path == "/central":
            self._json(200, self.news_center())
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
        if path == "/fundo.jpg":
            self._reply(200, background(), "image/jpeg")
            return
        if path in FILES:
            file, content_type = FILES[path]
            self._reply(200, file.read_bytes(), content_type)
            return
        self._reply(404, b"nao encontrado", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/resposta":
            self._reply(404, b"nao encontrado", "text/plain; charset=utf-8")
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
            info = self.data()["info"]
            career = info.get("career", "demo")
            state = estado.record(career, body)
            if self.effects and self.live_club and info.get("career", "demo") != "demo":
                player, date = int(body["player_id"]), body.get("date") or info["date"]
                delta = efeitos.allowed(state["respostas"][str(body["key"])]["effects"]["player"], player, date, state["moral"])
                try:
                    result = efeitos.apply_morale(player, delta)
                except Exception as error:                      # jogo fechado no meio do caminho
                    result = {"erro": f"jogo não respondeu: {error}"}
                state = estado.note_morale(career, str(body["key"]), player, date, result)
                with PressRoom.lock:
                    PressRoom.cache = None                      # a moral nova aparece no próximo /dados
            state = self._repercussion(career, str(body["key"]), state)
            self._json(200, state)
        except ValueError as error:
            self._json(400, {"erro": str(error)})

    def news_center(self) -> dict:
        """Central de Notícias: caixa do jogo (lida agora) + capturadas + textos guardados."""
        info = self.data()["info"]
        career = info.get("career", "demo")
        if not self.live_club or career == "demo":
            return central.payload([], [], {}, {**info, "aviso": "Sem jogo aberto: rode o servidor com --jogo."})
        try:
            import leitor
            inbox = noticias.inbox(leitor.Jogo())
        except Exception as error:
            return central.payload([], estado.captures(career), estado.texts(career),
                                   {**info, "aviso": f"Caixa do jogo não lida ({error}); mostrando só as capturadas."})
        return central.payload(inbox, estado.captures(career), estado.texts(career), info)

    def _repercussion(self, career: str, key: str, state: dict) -> dict:
        """Matéria do veículo sobre a resposta (§8.8); se faltar algum dado, a resposta fica sem ela."""
        answer = state["respostas"][key]
        data = self.data()
        situation = next((s for s in data["situations"] if s["id"] == answer["situation_id"]), None)
        intention = situation and next((i for i in situation["intentions"] if i["id"] == answer["answer_id"]), None)
        player = next((p for p in data["players"] if str(p["id"]) == str(answer["player_id"])), {})
        outlet = next((o for o in data["outlets"] if o["id"] == answer["outlet_id"]), None)
        if not (intention and outlet):
            return state
        story = repercussao.build(key, answer, intention, situation, player, outlet, data["info"], state)
        return estado.note_repercussion(career, key, story)

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
    parser.add_argument("--sem-efeitos", action="store_true", help="--jogo sem mexer na moral do jogo")
    parser.add_argument("--exclusivo", action="store_true",
                        help="--jogo: notícia de imprensa do elenco sai da caixa do jogo e fica só na Sala")
    parser.add_argument("--exclusivo-classes", default="", help="teste: classes a mais, ex. MOM_SUMMARY_NEWS")
    parser.add_argument("--exclusivo-todas", action="store_true",
                        help="--jogo: toda notícia nova sem resposta sai da caixa do jogo e fica só na Central de Notícias")
    args = parser.parse_args()
    problems = banco.validate()
    if problems:
        raise SystemExit("Banco editorial inválido:\n- " + "\n- ".join(problems))
    url = f"http://127.0.0.1:{args.porta}"
    # sem SO_REUSEADDR: no Windows ele deixa um 2º servidor ocupar a mesma porta e o navegador
    # continua falando com o antigo (03/11)
    ThreadingHTTPServer.allow_reuse_address = False
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.porta), PressRoom)
    except OSError:
        raise SystemExit(f"A porta {args.porta} já está em uso: feche a outra janela deste servidor (Ctrl+C) e rode de novo.")
    print(f"Sala de Imprensa: {url}")
    print(f"Banco: {banco.stats()}")
    if args.jogo:
        PressRoom.live_club = args.clube
        PressRoom.effects = not args.sem_efeitos
        PressRoom.watcher = NewsWatcher(url, exclusive=args.exclusivo or args.exclusivo_todas,
                                         extra=frozenset(c for c in args.exclusivo_classes.split(",") if c),
                                         every=args.exclusivo_todas)
        threading.Thread(target=PressRoom.watcher.run, daemon=True).start()
        print(f"Modo jogo: lê o elenco do {args.clube} no FM06 aberto; a resposta mexe só na moral do jogador (--sem-efeitos desliga).")
        print("Ao abrir uma notícia na caixa de entrada do jogo, a pauta dela aparece aqui.")
        if args.exclusivo_todas:
            print("Modo exclusivo (todas): toda notícia nova sem resposta sai da caixa do jogo e fica só na Central de Notícias (salve o jogo para manter).")
        elif args.exclusivo:
            print("Modo exclusivo: notícia de imprensa do elenco sai da caixa do jogo e fica só aqui (salve o jogo para manter).")
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

