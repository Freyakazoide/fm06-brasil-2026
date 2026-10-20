# C8 — Motor de partida

## Objetivo
Gerar partidas lance a lance reproduzíveis, calibráveis e suficientes para uma apresentação 2D por sprites.

## Regras
1. Unidade: posses de 4–35 segundos; relógio avança por duração. Cada posse gera origem, progressão e desfecho.
2. Ordem: recuperação/saída → escolha de zona → ação (passe, condução, drible, cruzamento) → duelo → desfecho (continua, perda, chute, bola parada, falta).
3. Probabilidade usa diferença logística entre atacante e defensor, acrescida de tática, fadiga, mando e ruído reproduzível por `seed`.
4. Passe pesa Passe, Técnica, Decisões e Compostura contra Antecipação, Posicionamento e Pressão; drible usa Finta/Aceleração/Agilidade contra Desarme/Antecipação/Força; chute usa Finalização/Técnica/Compostura contra pressão e goleiro.
5. Qualidade do chute (`xG`) depende de distância, ângulo, parte do corpo, assistência e pressão; atributo muda conversão, não cria xG impossível.
6. Tática: mentalidade altera risco e jogadores à frente; linha altera espaço atrás; pressão aumenta recuperações e fadiga; largura muda zonas e cruzamentos.
7. Mando: +0,12 no logit de duelos e decisões do time da casa; clássico reduz o bônus pela metade. Altitude e calor afetam fadiga, gramado ruim eleva erro técnico.
8. Cartões resultam de falta, intensidade, agressividade, jogo sujo e rigor do árbitro. Lesão resulta de contato, fadiga, piso e propensão.
9. Uma temporada simulada deve cair nos intervalos do C0; calibração olha média de 100 temporadas, não uma partida.
10. Toda partida salva `seed`, escalações, táticas e eventos; reprocessar com os mesmos dados gera o mesmo placar.

## Formato do evento
| campo | tipo | exemplo |
|---|---|---|
| `id`, `minuto`, `segundo` | inteiro | 184, 67, 12 |
| `tipo` | enum | `chute` |
| `time`, `ator`, `alvo` | id | `FLA`, `p_102`, `gol_1` |
| `zona_origem`, `zona_destino` | 1–18 | 14, 17 |
| `resultado` | enum | `gol`, `defesa`, `fora`, `bloqueio` |
| `xg`, `probabilidade` | 0–1 | 0,34, 0,41 |
| `placar` | par | 2–1 |
| `animacao` | enum | `chute_colocado_direita` |
| `texto_chave` | id | `match.shot.goal.placed` |

## Números (parâmetros)
| parâmetro | valor | por quê / fonte |
|---|---:|---|
| posses por time | 85–115 | alvo editorial |
| chutes totais | 18–26 | calibrar pelo C0 |
| gols Série A | 2,44–2,52/jogo | C0, 2023–2025 |
| vitória mandante Série A | 46,8–50,3% | C0 |
| empates Série A | 25,8–26,6% | C0 |
| impacto máximo do mando | ~3 pontos percentuais de sucesso | editorial |

## Exemplos / casos de teste
| entrada | resultado esperado |
|---|---|
| mesma seed, dados e tática | lista de eventos e placar idênticos |
| atacante 16 vs defensor 10, sem pressão | chance maior que atacante 10 vs defensor 16 |
| 100 temporadas da Série A | gols/jogo entre 2,35–2,65; mandante 44–52%; empate 23–30% |
| pressão máxima por 90 min | mais recuperações altas e fadiga; não apenas bônus gratuito |
| chuva forte e gramado 6/20 | mais erros de domínio/passe e menos velocidade da bola |

## Casos de borda
Sem goleiro, jogador de linha assume com atributos mínimos; duas expulsões não encerram jogo, menos de sete atletas encerra; vantagem é resolvida antes da falta; acréscimo inclui lesões, VAR e substituições.

## Liga com
Atributos, tática, árbitros, clima, lesões, C0, sprites e notícias.

## Perguntas em aberto
Escolher 18 ou 24 zonas; definir alcance visual das animações; completar metas de cartões, pênaltis e escanteios no C0.

