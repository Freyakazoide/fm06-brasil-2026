# Exemplo resolvido — leitor do árbitro (`OFFICIAL`)

- Quem analisou / data: Claude, 22/10/2026
- Ferramenta: capstone (desmontagem), `fm.exe` 6.0.2 original
- Função principal: `00a6d540` (`OFFICIAL_ler`; a vtable `010f8fbc` chama via `00a6e280`)

## Resumo

Lê o bloco do árbitro depois da parte comum da pessoa: um número, capacidade, potencial,
reputação e 10 atributos de 1 byte. Os três primeiros números batem com o banco (Wilson
Luís Seneme: 135, 160, 145) e viraram o `aplicar_arbitros.py`.

## Campos lidos, em ordem

| # | Endereço da instrução | Lê | Vai para | O que acho que é | Certeza | Por quê |
|---|---|---|---|---|---|---|
| 1 | `00a6d566` | u32 | `this - 0x30` | referência (cidade ou federação?) | baixa | quase sempre FFFFFFFF; Seneme 1434 |
| 2 | `00a6d57d` | u16 | `this - 0x2c` | capacidade | alta | Seneme 135; os FIFA de 2005 têm os maiores |
| 3 | `00a6d58c` | u16 | `this - 0x2a` | potencial | alta | sempre ≥ capacidade |
| 4 | `00a6d59b` | u16 | `this - 0x28` | reputação | média | igual à capacidade na maioria |
| 5–14 | `00a6d5aa`–`00a6d641` | 10 × u8 | `this - 0x26` a `this - 0x1d` | atributos do árbitro | média | zerados na maioria dos brasileiros; de 1 a 20 em alguns |
| 15 | `00a6d654` | u32 | `this - 0x1c` | ? | baixa | |

Condições de versão:

| Endereço | Condição | O que fica dentro |
|---|---|---|
| `00a6d665` | versão ≥ `0xfd` | `00a6d470` lê mais um bloco em `this - 0x18` |

## Quem chama / de onde vem

| Endereço | Função | O que faz com isto |
|---|---|---|
| `00a6e280` | ajuste de `this` | entra no `00a6d540` (herança múltipla) |
| `00a54060` | leitor da pessoa | lê a parte comum (nome, nascimento, nação) |

## Respostas

1. O registro é: parte comum da pessoa, par (índice, UID), u32, u8 tipo = 4, e este bloco.
2. O "rigor" ainda não dá para saber: os 10 atributos estão zerados na maioria dos
   árbitros brasileiros e o leitor não diz o nome de cada um. Falta ver quem usa cada
   `this - 0x26..` (por exemplo, o código que decide dar cartão).
