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
import threading
import time
import webbrowser
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import leitor  # noqa: E402
import habilidades  # noqa: E402
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


# A Central do jogo avisa a página: o desvio de abertura de tela do exe (patch centro_colunas,
# centro.open_code) anota a seção aberta em .fm26+0xD7F4 e conta as aberturas em +0xD7F8.
SECTION_NOW, OPENINGS, CENTRO_SECTION = 0x015C17F4, 0x015C17F8, 0x74636476     # 'tcdv'


def plans_file(time_uid) -> Path:
    HISTORY.mkdir(parents=True, exist_ok=True)
    return HISTORY / f"planos_{time_uid}.json"


def load_plans(time_uid) -> dict:
    file = plans_file(time_uid)
    return json.loads(file.read_text(encoding="utf-8")) if file.exists() else {"ativos": {}, "aprendidos": []}


def save_plans(time_uid, plans: dict) -> None:
    plans_file(time_uid).write_text(json.dumps(plans, ensure_ascii=False, indent=1), encoding="utf-8")


def attach_skills(payload: dict) -> dict:
    """Junta a cada jovem o plano ativo (avaliado pela data do jogo) e o catálogo de habilidades."""
    info, plans = payload["info"], load_plans(payload["info"]["time_uid"])
    for j in payload["jovens"]:
        known = j.get("movimentos_idx", [])
        plan = plans["ativos"].get(str(j["uid"]))
        j["habilidades"] = {
            "plano": habilidades.evaluate(plan, info["data"], j["atributos"], j["idade"], known) if plan else None,
            "catalogo": habilidades.catalog_for(j["atributos"], known),
            "semanas_estimadas": habilidades.weeks_needed(j["atributos"], j["idade"]),
            "aprendidos": [a for a in plans["aprendidos"] if a["uid"] == j["uid"]],
        }
    return payload


class Watcher:
    """Lê a tela aberta no jogo; ao entrar na Central de Desenvolvimento, atualiza a página aberta
    ou abre uma no navegador."""

    def __init__(self, url: str) -> None:
        self.url, self.entries, self.last_poll = url, 0, 0.0
        self.seen, self.opened_at = None, 0.0

    def run(self) -> None:
        jogo = None
        while True:
            time.sleep(0.7)
            try:
                jogo = jogo or leitor.Jogo()
                section, count = jogo.u32(SECTION_NOW), jogo.u32(OPENINGS)
            except Exception:                                            # jogo fechado ou exe antigo
                jogo = None
                continue
            if self.seen is None:
                self.seen = count
                continue
            if count != self.seen and section == CENTRO_SECTION:
                self.entries += 1
                page_open = time.time() - self.last_poll < 5
                if not page_open and time.time() - self.opened_at > 8:
                    self.opened_at = time.time()
                    webbrowser.open(self.url)
            self.seen = count


class Central(BaseHTTPRequestHandler):
    max_age = 19
    demo = False
    watcher: Watcher | None = None

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
                payload = attach_skills(payload)
                body = json.dumps(payload, ensure_ascii=False)
                self.reply(200, body.encode("utf-8"), "application/json; charset=utf-8")
            except Exception as error:                                   # jogo fechado, etc.
                self.reply(503, json.dumps({"erro": str(error)}).encode("utf-8"), "application/json")
            return
        if path == "/evento":
            watcher = self.watcher
            if watcher:
                watcher.last_poll = time.time()
            body = json.dumps({"centro": watcher.entries if watcher else 0})
            self.reply(200, body.encode("utf-8"), "application/json")
            return
        if path == "/fundo.jpg":
            self.reply(200, background(), "image/jpeg")
            return
        if path in FILES:
            file, kind = FILES[path]
            self.reply(200, file.read_bytes(), kind)
            return
        self.reply(404, f"nao encontrado: {path}".encode("utf-8"), "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        """Planos de habilidade: /plano {uid, idx}, /plano/cancelar {uid}, /aprender {uid}."""
        path = urlsplit(self.path).path
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if self.demo:
                raise RuntimeError("modo demo: nada é gravado")
            lista, info = leitor.jovens(self.max_age)
            player = next(j for j in lista if j.uid == int(body["uid"]))
            plans = load_plans(info["time_uid"])
            key = str(player.uid)
            if path == "/plano":
                index = int(body["idx"])
                if index not in habilidades.CATALOG:
                    raise ValueError("habilidade fora do catálogo")
                plans["ativos"][key] = {"idx": index, "inicio": info["data"],
                                        "semanas": habilidades.weeks_needed(player.atributos, player.idade)}
                result = {"ok": True}
            elif path == "/plano/cancelar":
                plans["ativos"].pop(key, None)
                result = {"ok": True}
            elif path == "/aprender":
                plan = plans["ativos"].get(key)
                state = plan and habilidades.evaluate(plan, info["data"], player.atributos, player.idade, player.movimentos_idx)
                if not state or not state["pronto"]:
                    raise ValueError("o plano ainda não está pronto")
                bits = leitor.learn(player.uid, plan["idx"], habilidades.CATALOG[plan["idx"]][2])
                plans["ativos"].pop(key)
                plans["aprendidos"].append({"uid": player.uid, "idx": plan["idx"], "nome": state["nome"], "data": info["data"]})
                result = {"ok": True, "bits": bits}
            else:
                self.reply(404, b"{}", "application/json")
                return
            save_plans(info["time_uid"], plans)
            self.reply(200, json.dumps(result).encode("utf-8"), "application/json")
        except Exception as error:
            self.reply(400, json.dumps({"erro": str(error)}, ensure_ascii=False).encode("utf-8"), "application/json")

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
    if not args.demo:
        Central.watcher = Watcher(url)
        threading.Thread(target=Central.watcher.run, daemon=True).start()
        print("Ao entrar na Central de Desenvolvimento do jogo, esta página abre ou se atualiza sozinha.")
    if not args.sem_navegador:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
