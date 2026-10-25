"""O mod inteiro, na ordem, com um comando só.

    python scripts\\aplicar_tudo.py              (tudo, do zero)
    python scripts\\aplicar_tudo.py --rapido     (sem a contagem dos elencos no jogo: usa o
                                                workspace\\elencos_2005.csv que já existe)
    python scripts\\aplicar_tudo.py --etapa 3    (recomeça da etapa 3, depois de um erro)

Etapas (o script para e avisa quando o jogo tem de ser aberto ou fechado):
1. jogo fechado: aplicar_brasil_2026.py --apply e reforcar_elencos.py --apply (na primeira
   vez, antes do reforço, um New Game para contar os elencos de 2005 sem reforço);
2. jogo aberto (New Game, tela principal): live_player_editor.py --squads-all, que conta
   os jogadores de 2005 de cada clube; depois feche o jogo;
3. jogo fechado: montar_elencos.py, aplicar_comissao.py --apply, aplicar_arbitros.py --apply,
   aplicar_historico.py --apply, gravar_atributos.py --apply (atributos, CA/PA, personalidade,
   físico, nascimento, nação, preferred moves e jogos pela seleção dos jogadores direto no
   people_db) e a cópia do .lnc dos jogadores para data\\db\\lnc\\all. Depois: New Game.

O injetor (live_player_editor.py ... --apply, a antiga etapa 4) não é mais usado: tudo o que
ele gravava na memória vai agora no arquivo (docs\\reversing\\rea-atributos.md). Continua para
conferência (--show) e para a contagem dos elencos da etapa 2.

A contagem dos elencos é dos clubes de identidade_fm06.csv e, com data\\estrangeiros
(coletar_estrangeiros.py), dos clubes da CONMEBOL (workspace\\identidades_todas.csv).

O --rapido pula a etapa 2: serve quando os elencos de 2005 não mudaram (mudou só
tradução, comissão, árbitros, histórico, rivais...). Ele refaz o reforço e confere se o
people_db e a lista de clubes ficaram iguais aos da última contagem (os SHA-256
guardados na etapa 2); se não ficaram, a contagem está velha e ele para pedindo a
rodada completa. Se um passo dá erro,
o script para ali; corrija e rode de novo com --etapa.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import estrangeiros  # noqa: E402

IDENTITIES = ROOT / "workspace" / "identidades_todas.csv"    # Brasil + CONMEBOL, para a contagem
PLAYERS_LNC = ROOT / "workspace" / "mods" / "brasil_2026_jogadores.lnc"
HOSTS = ROOT / "workspace" / "elencos_2005.csv"
HOSTS_BASE = ROOT / "workspace" / "elencos_2005_sem_reforco.csv"     # contagem antes do reforço
COUNTED = ROOT / "workspace" / "elencos_2005_people_db.sha256"        # people_db da última contagem
GAME_EXES = ("fm_brasil.exe", "fm.exe")


def game_dir() -> Path:
    return Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])


def game_running() -> bool | None:
    """True/False pelo tasklist do Windows; None quando não dá para saber."""
    if sys.platform != "win32":
        return None
    try:
        out = subprocess.run(["tasklist"], capture_output=True, text=True, errors="replace").stdout.lower()
    except OSError:
        return None
    return any(exe in out for exe in GAME_EXES)


def wait(message: str) -> None:
    try:
        input(f"\n>>> {message}\n    Aperte Enter quando estiver pronto (Ctrl+C para parar). ")
    except (KeyboardInterrupt, EOFError):
        sys.exit("\nParado. Para continuar daqui, rode de novo com --etapa.")


def need_closed() -> None:
    while game_running():
        wait("Feche o jogo (os arquivos do banco não podem estar em uso).")


def need_open() -> None:
    wait("Abra o fm_brasil.exe e comece um New Game com: Países Escolhidos = só o Brasil; Base Dados = a\n"
         "    maior; Carregar Todos Jogadores de = os países da América do Sul (senão os clubes da CONMEBOL\n"
         "    ficam sem os jogadores de 2026). Espere chegar na tela principal.")
    while game_running() is False:
        wait("Não achei o fm_brasil.exe aberto. Abra o jogo e chegue na tela principal.")


def people_sha(game: Path) -> str:
    return hashlib.sha256((game / "data" / "db" / "people_db.dat").read_bytes()).hexdigest().upper()


def counted_key(game: Path) -> str:
    """O que a contagem dos elencos depende: o people_db e a lista dos clubes contados."""
    clubs = hashlib.sha256(estrangeiros.write_all_identities(IDENTITIES).read_bytes()).hexdigest().upper()
    return f"{people_sha(game)}\n{clubs}"


def run(stage: int, script: str, *args: str, retry: bool = False) -> None:
    print(f"\n=== etapa {stage}: {script} {' '.join(args)}".rstrip(), flush=True)
    while True:
        if subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=ROOT).returncode == 0:
            return
        if not retry:
            sys.exit(f"\n[ERRO] {script} falhou. Corrija e rode de novo: python scripts\\aplicar_tudo.py --etapa {stage}")
        wait(f"{script} falhou (o jogo está na tela principal?). Enter tenta de novo.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rapido", action="store_true", help="sem o reforço e sem a contagem dos elencos no jogo")
    parser.add_argument("--etapa", type=int, default=1, choices=(1, 2, 3), help="recomeça desta etapa")
    args = parser.parse_args()
    if args.rapido and not HOSTS.exists():
        sys.exit(f"[ERRO] --rapido precisa do {HOSTS.relative_to(ROOT)}; rode sem --rapido.")
    game = game_dir()
    lnc = game / "data" / "db" / "lnc" / "all" / PLAYERS_LNC.name

    if args.etapa <= 1:
        need_closed()
        run(1, "aplicar_brasil_2026.py", "--apply")
        if not args.rapido:
            if not HOSTS_BASE.exists() and not HOSTS.exists():     # instalação nova: contar antes do reforço
                print("\nPrimeira vez: o reforço precisa da contagem dos elencos de 2005 sem reforço.")
                need_open()
                estrangeiros.write_all_identities(IDENTITIES)
                run(1, "live_player_editor.py", "--squads-all", str(IDENTITIES), retry=True)
                need_closed()
        run(1, "reforcar_elencos.py", "--apply")
        if args.rapido and (not COUNTED.exists() or COUNTED.read_text().strip() != counted_key(game)):
            sys.exit("\n[ERRO] O people_db ou a lista de clubes (data\\estrangeiros) mudou desde a última contagem\n"
                     "dos elencos (ou a contagem é de antes desta conferência): os jogadores de 2026 iriam para\n"
                     "os hospedeiros errados. Rode sem --rapido: python scripts\\aplicar_tudo.py")
    if args.etapa <= 2 and not args.rapido:
        if lnc.exists():            # a contagem dos elencos é num jogo sem os nomes de 2026
            lnc.unlink()
            print(f"[OK] tirado {lnc} até a etapa 3")
        counted = counted_key(game)             # o banco que o jogo carrega nesta contagem
        need_open()
        run(2, "live_player_editor.py", "--squads-all", str(IDENTITIES), retry=True)
        COUNTED.write_text(counted + "\n")
    if args.etapa <= 3:
        need_closed()
        run(3, "montar_elencos.py")
        run(3, "aplicar_comissao.py", "--apply")
        run(3, "aplicar_arbitros.py", "--apply")
        run(3, "aplicar_historico.py", "--apply")
        run(3, "gravar_atributos.py", "--apply")
        lnc.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PLAYERS_LNC, lnc)
        print(f"[OK] copiado {PLAYERS_LNC.name} para {lnc.parent}")
    print("\n[OK] Pronto. Abra o fm_brasil.exe e comece um New Game; os testes que faltam estão em "
          "docs\\TESTES_PENDENTES.md.")


if __name__ == "__main__":
    main()
