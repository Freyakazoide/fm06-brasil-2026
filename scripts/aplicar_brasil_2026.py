"""Aplica a estrutura do futebol brasileiro de 2026 (Séries A, B, C e D).

    python scripts\\aplicar_brasil_2026.py            (simulação: mostra o que faria)
    python scripts\\aplicar_brasil_2026.py --apply    (grava tudo)
    python scripts\\aplicar_brasil_2026.py --restore  (volta o banco original, o histórico de carreira e tira o .lnc)

Com --apply:
1. cria fm_brasil.exe na pasta do jogo (cópia do fm.exe com os patches das séries);
2. grava o server_db.dat do jogo com os clubes de cada série, partindo sempre
   do original (cópia em workspace\\baseline\\server_db.original.dat), com saldo,
   público, reputação e o CT e a base da aba Estrutura da clubes_estrutura_2026.xlsx;
3. grava data\\db\\lnc\\all\\brasil_2026.lnc com os nomes Série A, B, C e D;
4. atualiza data\\brasil\\mapa_2026.csv (quem entrou no lugar de quem);
5. grava os participantes dos estaduais de 2026 (data\\brasil\\estaduais) e o
   mapa em data\\brasil\\estaduais\\mapa_estaduais_2026.csv;
6. grava a classificação de 2025 (data\\brasil\\classificacao_2025.csv) e o
   histórico real de campeões e vices (data\\brasil\\historico\\campeoes.csv: Séries
   A–D, Copa do Brasil, Libertadores, Sul-Americana e estaduais, até 2025; com
   --sem-historico, só os campeões de 2025 de Libertadores, Copa do Brasil e Série A);
7. grava o lang_db.dat com os nomes das fases e os textos (prêmios, lesões,
   descrições) em português do Brasil, pelo glossário de
   data\\modelos\\traducao_ptbr.xlsx (cópia do original em
   workspace\\baseline\\lang_db.original.dat), e as telas
   (data\\languages\\portuguese.ltc, scripts\\traduzir_telas.py);
8. põe os nomes de data\\modelos\\nomes_regens.xlsx nas tabelas de nomes do banco
   (os regens brasileiros, argentinos... nascem com nomes de hoje);
9. põe os clássicos da aba Rivais de data\\modelos\\clubes_estrutura_2026.xlsx na lista de
   rivais dos clubes (os substitutos perdem os rivais do clube de 2005);
10. grava data\\db\\brasil_2026_regens.edt com as joias da base de
    data\\modelos\\regens_futuros_2026.xlsx (FUTURE_REGEN);
11. grava data\\brasil\\clubes\\identidade_fm06.csv (clube do jogo de cada clube de
   2026), lido pelo scripts\\gerar_graficos.py (escudos, uniformes e nomes).

Depois é só abrir o fm_brasil.exe e começar um New Game.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import struct
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch.brasil_2026 import SERIES, apply as apply_db, apply_last_season, lnc_text, plan, write_report  # noqa: E402
from fm06patch.server_teams import find_brazil_teams  # noqa: E402
from fm06patch.exe_patches import EXE_SHA256, PATCHES, apply as apply_exe  # noqa: E402
from fm06patch import (campeoes, cores, estaduais_clubes, estadios, financas, historico, instalacoes,  # noqa: E402
                       identidade, nomes_fases, nomes_regens, regens_futuros, reputacao, rivais, traducao)
import aplicar_historico  # noqa: E402
import traduzir_telas  # noqa: E402

EXE_PATCHES = [
    "serie_a_calendario_copa",
    "serie_a_rebaixa_4",
    "serie_b_datas_2026",
    "serie_b_playoffs",
    "serie_b_rebaixa_4",
    "serie_c_nova",
    "serie_d_96",
    "virada_1_janeiro",
    "estaduais_2026",
    "copa_do_brasil_2026",
    "sul_americana_2026", "libertadores_vagas_2026", "libertadores_datas_2026",
    "ano_exibido_mais_20",
    "shortlist_sem_pessoa",
]
SERVER_SHA256 = "9FB7A4A2B87798120BF4D9DA9E86E7DABB99C668802B2FB9ECB035230F66BE62"
BACKUP = ROOT / "workspace" / "baseline" / "server_db.original.dat"
LANG_SHA256 = "313B5D388208389E1C97FCE8270B880BB9B95BA444FCC392AFF90474DD24EEF4"
LANG_BACKUP = ROOT / "workspace" / "baseline" / "lang_db.original.dat"
TRANSLATION = ROOT / "data" / "modelos" / "traducao_ptbr.xlsx"
REGEN_NAMES = ROOT / "data" / "modelos" / "nomes_regens.xlsx"
STRUCTURE = ROOT / "data" / "modelos" / "clubes_estrutura_2026.xlsx"   # abas Rivais e Estrutura
FUTURE_REGENS = ROOT / "data" / "modelos" / "regens_futuros_2026.xlsx"   # joias da base
TRANSLATION_REPORT = ROOT / "data" / "brasil" / "traducao_lang_db.csv"
DATA_DIR = ROOT / "data" / "brasil"
HISTORY_REPORT = DATA_DIR / "historico" / "sem_clube_no_jogo.txt"
FINANCES = DATA_DIR / "clubes" / "financas_2026.csv"


def game_dir() -> Path:
    config = ROOT / "config" / "local.json"
    return Path(json.loads(config.read_text(encoding="utf-8"))["game_dir"])


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def original_server_db(path: Path) -> bytes:
    if BACKUP.exists():
        return BACKUP.read_bytes()
    data = path.read_bytes()
    if sha256(data) != SERVER_SHA256:
        sys.exit("[ERRO] o server_db.dat do jogo não é o original e não há cópia em workspace\\baseline.")
    return data


def original_lang_db(path: Path) -> bytes | None:
    if LANG_BACKUP.exists():
        return LANG_BACKUP.read_bytes()
    data = path.read_bytes()
    if sha256(data) != LANG_SHA256:
        print("[AVISO] o lang_db.dat do jogo não é o original e não há cópia em workspace\\baseline: "
              "nomes das fases não gravados.")
        return None
    LANG_BACKUP.parent.mkdir(parents=True, exist_ok=True)
    LANG_BACKUP.write_bytes(data)
    print(f"[OK] cópia do lang_db original em {LANG_BACKUP}")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--restore", action="store_true")
    parser.add_argument("--sem-historico", action="store_true",
                        help="não reescreve o histórico de campeões (só os de 2025, como antes)")
    parser.add_argument("--sem-nomes-regens", action="store_true",
                        help="não põe os nomes de data/modelos/nomes_regens.xlsx no banco")
    parser.add_argument("--teste-copa", type=int, choices=(1, 2),
                        help="troca as datas da Série A pelo teste de pausa da Copa (exp_a_copa_1 ou _2)")
    args = parser.parse_args()
    patches = list(EXE_PATCHES)
    if args.teste_copa:
        patches[patches.index("serie_a_calendario_copa")] = f"exp_a_copa_{args.teste_copa}"

    game = game_dir()
    server = game / "data" / "db" / "server_db.dat"
    lnc = game / "data" / "db" / "lnc" / "all" / "brasil_2026.lnc"
    lang = game / "data" / "db" / "lang_db.dat"
    regens_edt = game / "data" / "db" / "brasil_2026_regens.edt"

    if args.restore:
        if BACKUP.exists():
            shutil.copy2(BACKUP, server)
            print(f"[OK] banco original restaurado em {server}")
        if LANG_BACKUP.exists():
            shutil.copy2(LANG_BACKUP, lang)
            print(f"[OK] lang_db original restaurado em {lang}")
        traduzir_telas.restore(game)
        aplicar_historico.restore(game)
        people_backup = BACKUP.with_name("people_db.original.dat")      # do reforcar_elencos.py
        if people_backup.exists():
            shutil.copy2(people_backup, game / "data" / "db" / "people_db.dat")
            print("[OK] people_db original restaurado")
        for path in (lnc, lnc.with_name("brasil_2026_clubes.lnc"),      # o 2º vem do pacote de gráficos
                     lnc.with_name("brasil_2026_comissao.lnc"), lnc.with_name("brasil_2026_arbitros.lnc"),
                     regens_edt):
            if path.exists():
                path.unlink()
                print(f"[OK] removido {path}")
        return

    data = original_server_db(server)
    taken = frozenset(estaduais_clubes.equivalents(data))     # clubes do FM06 que já são um clube de 2026
    placements = plan(data, DATA_DIR, taken)
    counts = Counter(p.serie for p in placements)
    kinds = Counter(p.kind for p in placements)
    print("Clubes por série:", {s: counts[s] for s in SERIES},
          f"({kinds['equivalente']} equivalentes, {kinds['substituto']} substitutos)")
    print("\nSubstitutos (clube de 2026 -> clube do FM06):")
    for p in placements:
        if p.kind == "substituto":
            print(f"  Série {p.serie}: {p.clube or '(vaga extra)':24} -> {p.team.short_name}")

    states, _ = estaduais_clubes.plan(data, national=placements, protect=taken)
    subs = [e for e in states if e.substitute]
    print(f"\nEstaduais 2026: {len(states)} clubes, {len(subs)} substitutos (clube que não existe no FM06):")
    for e in subs:
        print(f"  {e.uf}: {e.clube:28} -> {e.team.short_name}")

    if not args.apply:
        print("\nSimulação. Para gravar, rode de novo com --apply no fim.")
        return

    exe = game / "fm.exe"
    exe_data = exe.read_bytes()
    if sha256(exe_data) != EXE_SHA256:
        sys.exit(f"[ERRO] {exe} não é o fm.exe 6.0.2 original.")
    target = game / "fm_brasil.exe"
    target.write_bytes(apply_exe(exe_data, patches))
    print(f"\n[OK] criado {target}")
    for name in patches:
        print(f"     + {name}")

    if not BACKUP.exists():
        BACKUP.parent.mkdir(parents=True, exist_ok=True)
        BACKUP.write_bytes(data)
        print(f"[OK] cópia do banco original em {BACKUP}")
    db, missing = apply_last_season(apply_db(data, placements), placements, DATA_DIR / "classificacao_2025.csv")
    if missing:
        print("[AVISO] classificação 2025: clubes que não estão nas séries de 2026:", ", ".join(missing))
    db = estaduais_clubes.apply(db, states)
    if args.sem_historico:
        db, notes = historico.apply(db)
        for note in notes:
            print(f"[OK] campeões 2025: {note}")
    changes = reputacao.plan(placements, states)
    db = reputacao.apply(db, changes)
    print(f"[OK] reputação de {len(changes)} substitutos ajustada (ex.: "
          + ", ".join(f"{c} {a}->{b}" for a, b, c in list(changes.values())[:3]) + ")")
    identities = identidade.build(data, placements, states)
    db, painted = cores.apply(db, cores.plan(identities))
    print(f"[OK] cores de 2026 (tela do clube e uniforme da partida) em {painted} substitutos")
    teams_by_repo = {p.team.club_uid: p.team.offset for p in placements}
    teams_by_repo.update({e.team.club_uid: e.team.offset for e in states})
    sheet = next((x for x in (DATA_DIR / "clubes" / "estadios_2026.xlsx", DATA_DIR / "clubes" / "estadios_2026_modelo.xlsx")
                  if x.exists()), None)
    wanted, sheet_reputation = estadios.wanted_from_sheets(identities, teams_by_repo,
                                                           DATA_DIR / "clubes" / "estadios_sofascore.csv", sheet)
    ours = {i.repo_uid for i in identities}
    others = [t.offset for t in find_brazil_teams(data) if t.club_uid not in ours]
    keep = [teams_by_repo[i.repo_uid] for i in identities
            if i.repo_uid in teams_by_repo and teams_by_repo[i.repo_uid] not in {w.team_offset for w in wanted}]
    venues = estadios.plan(data, original_lang_db(lang) or b"", wanted, others, keep)
    db = estadios.apply(db, venues)
    print(f"[OK] estádios de 2026: {len(venues.stadium_names)} nomes, {len(venues.capacity)} capacidades, "
          f"{len(venues.team_stadium)} clubes trocam de estádio, {len(venues.stadium_city)} cidades")
    for line in venues.report:
        if "sem estádio" in line:
            print("[AVISO]", line)
    by_uid = {i.uid: i.repo_uid for i in identities}
    buffer = bytearray(db)
    for uid, value in sheet_reputation.items():                 # reputação da planilha de estádios
        if by_uid.get(uid) in teams_by_repo:
            struct.pack_into("<H", buffer, teams_by_repo[by_uid[uid]] + 3, max(1, min(10000, value)))
    db = bytes(buffer)
    if sheet_reputation:
        print(f"[OK] reputação da planilha em {len(sheet_reputation)} clubes")
    if FINANCES.exists():                                        # saldo e público de 2026
        by_name = {i.clube: i.repo_uid for i in identities}
        money = {}
        for row in csv.DictReader(FINANCES.open(encoding="utf-8-sig")):
            if row["clube"] in by_name and (row["saldo_rs"] or row["publico_medio"]):
                money[by_name[row["clube"]]] = (float(row["saldo_rs"]) if row["saldo_rs"] else None,
                                                int(float(row["publico_medio"])) if row["publico_medio"] else None)
        skipped = []
        for repo_uid in list(money):
            try:
                financas.read(data, financas.record_start(data, repo_uid))
            except ValueError:
                skipped.append(repo_uid)
                money.pop(repo_uid)
        db = financas.apply(data, money, into=db)
        print(f"[OK] saldo de 2026 em {len(money)} clubes, público médio em "
              f"{sum(1 for _, crowd in money.values() if crowd)}" + (f" ({len(skipped)} sem registro legível)" if skipped else ""))
    if STRUCTURE.exists():                                       # CT e base (aba Estrutura)
        by_name = {i.clube: i.repo_uid for i in identities}
        wanted = {by_name[club]: values for club, values in instalacoes.load_sheet(STRUCTURE).items()
                  if club in by_name and any(v is not None for v in values)}
        capped = []
        for repo_uid, (_, youth, recruitment) in wanted.items():
            if repo_uid in teams_by_repo:           # o jogo limita a base a reputação / 250
                limit = struct.unpack_from("<H", db, teams_by_repo[repo_uid] + 3)[0] // 250
                if max(youth or 0, recruitment or 0) > limit:
                    capped.append(f"{next(c for c, u in by_name.items() if u == repo_uid)} ({limit})")
        db = instalacoes.apply(data, wanted, into=db)
        print(f"[OK] CT, base e captação de 2026 em {len(wanted)} clubes")
        if capped:
            print("[CONFIRA] base acima de reputação/250, o jogo deve baixar para o número entre parênteses: "
                  + ", ".join(capped))
    db, cleared = historico.clear_brazil_continental(db)
    if cleared:
        print("[OK] vaga continental do banco original retirada:", ", ".join(cleared))
    if not args.sem_historico:                                   # por último: muda o tamanho do arquivo
        print("Reescrevendo o histórico de campeões...", flush=True)
        db, history = campeoes.rewrite(data, identities, into=db)
        for line in history.lines:
            print("     ", line)
        print(f"[OK] histórico: {history.reused} registros órfãos reaproveitados, {history.appended} novos; "
              f"{len(history.unmatched)} times sem clube no jogo ficam em branco "
              f"(lista em {HISTORY_REPORT.relative_to(ROOT)})")
        HISTORY_REPORT.write_text("\n".join(history.unmatched) + "\n", encoding="utf-8")
    if REGEN_NAMES.exists() and not args.sem_nomes_regens:      # nomes dos regens (muda o tamanho)
        starts = nomes_regens.locate(db, data)
        changes = nomes_regens.plan(db, nomes_regens.load_sheet(REGEN_NAMES), starts)
        db = nomes_regens.apply(db, changes, starts)
        print(f"[OK] nomes de regens: {sum(len(a) for _, a in changes.values())} novos e "
              f"{sum(len(u) for u, _ in changes.values())} que já existiam com peso maior "
              f"({REGEN_NAMES.relative_to(ROOT)})")
    if STRUCTURE.exists():                                       # rivais e clássicos (muda o tamanho)
        clubs = rivais.read(db)
        uid_of = {i.clube: i.uid for i in identities}
        fm06 = {c.name: uid for uid, c in clubs.items() if uid not in set(uid_of.values())}
        pairs, missing = rivais.load_sheet(STRUCTURE, uid_of, fm06)
        changes = rivais.plan(clubs, pairs, {i.uid for i in identities if i.tipo == "substituto"})
        db = rivais.apply(db, clubs, changes)
        print(f"[OK] rivais: {len(pairs)} clássicos da aba Rivais; {len(changes)} clubes com a lista de rivais "
              "nova (os substitutos perdem os rivais do clube de 2005)")
        if missing:
            print("[AVISO] rivais: clubes da planilha que não estão no jogo:", ", ".join(missing))
    server.write_bytes(db)
    print(f"[OK] gravado {server}")

    lang_data = original_lang_db(lang)
    if lang_data is not None:
        lang_new, renamed = nomes_fases.apply(lang_data)
        translated = 0
        if TRANSLATION.exists():                                 # glossário pt-PT -> pt-BR
            sheet = traducao.load_sheet(TRANSLATION)
            changes, too_long = traducao.plan(lang_new, sheet.glossary(), sheet.phrases, sheet.short_phrases)
            lang_new = traducao.apply(lang_new, changes)
            translated = len(changes)
            with TRANSLATION_REPORT.open("w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle, lineterminator="\n")
                writer.writerow(["antes", "depois"])
                writer.writerows(sorted({(c.old, c.new) for c in changes}))
                writer.writerows([(line, "NÃO COUBE") for line in too_long])
        lang.write_bytes(lang_new)
        print(f"[OK] gravado {lang} (nomes das fases: {len(renamed)} trocados; "
              f"{translated} textos em pt-BR, lista em {TRANSLATION_REPORT.relative_to(ROOT)})")
    traduzir_telas.translate(game, apply=True)                   # telas (portuguese.ltc)

    lnc.parent.mkdir(parents=True, exist_ok=True)
    lnc.write_bytes((lnc_text() + "\r\n".join(estadios.lnc_lines(venues)) + "\r\n").encode("utf-16"))
    (DATA_DIR / "clubes" / "estadios_2026_relatorio.txt").write_text("\n".join(venues.report) + "\n", encoding="utf-8")
    print(f"[OK] gravado {lnc}")
    prospects = regens_futuros.load_sheet(FUTURE_REGENS) if FUTURE_REGENS.exists() else []
    if prospects:                                                # joias da base (FUTURE_REGEN)
        text, warnings = regens_futuros.edt_text(prospects, {i.clube: i.uid for i in identities})
        regens_edt.write_bytes(text.encode("cp1252", errors="replace"))     # .edt é texto ANSI
        count = sum(line.startswith('"FUTURE_REGEN"') for line in text.splitlines())
        print(f"[OK] joias da base: {count} regens em {regens_edt}")
        for warning in warnings:
            print("[AVISO] joias da base:", warning)
    elif regens_edt.exists():
        regens_edt.unlink()

    write_report(DATA_DIR / "mapa_2026.csv", placements)
    print(f"[OK] lista completa em {DATA_DIR / 'mapa_2026.csv'}")
    report = DATA_DIR / "estaduais" / "mapa_estaduais_2026.csv"
    estaduais_clubes.write_report(report, states)
    print(f"[OK] estaduais: lista completa em {report}")
    report = DATA_DIR / "clubes" / "identidade_fm06.csv"
    identidade.write_report(report, identities)
    print(f"[OK] clube do jogo de cada clube de 2026 (escudos, uniformes, nomes) em {report}")


if __name__ == "__main__":
    main()
