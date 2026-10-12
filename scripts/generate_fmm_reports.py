from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "reverse" / "fmm"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_fmm_live import analyze  # noqa: E402
from fm06patch.fmm_schema import FMM2_DEFAULT, describe_schema  # noqa: E402


SAVIOLA_UID = 3100367
SAVIOLA_SNAPSHOT = (
    ROOT / "workspace" / "live_memory" / str(SAVIOLA_UID) / "saviola_original.json"
)
MANUAL_BASELINE = (
    ROOT
    / "workspace"
    / "live_memory"
    / str(SAVIOLA_UID)
    / "fmm_batch_player_baseline.json"
)
MANUAL_OBSERVED = (
    ROOT
    / "workspace"
    / "live_memory"
    / str(SAVIOLA_UID)
    / "manual_changes_observed_20261012.json"
)


MANUAL_CONFIRMED_PLAYING = {
    "Crossing": "raw 247→16 e depois 16→12",
    "Dribbling": "raw 20→18 entre as duas capturas da rodada",
    "Penalty": "raw 81→15 e depois 15→16",
    "Creativity": "raw 252→17 e depois 17→19",
    "Aggression": "raw 20→5 e depois 5→4",
    "Att. Mid.": "17→16",
    "Attacker": "20→19",
    "Finishing": "raw 247→246 em alteração isolada",
    "Anticipation": "raw 252→251 em alteração isolada",
    "Acceleration": "raw 96→97 em alteração isolada; direção da escala ainda não resolvida",
    "Pace": "raw 86→85 em alteração isolada",
    "Left foot": "raw 56→55 em alteração isolada",
    "Handling": "raw 186→187 em alteração isolada",
}


def write_json(name: str, value) -> None:
    (OUTPUT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_csv(name: str, rows: list[dict]) -> None:
    path = OUTPUT / name
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as target:
        writer = csv.DictWriter(target, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def personal_layout() -> list[dict]:
    rows = [
        ("Nationality", "Player", 64, "pointer -> Nation record", "CONFIRMED", "Diff Argentina UID 1649→Espanha UID 796 trocou o ponteiro entre os dois objetos Nation válidos."),
        ("Born", "Player", 52, "Date {u16 day_of_year_0, u16 year}", "CONFIRMED", "11/12/1981→12/12/1981 alterou dia 344→345 em UID+52."),
        ("Value", "Player", None, None, "UNRESOLVED", "Candidato u32 em UID-196 apareceu apenas numa alteração acidental da restauração; não promovido."),
        ("Ask Value", "Player", -192, "u32", "CONFIRMED", "Alteração isolada 6350936→6350937."),
        ("Current Ability", "Player", -204, "u16", "CONFIRMED", "Saviola 160→161; mesmo offset em Zidane, Ceni, Sávio e Fred."),
        ("Potential Ability", "Player", -202, "u16", "CONFIRMED", "Saviola 179→178; mesmo offset estrutural nos demais âncoras."),
        ("Height", "Player", -76, "u16", "CONFIRMED", "Diff manual Saviola 168→169; Zidane 185 no mesmo offset."),
        ("Weight", "Player", -78, "u16", "CONFIRMED", "Diff manual Saviola 61→62; Zidane 80 no mesmo offset."),
        ("Home Rep.", "Player", -210, "u16", "CONFIRMED", "Diff manual Saviola 8198→8197."),
        ("Current Rep.", "Player", -208, "u16", "CONFIRMED", "Diff manual Saviola 7998→7997."),
        ("World Rep.", "Player", -206, "u16", "CONFIRMED", "Diff manual Saviola 5862→5861."),
        ("Int. Caps", "Player", 72, "u8", "HIGH", "Saviola 29 e Zidane 95 exatos na ficha viva."),
        ("Int. Goals", "Player", 74, "u8", "HIGH", "Saviola 1 e Zidane 26 exatos na ficha viva."),
        ("U21 Caps", "Player", 73, "u8", "CONFIRMED", "Alteração isolada 0→1 em UID+73."),
        ("U21 Goals", "Player", 75, "u8", "CONFIRMED", "Alteração isolada 0→1 em UID+75."),
        ("Morale", "Player", -184, "u8", "CONFIRMED", "Diff manual Saviola 20→19."),
        ("Fitness", "Player", -216, "u16", "CONFIRMED", "Diff manual Saviola 4000→3999."),
        ("Jadedness", "Player", -212, "u16", "CONFIRMED", "Diff manual Saviola 0→1."),
        ("Match Exercise", "Player", -214, "u16", "CONFIRMED", "Diff manual Saviola 7080→7079."),
        ("Adaptability", "PData", 8, "u8", "CONFIRMED", "Diff manual Saviola 12→13; sequência PData coerente."),
        ("Ambition", "PData", 9, "u8", "HIGH", "Sequência FMM completa."),
        ("Loyalty", "PData", 10, "u8", "HIGH", "Sequência FMM completa; FMM também contém typo Loyality."),
        ("Pressure", "PData", 11, "u8", "HIGH", "Sequência FMM completa."),
        ("Professional", "PData", 12, "u8", "HIGH", "Sequência FMM completa."),
        ("Sportsmanship", "PData", 13, "u8", "HIGH", "Sequência FMM completa."),
        ("Temperament", "PData", 14, "u8", "HIGH", "Sequência FMM completa."),
        ("Controversy", "PData", 15, "u8", "HIGH", "Sequência FMM completa."),
    ]
    return [
        {
            "field": field,
            "object": obj,
            "relative_to_object_uid": relative,
            "type": kind,
            "confidence": confidence,
            "evidence": evidence,
        }
        for field, obj, relative, kind, confidence, evidence in rows
    ]


def table(rows: list[dict], columns: list[tuple[str, str]]) -> str:
    header = "| " + " | ".join(label for _, label in columns) + " |"
    divider = "|" + "|".join("---" for _ in columns) + "|"
    body = []
    for row in rows:
        body.append(
            "| "
            + " | ".join(
                ("" if row.get(key) is None else str(row.get(key, ""))).replace("|", "\\|")
                for key, _ in columns
            )
            + " |"
        )
    return "\n".join([header, divider, *body])


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    schema = describe_schema(FMM2_DEFAULT)
    live = analyze(SAVIOLA_SNAPSHOT, FMM2_DEFAULT)
    manual_baseline = analyze(MANUAL_BASELINE, FMM2_DEFAULT)
    manual_observed = analyze(MANUAL_OBSERVED, FMM2_DEFAULT)
    personal = personal_layout()

    manual_changes = [
        {"object": "Player", "field": "Height", "offset": -76, "type": "u16", "before": 168, "after": 169},
        {"object": "Player", "field": "Weight", "offset": -78, "type": "u16", "before": 61, "after": 62},
        {"object": "Player", "field": "Home Rep.", "offset": -210, "type": "u16", "before": 8198, "after": 8197},
        {"object": "Player", "field": "Current Rep.", "offset": -208, "type": "u16", "before": 7998, "after": 7997},
        {"object": "Player", "field": "World Rep.", "offset": -206, "type": "u16", "before": 5862, "after": 5861},
        {"object": "Player", "field": "Morale", "offset": -184, "type": "u8", "before": 20, "after": 19},
        {"object": "Player", "field": "Fitness", "offset": -216, "type": "u16", "before": 4000, "after": 3999},
        {"object": "Player", "field": "Jadedness", "offset": -212, "type": "u16", "before": 0, "after": 1},
        {"object": "Player", "field": "Match Exercise", "offset": -214, "type": "u16", "before": 7080, "after": 7079},
        {"object": "PData", "field": "Adaptability", "offset": 8, "type": "u8", "before": 12, "after": 13},
        {"object": "Playing", "field": "Crossing", "offset": 33, "type": "u8", "before": 247, "after": 16},
        {"object": "Playing", "field": "Penalty", "offset": 41, "type": "u8", "before": 81, "after": 15},
        {"object": "Playing", "field": "Creativity", "offset": 43, "type": "u8", "before": 252, "after": 17},
        {"object": "Playing", "field": "Aggression", "offset": 78, "type": "u8", "before": 20, "after": 5},
        {"object": "Playing", "field": "Att. Mid.", "offset": 13, "type": "u8", "before": 17, "after": 16},
        {"object": "Playing", "field": "Attacker", "offset": 14, "type": "u8", "before": 20, "after": 19},
        {"object": "Playing", "field": "Dribbling", "offset": 34, "type": "u8", "before": 20, "after": 18},
        {
            "object": "Contract(main)",
            "field": "Wages",
            "offset": 16,
            "type": "tagged u32: value*10+2",
            "before": 650000,
            "after": 650001,
            "encoded_before": 6500002,
            "encoded_after": 6500012,
        },
    ]
    for row in manual_changes:
        row["delta"] = row["after"] - row["before"]
        row["confidence"] = "CONFIRMED"
    write_json(
        "manual_change_observations.json",
        {
            "original_snapshot": str(SAVIOLA_SNAPSHOT.relative_to(ROOT)),
            "batch_entry_snapshot": str(MANUAL_BASELINE.relative_to(ROOT)),
            "observed_snapshot": str(MANUAL_OBSERVED.relative_to(ROOT)),
            "note": "A captura de entrada já continha alterações acumuladas. Os pares abaixo só incluem mudanças atribuíveis sem ambiguidade a campos mapeados pelo FMM2.",
            "changes": manual_changes,
            "batch_entry_decoded": manual_baseline,
            "observed_decoded": manual_observed,
        },
    )
    write_csv("manual_change_observations.csv", manual_changes)

    player_payload = {
        "schema": "fm06-live-player-layout-v1",
        "target_build": "6.0.2f72973",
        "fmm_source": {"path": schema["source"], "sha256": schema["sha256"]},
        "target_fmm_row": 3,
        "objects": {
            "Player": {
                "record_stride": 456,
                "uid_relative_to_record_start": 224,
                "root_signature_relative_to_uid": -20,
                "root_signature": [f"0x{x:08X}" for x in schema["roots"]["Player"][:5]],
                "confidence": "CONFIRMED",
            },
            "PData": {
                "record_stride": 36,
                "uid_relative_to_record_start": 20,
                "root_signature_relative_to_uid": -20,
                "root_signature": [f"0x{x:08X}" for x in schema["roots"]["PData"]],
                "confidence": "HIGH",
            },
            "Playing": {
                "record_stride": 112,
                "uid_relative_to_record_start": 20,
                "root_signature_relative_to_uid": -20,
                "root_signature": [f"0x{x:08X}" for x in schema["roots"]["Playing"]],
                "confidence": "HIGH",
            },
        },
        "personal_info": personal,
        "observed_saviola": live,
    }
    write_json("player_live_layout.json", player_payload)
    write_csv("player_live_layout.csv", personal)

    playing = live["playing_attributes"]
    for row in playing:
        row["offset_confidence"] = row.pop("confidence")
        if row["field"] in MANUAL_CONFIRMED_PLAYING:
            row["offset_confidence"] = "CONFIRMED"
        row["value_transform_confidence"] = (
            "HIGH" if row["fmm_index"] >= 54 else "LOW"
        )
        if row["field"] in MANUAL_CONFIRMED_PLAYING:
            row["evidence"] = (
                "Diff manual no offset previsto: "
                + MANUAL_CONFIRMED_PLAYING[row["field"]]
                + "."
            )
            row["fmm_write_encoding"] = "DIRECT_U8_OBSERVED"
            row["fmm_write_encoding_confidence"] = "CONFIRMED"
        else:
            row["evidence"] = (
                "Offset = UID+8+Playing Position[index]; assinatura Playing e permutação explícita no FMM2."
            )
            row["fmm_write_encoding"] = None
            row["fmm_write_encoding_confidence"] = "UNRESOLVED"
    write_json(
        "playing_attributes_layout.json",
        {
            "record_size": 112,
            "uid_offset": 20,
            "attribute_storage_start_relative_to_uid": 8,
            "attribute_count": 79,
            "storage_width": "u8",
            "note": "Offsets estão mapeados. A transformação de raw 0..255 para 1..20 ainda exige diffs controlados para os campos não posicionais.",
            "fields": playing,
        },
    )

    contract = [
        {
            "fmm_index": index,
            "field": field,
            "object": "Contract",
            "relative_offset": None,
            "type": None,
            "confidence": "UNRESOLVED",
            "evidence": "Registro ligado ao jogador; este campo específico ainda não produziu diff controlado confiável.",
        }
        for index, field in enumerate(schema["contract_info"])
    ]
    contract_known = {
        "Club": {
            "relative_offset": 8,
            "type": "pointer -> Club record",
            "confidence": "HIGH",
            "evidence": "Barcelona/Sevilla/Real Madrid/São Paulo/Zaragoza/Lyon resolvem para Club UID+20.",
        },
        "Wages": {
            "relative_offset": 16,
            "type": "tagged u32: value*10+2",
            "confidence": "CONFIRMED",
            "evidence": "Edição 650001 produziu 6500012 no contrato principal de Saviola.",
        },
        "Started": {
            "relative_offset": 24,
            "type": "Date {u16 day_of_year_0, u16 year}",
            "confidence": "CONFIRMED",
            "evidence": "Datas exatas em quatro jogadores e diff isolado de +1 dia no contrato principal de Saviola.",
        },
        "Expires": {
            "relative_offset": 32,
            "type": "Date {u16 day_of_year_0, u16 year}",
            "confidence": "CONFIRMED",
            "evidence": "Datas exatas em quatro jogadores e diff isolado de +1 dia no contrato principal de Saviola.",
        },
        "Squad Status": {
            "relative_offset": 37,
            "type": "enum u8",
            "confidence": "CONFIRMED",
            "evidence": "Mudança isolada de opção gravou 4→5 em +37.",
        },
        "Transfer": {
            "relative_offset": 38,
            "type": "flags u8 (semântica dos bits parcial)",
            "confidence": "CONFIRMED",
            "evidence": "Alternância isolada mudou o byte +38 de 0x04 para 0x01; a codificação completa segue parcial.",
        },
        "Loan": {
            "relative_offset": 38,
            "type": "flags u8; bit 1 observado",
            "confidence": "CONFIRMED",
            "evidence": "Alternância isolada mudou +38 de 0x01 para 0x03 (xor 0x02).",
        },
        "Happiness": {
            "relative_offset": 48,
            "type": "u8",
            "confidence": "CONFIRMED",
            "evidence": "Alteração isolada 41→42 em +48.",
        },
        "Squad Number": {
            "relative_offset": 49,
            "type": "u8; 0xFF = ausente, transformação de entrada pendente",
            "confidence": "CONFIRMED",
            "evidence": "Entrada 0 no FMM alterou +49 de 0xFF para 0x01; offset confirmado, escala de interface não.",
        },
        "Apears": {
            "relative_offset": 76,
            "type": "u32",
            "confidence": "CONFIRMED",
            "evidence": "Alteração isolada 0→1 em +76.",
        },
        "Goal": {
            "relative_offset": 80,
            "type": "u32",
            "confidence": "CONFIRMED",
            "evidence": "Alteração isolada 2757→2758 em +80.",
        },
        "Assist": {
            "relative_offset": 84,
            "type": "u32",
            "confidence": "CONFIRMED",
            "evidence": "Alteração isolada 1390→1391 em +84.",
        },
        "Clean Sheet": {
            "relative_offset": 88,
            "type": "u32",
            "confidence": "CONFIRMED",
            "evidence": "Alteração isolada 0→1 em +88.",
        },
        "Agreed Price": {
            "relative_offset": 56,
            "type": "signed u32; -1 = ausente",
            "confidence": "CONFIRMED",
            "evidence": "No contrato de empréstimo, alteração isolada gravou -1→1 em +56.",
        },
    }
    for row in contract:
        if row["field"] in contract_known:
            row.update(contract_known[row["field"]])
    write_json(
        "contract_live_layout.json",
        {
            "roots": [f"0x{x:08X}" for x in schema["roots"]["Contract"]],
            "record_variants": [
                {"root": "0x00EB3954", "record_size": 120, "role": "main contract", "confidence": "HIGH"},
                {"root": "0x010BAAD4", "record_size": 72, "role": "loan contract", "confidence": "HIGH"},
            ],
            "common_linkage": {
                "player_pointer_offset": 4,
                "player_pointer_target": "Player UID-20",
                "club_pointer_offset": 8,
                "club_pointer_target": "Club record start (public UID at +20)",
                "confidence": "HIGH",
            },
            "observed_candidate_arrays": [
                {"root": "0x00EB3954", "candidate_stride": 120, "hits": 9712},
                {"root": "0x010BAAD4", "candidate_stride": 72, "hits": 584},
            ],
            "fields": contract,
        },
    )

    known_active = {
        0: "Corre Com Bola Pela Esquerda",
        6: "Joga Curto e Simples",
        10: "Remata Em Jeito",
        12: "Gosta de Rodear G-Redes",
        13: "Gosta de Jogar No Limite do Fora-de-Jogo",
        29: "Mete Bola No Pé Esquerdo Antes De Ir Para A Finta",
        39: "Vem Para Dentro",
        47: "Troca de Flancos",
    }
    moves = []
    tested_moves = {0, 1, 31, 47}
    for index, field in enumerate(schema["preferred_moves"]):
        moves.append(
            {
                "fmm_index": index,
                "move_name": field,
                "storage_type": "48-bit bitset in Player",
                "byte_offset": -48 + index // 8,
                "bit": index % 8,
                "confidence": "CONFIRMED" if index in tested_moves else "HIGH",
                "evidence": (
                    "Diff controlado neste índice."
                    if index in tested_moves
                    else "Interpolação estrutural do bitset confirmada nos índices 0, 1, 31 e 47."
                ),
                "saviola_visible_active": index in known_active,
                "visible_portuguese": known_active.get(index),
            }
        )
    write_json(
        "preferred_moves_layout.json",
        {
            "count": 48,
            "bitset_start_relative_to_player_uid": -48,
            "bit_order": "LSB-first dentro de cada byte",
            "note": "A representação física foi resolvida por diffs nos índices 0, 1, 31 e 47. Dois textos portugueses visíveis continuam semanticamente ambíguos, mas isso não afeta o mapa de bits.",
            "ambiguous_visible_moves": ["Desarma Adversários", "Cai Ao Mínimo Toque"],
            "moves": moves,
        },
    )

    club = [
        {
            "fmm_index": index,
            "field": field,
            "relative_offset": None,
            "type": None,
            "confidence": "UNRESOLVED",
        }
        for index, field in enumerate(schema["club_info"])
    ]
    for row in club:
        if row["field"] == "Cash":
            row.update(
                {
                    "relative_offset": 248,
                    "type": "u32",
                    "confidence": "CONFIRMED",
                    "evidence": "Sevilla UID 1759: alteração isolada 55000→55001 em +248.",
                }
            )
    write_json(
        "club_live_layout.json",
        {
            "roots": [f"0x{x:08X}" for x in schema["roots"]["Club"]],
            "object_layout": {
                "record_size": 440,
                "root_signature_offset": 0,
                "public_uid_offset": 20,
                "internal_ordinal_offset": 24,
                "confidence": "HIGH",
                "evidence": "São Paulo 337, Lyon 865, Barcelona 1708, Real Madrid 1736, Zaragoza 1749 e Sevilla 1759.",
            },
            "fields": club,
            "database_crosscheck": [
                {"club": "São Paulo", "public_uid": 337, "field_a": 212, "field_b": 336, "nation_internal_id": 189},
                {"club": "Lyon", "public_uid": 865, "field_a": 589, "field_b": 864, "nation_internal_id": 143},
                {"club": "Real Madrid", "public_uid": 1736, "field_a": 1313, "field_b": 1733, "nation_internal_id": 170},
                {"club": "Zaragoza", "public_uid": 1749, "field_a": 1324, "field_b": 1746, "nation_internal_id": 170},
            ],
        },
    )

    nation = [
        {
            "fmm_index": index,
            "field": field,
            "relative_offset": None,
            "type": None,
            "confidence": "UNRESOLVED",
        }
        for index, field in enumerate(schema["nation_info"])
    ]
    nation_known = {
        "League Standard": {
            "relative_offset": [230, 231],
            "type": "candidate u8 pair",
            "confidence": "LOW",
            "evidence": "O passo alterou simultaneamente +230 1→2 e +231 13→14; não há atribuição inequívoca.",
        },
        "Development": {
            "relative_offset": 228,
            "type": "u8",
            "confidence": "CONFIRMED",
            "evidence": "Argentina UID 1649: alteração isolada 2→1 em +228.",
        },
        "Economic Factor": {
            "relative_offset": 233,
            "type": "u8",
            "confidence": "CONFIRMED",
            "evidence": "Argentina UID 1649: alteração isolada 16→17 em +233; direção da escala da interface requer cautela.",
        },
        "Reputation": {
            "relative_offset": 252,
            "type": "u16",
            "confidence": "CONFIRMED",
            "evidence": "Argentina UID 1649: alteração isolada 9000→8999 em +252.",
        },
    }
    for row in nation:
        if row["field"] in nation_known:
            row.update(nation_known[row["field"]])
    write_json(
        "nation_live_layout.json",
        {
            "roots": [f"0x{x:08X}" for x in schema["roots"]["Nation"]],
            "object_layout": {
                "record_size": 700,
                "root_signature_offset": 0,
                "public_uid_offset": 20,
                "internal_ordinal_offset": 24,
                "confidence": "HIGH",
            },
            "fields": nation,
            "known_namespaces": {
                "internal_ids": {"Brasil": 189, "França": 143, "Espanha": 170, "Argentina": 187},
                "public_uids": {"Brasil": 1651, "França": 769, "Espanha": 796, "Argentina": 1649},
            },
        },
    )

    confirmed_personal = sum(row["confidence"] == "CONFIRMED" for row in personal)
    confirmed_playing = sum(
        row["offset_confidence"] == "CONFIRMED" for row in playing
    )
    high_personal = sum(row["confidence"] == "HIGH" for row in personal)
    high_playing = sum(row["offset_confidence"] == "HIGH" for row in playing)
    confirmed_contract = sum(row["confidence"] == "CONFIRMED" for row in contract)
    confirmed_moves = sum(row["confidence"] == "CONFIRMED" for row in moves)
    confirmed_club = sum(row["confidence"] == "CONFIRMED" for row in club)
    confirmed_nation = sum(row["confidence"] == "CONFIRMED" for row in nation)
    unresolved = (
        sum(row["confidence"] == "UNRESOLVED" for row in personal)
        + sum(row["confidence"] == "UNRESOLVED" for row in contract)
        + sum(row["confidence"] == "UNRESOLVED" for row in moves)
        + sum(row["confidence"] == "UNRESOLVED" for row in club)
        + sum(row["confidence"] == "UNRESOLVED" for row in nation)
    )

    schema_md = f"""# FMM2 6.0.2f72973 — schema vivo preliminar

## Resumo

Campos confirmados: {confirmed_personal} campos pessoais, {confirmed_playing} offsets Playing, {confirmed_contract} campos de contrato, {confirmed_moves} bits de Preferred Moves, {confirmed_club} campo de clube, {confirmed_nation} campos de nação e a seleção da terceira linha de raízes do FMM2.

Campos high confidence: {high_personal + high_playing} entradas adicionais. A transformação numérica de leitura não está confirmada para todos os atributos Playing.

Campos unresolved: {unresolved} entradas explícitas nos artefatos.

Hipóteses rejeitadas: endereços absolutos estáveis; primeira ocorrência do UID; PA de database menos 1; UID público igual a ID interno de clube/nação; ano literal como formato de contrato.

## Fonte e build

- FMM usado: `{schema['source']}`
- SHA-256: `{schema['sha256']}`
- Build: `fm.exe` 6.0.2f72973
- Linha ativa: terceira linha (índice 2). A prova é estrutural: os marcadores `[Player]` `010F1034 010F1020 010F0FF8 010F0FEC 010F0FD8` aparecem consecutivos em `UID-20..UID-4`, e `010F12F4 010F14CC` em `UID-224..UID-220`.

## Player object

Stride observado: 456 bytes. O UID fica em `record_start+224`. Não usar endereço absoluto.

{table([row for row in personal if row['object'] == 'Player'], [('field','Campo'),('relative_to_object_uid','Offset relativo ao UID'),('type','Tipo'),('evidence','Evidência'),('confidence','Confiança')])}

## Personal Info / PData

O registro PData tem stride 36, assinatura de 20 bytes, UID em `+20` e oito bytes de personalidade em `UID+8..+15`.

{table([row for row in personal if row['object'] == 'PData'], [('field','Campo'),('relative_to_object_uid','Offset relativo ao UID PData'),('type','Tipo'),('evidence','Evidência'),('confidence','Confiança')])}

## Playing attributes

O registro Playing tem stride 112, assinatura em `UID-20..-4` e 79 bytes em `UID+8..UID+86`. A ordem lógica é resolvida pela permutação `[Playing Position]` do FMM2. Cada linha está em `playing_attributes_layout.json`.

Os campos posicionais (índices FMM 54–78) aparecem diretamente em escala 1–20. Os atributos restantes incluem valores raw 0–255. A rodada manual confirmou que o FMM2 grava um literal u8 nos campos editados, mas a transformação dos valores originais carregados do save continua sem fórmula geral.

{table(playing, [('fmm_index','Índice FMM'),('field','Campo'),('storage_index','Índice físico'),('relative_to_playing_uid','Offset UID'),('type','Tipo'),('raw_value','Raw Saviola'),('offset_confidence','Confiança offset')])}

## Contract

As raízes `00EB3954` e `010BAAD4` formam registros de 120 bytes (contrato principal) e 72 bytes (empréstimo). Em ambos, `+4` aponta para `Player UID-20` e `+8` aponta para o início do objeto Club. O contrato principal e o empréstimo de Saviola foram ligados sem depender de endereço absoluto.

`Started` e `Expires` ficam em `+24` e `+32`, como `{{u16 dia_do_ano_base_zero, u16 ano}}`. O cruzamento reproduz exatamente datas de Zidane, Ceni, Sávio e Saviola, e os diffs de um dia confirmaram ambos. `Wages` fica em `+16`; a edição manual 650001 foi gravada como o tagged integer `650001*10+2 = 6500012`. Os testes 17–28 foram aplicados ao contrato principal do Barcelona apesar do roteiro mencionar Sevilla; a ligação do ponteiro de clube torna esse desvio explícito e os diffs isolados continuam válidos para o layout comum.

{table(contract, [('fmm_index','Índice FMM'),('field','Campo'),('relative_offset','Offset'),('type','Tipo'),('confidence','Confiança')])}

## Preferred Moves

Os 48 nomes foram preservados em ordem. O armazenamento é um bitset de 48 bits em `Player UID-48..UID-43`, LSB-first. Os índices 0, 1, 31 e 47 tiveram diffs controlados; os demais bits são interpolação estrutural `HIGH`. Dois textos portugueses visíveis continuam semanticamente ambíguos, sem afetar o mapa físico.

{table(moves, [('fmm_index','Índice FMM'),('move_name','Movimento'),('byte_offset','Offset'),('bit','Bit'),('confidence','Confiança')])}

## Club / Nation

Club usa registros de 440 bytes e Nation de 700 bytes. Em ambos, a assinatura começa em `+0`, o UID público fica em `+20` e o ordinal interno em `+24`. Os namespaces continuam separados. Em RAM foram confirmados, entre outros, Barcelona 1708/411, Sevilla 1759/429, Argentina 1649/187 e Brasil 1651/189. Em Club, Cash foi confirmado em `+248`. Em Nation, Development, Economic Factor e Reputation foram confirmados; League Standard ficou com dois candidatos adjacentes e confiança baixa.

### Club Info

{table(club, [('fmm_index','Índice FMM'),('field','Campo'),('relative_offset','Offset'),('type','Tipo'),('confidence','Confiança')])}

### Nation Info

{table(nation, [('fmm_index','Índice FMM'),('field','Campo'),('relative_offset','Offset'),('type','Tipo'),('confidence','Confiança')])}

## Relação com database

| Campo | RAM | people_db/server_db/client_db | Relação | Confiança |
|---|---|---|---|---|
| Current Ability | Player UID-204 u16 | people_db UID+15 u16 | RUNTIME_MUTATED | HIGH |
| Potential Ability | Player UID-202 u16 | people_db UID+17 u16 | RUNTIME_MUTATED | HIGH |
| Reputações | Player UID-210/-208/-206 u16 | people_db UID+9/+11/+13 u16 | UNKNOWN | MEDIUM |
| Nation | Player UID+64 pointer -> Nation | people_db UID-19 internal id | REFERENCE | HIGH |
| Height/Weight | Player UID-76/-78 u16 | offset de database não resolvido | UNKNOWN | HIGH (RAM) |

## Ranking de matches principais

### Home Reputation = 8198

1. `Player UID-210`, u16, diff manual 8198→8197, score 100, `CONFIRMED`.
2. Demais coincidências fora do objeto Player foram rebaixadas por ausência da assinatura e conflito entre jogadores.

### World Reputation = 5862

1. `Player UID-206`, u16, diff manual 5862→5861, score 100, `CONFIRMED`.

### Height / Weight

1. `UID-76` / `UID-78`, u16, diffs manuais Saviola 168→169 e 61→62; Zidane (185/80) como âncora, score 100, `CONFIRMED`.

### International caps / goals

1. `UID+72` / `UID+74`, u8, Saviola (29/1) e Zidane (95/26), score 100, `HIGH`.

## Evidência de snapshots

- `workspace/live_memory/3100367/saviola_original.json`
- `workspace/live_memory/3100367/saviola_ca161.json`
- `workspace/live_memory/3100367/saviola_ca160_pa178_v2.json`
- `workspace/live_memory/*/baseline_20261012*.json`
- `workspace/live_memory/3100367/fmm_batch_player_baseline.json`
- `workspace/live_memory/3100367/manual_changes_observed_20261012.json`
- `workspace/live_memory/fmm_manual_batch/*/manual_changes_observed_20261012.json`
- `workspace/live_memory/3100367/fmm_batch_remaining_round_20261012_*.json`
- `workspace/live_memory/fmm_manual_batch/*/remaining_round_20261012_*.json`

Os diffs decodificados estão em `manual_change_observations.json`/`.csv` e `remaining_round_analysis.json`/`.csv`. Somente pares atribuíveis sem ambiguidade foram promovidos a `CONFIRMED`.

Os endereços absolutos são deliberadamente omitidos do schema operacional; eles mudam entre processos.
"""
    (OUTPUT / "FMM_SCHEMA.md").write_text(schema_md, encoding="utf-8")

    unresolved_md = """# Campos não resolvidos e resultado das rodadas manuais

## Resultado aproveitado

As duas rodadas produziram baselines e diffs sequenciais. Além dos campos já confirmados de Player/PData/Playing, a rodada final resolveu:

- Personal Info: Nationality `UID+64`, Born `UID+52`, Ask Value `UID-192`, U21 Caps `UID+73` e U21 Goals `UID+75`.
- Playing: Finishing, Anticipation, Acceleration, Pace, Left foot e Handling nos offsets previstos pela permutação do FMM.txt.
- Preferred Moves: bitset de 48 bits começando em `Player UID-48`, LSB-first.
- Contract: Started `+24`, Expires `+32`, Squad Status `+37`, flags Transfer/Loan `+38`, Happiness `+48`, Squad Number `+49`, Agreed Price `+56` e bônus em `+76/+80/+84/+88`.
- Club: Cash `+248` u32 no Sevilla.
- Nation: Development `+228`, Economic Factor `+233` e Reputation `+252`.

Os dados integrais estão em `remaining_round_analysis.json` e `.csv`. Para os atributos Playing não posicionais, os offsets são sólidos, mas a fórmula geral de leitura dos raws originais 0..255 continua sem solução.

## Diffs não promovidos

- Value: o passo foi pulado. `Player UID-196` mudou apenas durante uma restauração acidental e permanece candidato, não campo confirmado.
- Contract Unhappy e Minimum Release não produziram alteração observável.
- Club: Maximum Attend, Capacity, Seating, Used Capacity, Expansion Capacity, Pitch Width e Pitch Length não produziram diff. Os demais campos foram marcados como ausentes/não editáveis.
- Nation Importance não produziu diff. League Standard alterou simultaneamente `+230` e `+231`, então os dois offsets ficaram como candidatos `LOW`. FIFA Ranking e Ranking Points estavam ausentes/não editáveis.
- O fato de um passo não produzir diff não rejeita a existência do campo; ele só impede a atribuição de um offset.

## Lacunas atuais

- Personal Info: Value ainda não confirmado.
- Playing: transformação raw→1..20 dos atributos não posicionais e confirmação individual dos offsets ainda marcados `HIGH`.
- Contract: Unhappy e Minimum Release; semântica completa dos bits Transfer/Loan e transformação de Squad Number.
- Club: todos os campos além de Cash.
- Nation: Capital, FIFA Ranking, Ranking Points, Stadium, Group Member, Importance e League Standard inequívoco.
- Staff/Coaching e demais estruturas do FMM.txt ainda têm somente raízes de schema, sem campanha controlada específica.

## Estado vivo observado na captura final

A captura chamada `restored_final` não voltou integralmente à baseline. Permaneceram na RAM Nationality, seis atributos Playing, os campos de contrato testados (inclusive Squad Number em raw `0x01`), Agreed Price e Club Cash. Nation foi restaurado por completo; Born, Ask Value, U21 e Preferred Moves também voltaram à baseline. Houve ainda uma alteração acidental em `Player UID-196`.

Como a partida não foi salva, o arquivo em disco não foi modificado. Para descartar o estado de teste, feche/recarregue a partida sem salvar. Não é necessária outra rodada manual para documentar os diffs já obtidos.
"""
    (OUTPUT / "unresolved_fields.md").write_text(unresolved_md, encoding="utf-8")
    print(f"Relatórios gerados em {OUTPUT}")


if __name__ == "__main__":
    main()
