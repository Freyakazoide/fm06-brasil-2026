# Interface (telas) do FM06

As telas são montadas por arquivos XML em `data\` (`panels`, `menus`,
`screens`, `skins`…). O `fm.exe` carrega `panels/`, `panels/global panels`,
`panels/dialog buttons` (`0x00C86F75`, `0x00C89A8C`, `0x00CC1AE9`).

## Abrir link ou programa a partir do jogo

- O `fm.exe` carrega `ShellExecuteW` sob demanda (thunk em `0x00D912D2`,
  ponteiro `0x0131F124`) e chama em `0x00C6A790` e `0x00C6A815` com
  `(janela, NULL, endereço, NULL, NULL, SW_SHOWNORMAL)`: abre um endereço
  como o Windows abriria (navegador, arquivo ou programa).
- O leitor de XML conhece as propriedades `hyperlink` e `html_hyperlink`
  (`0x00E23021`, `0x00E23041`).
- Há também `http://www.sigames.com/clickthru.php?url=` (`0x00E25750`).

Hipótese a testar: um botão num XML de painel com `hyperlink` apontando para
um endereço local (página ou programa nosso) abre esse programa de dentro do
jogo. O programa altera a memória do jogo (como o injetor) e o efeito fica no
save quando o usuário salva.
