from __future__ import annotations

import json
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from fm06patch.fmm_schema import FMM2_DEFAULT, describe_schema  # noqa: E402
from live_player_memory import find_process_id, kernel32, open_process  # noqa: E402
from run_fmm_manual_batch import (  # noqa: E402
    OUTPUT,
    capture_player,
    capture_pool,
    discover_pool,
)


ROUND = "remaining_round_20261012"
MANIFEST = OUTPUT / f"{ROUND}_manifest.json"
LOG = OUTPUT / f"{ROUND}.log"


STEPS = [
    # Personal Info ainda não resolvido.
    ("player", "01_nationality", "Personal Info — Nationality: troque Argentina por Spain/Espanha."),
    ("player", "02_born", "Personal Info — Born: avance a data de nascimento exatamente 1 dia."),
    ("player", "03_value", "Personal Info — Value: some exatamente 1 ao valor exibido."),
    ("player", "04_ask_value", "Personal Info — Ask Value: some exatamente 1 ao valor exibido."),
    ("player", "05_u21_caps", "Personal Info — U21 Caps: 0 → 1."),
    ("player", "06_u21_goals", "Personal Info — U21 Goals: 0 → 1."),
    # Amostras restantes de grupos Playing; offsets já estão mapeados.
    ("player", "07_acceleration", "Playing Attrib — Acceleration: reduza exatamente 1."),
    ("player", "08_finishing", "Playing Attrib — Finishing: reduza exatamente 1."),
    ("player", "09_anticipation", "Playing Attrib — Anticipation: reduza exatamente 1."),
    ("player", "10_pace", "Playing Attrib — Pace: reduza exatamente 1."),
    ("player", "11_left_foot", "Playing Attrib — Left foot: reduza exatamente 1."),
    ("player", "12_handling", "Playing Attrib — Handling: aumente exatamente 1."),
    # Preferred Moves.
    ("player", "13_ppm_remove_0", "Preferred Moves — desative Runs With Ball Down Left."),
    ("player", "14_ppm_add_1", "Preferred Moves — ative Runs With Ball Down Right."),
    ("player", "15_ppm_add_31", "Preferred Moves — ative Arrives Late In Opponents Area."),
    ("player", "16_ppm_remove_47", "Preferred Moves — desative Likes To Switch Ball To Other Flank."),
    # Contract. Datas entram para promover HIGH -> CONFIRMED.
    ("contract", "17_started", "Contract Sevilla — Started: avance exatamente 1 dia."),
    ("contract", "18_expires", "Contract Sevilla — Expires: avance exatamente 1 dia."),
    ("contract", "19_squad_status", "Contract Sevilla — Squad Status: selecione outra opção válida."),
    ("contract", "20_transfer", "Contract Sevilla — Transfer: alterne o valor/checkbox."),
    ("contract", "21_loan", "Contract Sevilla — Loan: alterne o valor/checkbox."),
    ("contract", "22_unhappy", "Contract Sevilla — Unhappy: alterne o valor/checkbox."),
    ("contract", "23_happiness", "Contract Sevilla — Happiness: aumente exatamente 1."),
    ("contract", "24_squad_number", "Contract Sevilla — Squad Number: aumente exatamente 1."),
    ("contract", "25_appearances", "Contract Sevilla — Apears/Appearances: aumente exatamente 1."),
    ("contract", "26_goal", "Contract Sevilla — Goal: aumente exatamente 1."),
    ("contract", "27_assist", "Contract Sevilla — Assist: aumente exatamente 1."),
    ("contract", "28_clean_sheet", "Contract Sevilla — Clean Sheet: aumente exatamente 1."),
    ("contract", "29_min_release", "Contrato Barcelona — Mini/Minimum Release: reduza exatamente 1."),
    ("contract", "30_agreed_price", "Contrato Barcelona — Agreed Price: aumente exatamente 1."),
    # Club. Referências e nome foram excluídos por risco; somente escalares/enum reversíveis.
    ("club", "31_last_position", "Club Sevilla — Last Position: aumente exatamente 1."),
    ("club", "32_match_day", "Club Sevilla — Match Day: aumente exatamente 1."),
    ("club", "33_prof_status", "Club Sevilla — Prof. Status: escolha outra opção válida."),
    ("club", "34_reputation", "Club Sevilla — Reputation: reduza exatamente 1."),
    ("club", "35_facilities", "Club Sevilla — Facilites/Facilities: reduza exatamente 1."),
    ("club", "36_youth_setup", "Club Sevilla — Youth Setup: reduza exatamente 1."),
    ("club", "37_average_attend", "Club Sevilla — Average Attend: aumente exatamente 1."),
    ("club", "38_minimum_attend", "Club Sevilla — Minimum Attend: aumente exatamente 1."),
    ("club", "39_maximum_attend", "Club Sevilla — Maximum Attend: aumente exatamente 1."),
    ("club", "40_cash", "Club Sevilla — Cash: aumente exatamente 1."),
    ("club", "41_transfer_budget", "Club Sevilla — Transfer Budget: aumente exatamente 1."),
    ("club", "42_budget_remain", "Club Sevilla — Budget Remain: aumente exatamente 1."),
    ("club", "43_available_percent", "Club Sevilla — Available(%): aumente exatamente 1."),
    ("club", "44_wage_budget", "Club Sevilla — Wage Budget: aumente exatamente 1."),
    ("club", "45_used", "Club Sevilla — Used: aumente exatamente 1."),
    ("club", "46_capacity", "Club Sevilla — Capacity: aumente exatamente 1."),
    ("club", "47_seating", "Club Sevilla — Seating: aumente exatamente 1."),
    ("club", "48_used_capacity", "Club Sevilla — Used Cap.: aumente exatamente 1."),
    ("club", "49_expansion_capacity", "Club Sevilla — Expansion Cap.: aumente exatamente 1."),
    ("club", "50_pitch_width", "Club Sevilla — Pitch Width: aumente exatamente 1."),
    ("club", "51_pitch_length", "Club Sevilla — Pitch Length: aumente exatamente 1."),
    # Nation. Referências Capital/Stadium/Group Member foram excluídas por risco.
    ("nation", "52_fifa_ranking", "Nation Argentina — FIFA Ranking: aumente exatamente 1."),
    ("nation", "53_ranking_points", "Nation Argentina — Ranking Points: aumente exatamente 1."),
    ("nation", "54_importance", "Nation Argentina — Importance: reduza exatamente 1."),
    ("nation", "55_league_standard", "Nation Argentina — League Standard: reduza exatamente 1."),
    ("nation", "56_development", "Nation Argentina — Development: reduza exatamente 1."),
    ("nation", "57_economic_factor", "Nation Argentina — Economic Factor: reduza exatamente 1."),
    ("nation", "58_reputation", "Nation Argentina — Reputation: reduza exatamente 1."),
]


class RemainingRoundApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("FMM2 — rodada restante de engenharia reversa")
        self.root.geometry("780x440")
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        OUTPUT.mkdir(parents=True, exist_ok=True)
        self.log_file = LOG.open("a", encoding="utf-8", buffering=1)
        sys.stdout = self.log_file
        sys.stderr = self.log_file

        self.schema = describe_schema(FMM2_DEFAULT)
        self.pid = find_process_id("fm.exe")
        self.handle = open_process(self.pid)
        self.pools: dict[str, list[dict]] = {}
        self.index = 0
        self.applied: list[dict] = []
        self.finished = False
        self.busy = False

        self.status = tk.StringVar(value="Preparando baselines...")
        self.counter = tk.StringVar(value="Inicialização")
        self.instruction = tk.StringVar(
            value="Não altere nada até a preparação terminar."
        )

        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, textvariable=self.counter, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(
            frame,
            textvariable=self.instruction,
            font=("Segoe UI", 15),
            wraplength=730,
            justify="left",
        ).pack(anchor="w", pady=(28, 24))
        ttk.Label(
            frame,
            text=(
                "Faça somente a alteração mostrada. Não avance nem salve a partida. "
                "Se o campo não aparecer ou não aceitar edição, use Pular."
            ),
            wraplength=730,
            justify="left",
        ).pack(anchor="w")
        ttk.Separator(frame).pack(fill="x", pady=22)
        ttk.Label(frame, textvariable=self.status, wraplength=730).pack(anchor="w")

        buttons = ttk.Frame(frame)
        buttons.pack(side="bottom", fill="x", pady=(25, 0))
        self.capture_button = ttk.Button(
            buttons, text="Alteração aplicada — capturar", command=self.capture
        )
        self.capture_button.pack(side="left")
        self.skip_button = ttk.Button(
            buttons, text="Campo ausente / não editável — pular", command=self.skip
        )
        self.skip_button.pack(side="left", padx=12)
        self.capture_button.state(["disabled"])
        self.skip_button.state(["disabled"])

        threading.Thread(target=self.prepare, daemon=True).start()

    def save_manifest(self, status: str) -> None:
        payload = {
            "round": ROUND,
            "status": status,
            "updated_at": datetime.now().astimezone().isoformat(),
            "fm_pid": self.pid,
            "steps_total": len(STEPS),
            "current_index": self.index,
            "results": self.applied,
        }
        MANIFEST.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def capture_scope(self, scope: str, label: str) -> None:
        if scope == "player":
            capture_player(f"{ROUND}_{label}")
        else:
            capture_pool(self.handle, scope, f"{ROUND}_{label}", self.pools[scope])

    def prepare(self) -> None:
        try:
            capture_player(f"{ROUND}_player_baseline")
            for scope in ("contract", "club", "nation"):
                self.root.after(0, self.status.set, f"Descobrindo e capturando {scope}...")
                self.pools[scope] = discover_pool(self.handle, self.schema, scope)
                capture_pool(
                    self.handle,
                    scope,
                    f"{ROUND}_{scope}_baseline",
                    self.pools[scope],
                )
            self.save_manifest("running")
            self.root.after(0, self.ready)
        except Exception as error:
            self.root.after(0, self.fail, str(error))

    def ready(self) -> None:
        self.capture_button.state(["!disabled"])
        self.skip_button.state(["!disabled"])
        self.status.set("Baselines prontas. Faça o primeiro teste.")
        self.show_step()

    def show_step(self) -> None:
        if self.index >= len(STEPS):
            self.start_restore()
            return
        _, _, text = STEPS[self.index]
        self.counter.set(f"Teste {self.index + 1} de {len(STEPS)}")
        self.instruction.set(text)
        self.status.set("Aguardando a alteração no FMM2.")

    def set_busy(self, value: bool) -> None:
        self.busy = value
        state = ["disabled"] if value else ["!disabled"]
        self.capture_button.state(state)
        self.skip_button.state(state)

    def capture(self) -> None:
        if self.busy or self.index >= len(STEPS):
            return
        self.set_busy(True)
        scope, label, instruction = STEPS[self.index]
        self.status.set("Capturando memória; não mexa no FMM2 por alguns segundos...")

        def worker() -> None:
            try:
                self.capture_scope(scope, label)
                self.applied.append(
                    {
                        "number": self.index + 1,
                        "scope": scope,
                        "label": label,
                        "instruction": instruction,
                        "status": "captured",
                    }
                )
                self.index += 1
                self.save_manifest("running")
                self.root.after(0, self.after_step)
            except Exception as error:
                self.root.after(0, self.fail, str(error))

        threading.Thread(target=worker, daemon=True).start()

    def skip(self) -> None:
        if self.busy or self.index >= len(STEPS):
            return
        scope, label, instruction = STEPS[self.index]
        self.applied.append(
            {
                "number": self.index + 1,
                "scope": scope,
                "label": label,
                "instruction": instruction,
                "status": "skipped_missing_or_readonly",
            }
        )
        self.index += 1
        self.save_manifest("running")
        self.show_step()

    def after_step(self) -> None:
        self.set_busy(False)
        self.show_step()

    def start_restore(self) -> None:
        captured = [row for row in self.applied if row["status"] == "captured"]
        self.counter.set("Restauração final")
        self.instruction.set(
            "Restaure no FMM2 todos os campos que você alterou nesta janela. "
            f"Foram capturados {len(captured)} testes. Depois clique no botão final."
        )
        self.status.set("Aguardando a restauração completa; não salve nem avance a partida.")
        self.skip_button.state(["disabled"])
        self.capture_button.configure(text="Restaurei tudo — capturar estado final")
        self.capture_button.configure(command=self.capture_final)

    def capture_final(self) -> None:
        if self.busy:
            return
        self.set_busy(True)
        self.status.set("Capturando restauração final...")

        def worker() -> None:
            try:
                capture_player(f"{ROUND}_restored_final")
                for scope in ("contract", "club", "nation"):
                    capture_pool(
                        self.handle,
                        scope,
                        f"{ROUND}_restored_final",
                        self.pools[scope],
                    )
                self.finished = True
                self.save_manifest("complete")
                self.root.after(0, self.complete)
            except Exception as error:
                self.root.after(0, self.fail, str(error))

        threading.Thread(target=worker, daemon=True).start()

    def complete(self) -> None:
        self.counter.set("Rodada concluída")
        self.instruction.set(
            "Capturas e restauração registradas. Pode fechar esta janela e avisar no Codex."
        )
        self.status.set(str(MANIFEST))
        self.capture_button.configure(text="Fechar", command=self.close)
        self.capture_button.state(["!disabled"])

    def fail(self, error: str) -> None:
        self.set_busy(False)
        self.status.set(f"ERRO: {error}")
        self.save_manifest("error")
        messagebox.showerror("Falha na captura FMM2", error)

    def close(self) -> None:
        if not self.finished:
            self.save_manifest("aborted")
        try:
            kernel32.CloseHandle(self.handle)
        finally:
            self.log_file.close()
            self.root.destroy()


def main() -> None:
    root = tk.Tk()
    RemainingRoundApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
