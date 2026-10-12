# Editor de jogadores na memória

**Validado no jogo (12/10/2026):** Saviola com CA 111, PA 199, altura 201, peso
99, Finta 1, Cruzamentos 20 e Velocidade 2. Os outros atributos ficaram
iguais, e tudo continuou igual depois de salvar e carregar o jogo.

Edita jogadores no FM06 aberto, logo depois do New Game. Depois é só salvar o
jogo: o save guarda tudo.

## Uso

1. Inicie um New Game e espere chegar à tela principal. Não precisa avançar dias.
2. No PowerShell (como Administrador, se pedir), na pasta do projeto:

   ```powershell
   python scripts\live_player_editor.py data\live_edits\teste_saviola.json
   ```

   Sem `--apply` o script só mostra o que mudaria.
3. Se estiver certo, rode de novo com `--apply`.
4. Confira a ficha do jogador no jogo. Para desfazer na mesma partida:
   `--restore workspace\live_edits\backup_<data>.json`.
5. Para só ver os dados atuais de um jogador: `--show <UID>`.
6. Para descobrir o clube de um jogador: `--club-of <UID>`.
7. Para listar o elenco de um clube: `--squad <UID do clube> --out workspace\elenco.csv`.
   O CSV traz UID, vínculo (contrato ou empréstimo), nascimento, CA, PA,
   altura, peso e posições com nota 15 ou mais.

## Formato do JSON

```json
{
  "year_shift": 0,
  "players": [
    {
      "uid": 3100367,
      "ca": 111, "pa": 199,
      "height": 201, "weight": 99,
      "birth_date": "1981-12-11",
      "nationality_like": 104318,
      "home_reputation": 8200, "current_reputation": 8000, "world_reputation": 5900,
      "attributes": { "Finta": 1, "Cruzamentos": 20, "Velocidade": 2 },
      "positions": { "Attacker": 20, "Att. Center": 20 },
      "personality": { "Ambition": 18, "Professional": 15 },
      "preferred_moves": { "add": ["Curls Ball"], "remove": [0] }
    }
  ]
}
```

- Todos os campos são opcionais, exceto `uid`.
- Os atributos aceitam o nome que aparece na ficha em português (como
  `Finta`, `Instinto` ou `Cond. Fís. Natural`) ou o nome em inglês do FMM. Os
  valores vão de 1 a 20, como o jogo mostra.
- `nationality_like` copia a nacionalidade de outro jogador (pelo UID). Use
  qualquer jogador que já tenha a nacionalidade desejada.
- `year_shift` soma anos a todas as `birth_date`. Use `-21` para escrever datas
  reais de 2026 e o jogador ficar com a idade certa num jogo que começa em 2005.
- Ao mudar o CA, os atributos relativos ao CA são deslocados pela diferença
  das bases, o que mantém exato o valor interno (e não só o exibido), a menos
  que você os defina no JSON.

## Como os atributos ficam na memória

Detalhes em `docs/reversing/people-db.md`. Resumo:

- **Absolutos** (físicos e parte dos mentais): 5 × valor.
- **Relativos ao CA** (técnicos, parte dos mentais e de goleiro): byte com
  sinal, exibido = `(byte + base) // 5`, com `base = (CA + 9) // 2`.
- A fórmula da base foi ajustada com 2 jogadores (CA 160 e 185). Por isso o
  script grava sempre no meio da faixa, o que tolera erro de ±2 na base.
