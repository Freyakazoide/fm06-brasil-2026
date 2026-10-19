# Dinheiro e finanças dos clubes (FM06 6.0.2)

- O jogo guarda dinheiro em libras. O registro de moeda do server_db
  ("Brazilian Real", "Real", "R$") tem 5,08 por libra (Euro 1,45).
- Registro do clube no server_db (leitor do CLUB, 0x00A31C70): depois dos
  apelidos e do ano de fundação, u32 público médio, mínimo e máximo
  (CLUB+0xF0/F4/F8), mais campos, duas listas (u8 n + n × u32), u8 tipo de
  finanças (0 básico, 1 completo) e o objeto de finanças, que começa com o
  **saldo** (u32, CLUB_FINANCE+4). Os clubes brasileiros do banco são do tipo
  básico. `src/fm06patch/financas.py`.
- `BOOST_TEAM` (executor 0x00AAD270): acha o time pelo UID em texto ou pelo nome;
  com `atte` > 0 grava público médio, médio − 10000 e médio + 10000 (o mínimo
  pode ficar negativo); com `repu` > 0 a reputação; com `cash` ≠ −1 zera
  empréstimos e, só em finanças completas, grava o saldo. Por isso o saldo dos
  brasileiros vai direto no banco.
- O "Cash +248" do FMM é, na verdade, CLUB+0xF8 (público máximo).
