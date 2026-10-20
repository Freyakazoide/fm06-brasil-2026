# C14 — Modo de edição e moddabilidade

## Objetivo
Permitir que clubes, pessoas, competições, textos e parâmetros sejam alterados sem recompilar, com validação, versão e migração de saves.

## Regras
1. Formatos: `.xlsx` para edição humana em massa, `.json` para execução e `.md` para documentação. Importador converte planilha para JSON validado.
2. Todo registro tem `id` imutável em ASCII, `nome` exibido, `fonte`, `atualizado` e `schema_version` quando aplicável.
3. IDs nunca são reciclados. Renomear muda `nome`, não `id`; exclusão cria `inactive=true` para preservar saves.
4. Carregamento: jogo-base → DLC → mods por prioridade → alterações do save. Conflito no mesmo campo vence a maior prioridade e entra no relatório.
5. Mod declara versão, autor, dependências, incompatibilidades e faixa de versão do jogo.
6. Validação tem níveis: erro bloqueia (id duplicado, referência inexistente, tipo errado); aviso permite (fonte vazia, estimativa, tradução longa).
7. Importação é transacional: se houver erro bloqueante, nada é aplicado. Backup automático guarda três versões.
8. Editor oferece formulários para registro único e grade para lote; mostra diferenças antes de salvar.
9. Save grava cópia dos parâmetros essenciais. Atualizar mod não muda competição em andamento sem migração explícita.

## Esquemas editáveis
| arquivo lógico | campos mínimos | formato de autoria |
|---|---|---|
| clubes | id, nome, país, cidade, reputação, finanças | xlsx |
| jogadores | id, nome, nascimento, clube, posições, CA, PA | xlsx |
| staff | id, nome, cargo, clube, atributos | xlsx |
| competições | id, temporada, fases, vagas, desempates | json/xlsx |
| traduções | chave, pt-BR, limite, contexto | xlsx |
| notícias | id, situação, texto, variáveis, peso | xlsx |
| parâmetros | chave, valor, mínimo, máximo | json |

## Números (parâmetros)
| parâmetro | valor | por quê / fonte |
|---|---:|---|
| backups automáticos | 3 | recuperação simples |
| tamanho máximo por mod | 2 GB | assets incluídos |
| versão de esquema inicial | 1.0 | semântica major/minor |
| relatório de validação | até 10 mil ocorrências agrupadas | não travar lotes grandes |

## Exemplos / casos de teste
| entrada | resultado esperado |
|---|---|
| dois jogadores com mesmo `id` | erro; importação inteira revertida |
| nome de clube alterado, mesmo `id` | saves e referências continuam válidos |
| mod B prioridade 20 altera campo de mod A prioridade 10 | B vence e conflito aparece no relatório |
| competição em rodada 12 recebe nova regra | save mantém versão antiga até próxima edição |
| coluna adicional desconhecida | aviso e preservação para reexportar; não quebra importação |

## Casos de borda
Referência circular de competição é erro; mod removido substitui registros usados por “conteúdo ausente” recuperável; codificação é UTF-8; datas são ISO `AAAA-MM-DD`; dinheiro usa inteiro na menor unidade.

## Liga com
Todos os dados do jogo, especialmente competições, traduções, regens e notícias.

## Perguntas em aberto
Assinatura e distribuição de mods; oficina online; política para assets com direitos autorais; editor dentro do jogo ou aplicativo separado.

