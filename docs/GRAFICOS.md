# Escudos, uniformes e nomes dos clubes de 2026

Formato do FM05/06 (validado no jogo com Flamengo 322, Palmeiras 329 e Cruzeiro 321):

- arquivos em `data\graphics\pictures\<qualquer subpasta>\` com um `config.xml`
  (`<list id="maps">`, `<record from="<arquivo sem .png>" to="<chave>"/>`);
- escudo: `graphics/pictures/club/<UID>/logo` (60×60, cabe no cabeçalho da skin)
  e `.../icon` (20×18);
- uniforme: `graphics/pictures/team/<UID>/kits/home|away|third` (100×100);
- UID = o do jogo ("Show Unique IDs" nas preferências), não o do repositório.

## Um clube do jogo = um clube de 2026

`identidade.build` junta as séries e os estaduais: o clube de 2026 que está numa
série usa no estadual o mesmo clube do FM06; os outros clubes das séries não
entram no estadual de ninguém; substituto de clube com nome não pode ser um
clube que já é outro clube de 2026 nos estaduais (só vaga extra, que fica com o
próprio nome). O `aplicar_brasil_2026.py --apply` grava o resultado em
`data\brasil\clubes\identidade_fm06.csv`.

## Gerar

```
python scripts\gerar_graficos.py --baixar
```

Lê `identidade_fm06.csv`, `uniformes_2026.xlsx`, `clubes_master.xlsx` e
`clubes_faltando.xlsx`; os escudos ficam em `data\brasil\clubes\escudos`
(`--baixar` baixa os que faltam pelo `escudo_url`). Grava
`data\brasil\graficos_2026\data` (copiar por cima da pasta `data` do jogo):
escudos, uniformes e `db\lnc\all\brasil_2026_clubes.lnc` (`CLUB_NAME_CHANGE`,
`_SHORT_`, `_LONG_` com o UID do jogo para quem tem outro nome no FM06), além de
`relatorio.csv` (clubes sem escudo).

Uniforme: `graficos.kit_png`, desenhado em 4× e reduzido (volume, dobras,
sombra), com gola e punhos na cor de detalhe, escudo no peito, fornecedor
(Adidas = 3 listras no ombro) e patrocínio master. O 3º uniforme sai quando
`uni3_camisa` está preenchido.
