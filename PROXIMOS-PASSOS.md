# Próximos passos

A fase 1 está pronta e verificada — ver [CHANGELOG.md](CHANGELOG.md) para o que o sistema já faz, e [docs/](docs/2026-08-05-siarrn-design.md) para as decisões de design e o porquê de cada uma.

---

## Antes de programar qualquer coisa da fase 2

**Combinar a fila preferencial com a cozinha.** O software já mostra quem confirmou presença; se a cozinha não atender essas pessoas primeiro, confirmar não traz vantagem nenhuma — e o aplicativo do aluno nasce sem motivo para ser instalado. Essa conversa vale mais para o projeto do que qualquer tela.

**Conseguir uma máquina para o totem.** A fase 1 existe justamente para ser a demonstração desse pedido: dá para rodar num notebook emprestado, na frente da coordenação, com nomes de verdade.

---

## Fase 2 — identificar e prever

**Códigos e cartões de papel.** Cada aluno já tem um código aleatório gerado no cadastro (`aluno.codigo`). Falta gerar a folha de QR para impressão — provavelmente uma tela nova no modo gestão, reaproveitando o `qr_util.py` do SIGBEF.

**Leitura de QR no totem.** Câmera comum mais decodificação. É a parte tecnicamente mais chata do projeto: foco, iluminação de refeitório, QR amassado no bolso. A busca por nome continua existindo como alternativa — ela é o que garante que a fila anda quando a câmera implica.

**Aplicativo do aluno** (Kotlin + Compose). Três telas: quem sou eu, o dia de hoje com o cardápio e o botão de confirmar, e o meu QR. O mesmo código funciona impresso ou na tela do celular, então quem não tem aparelho não fica de fora.

Lembrar que a distribuição do APK passa pelo aviso de "fontes desconhecidas" e vai derrubar a adesão. O desenho absorve isso: declaração nunca foi requisito, e quem não instalar entra na conta pelo histórico.

---

## Fase 3 — aprender

Relatórios e a correlação entre cardápio e comparecimento. O campo `refeicao.cardapio` já é preenchido; falta cruzar. É assim que se descobre que peixe traz trinta por cento menos gente — e é aí que a sobra deixa de ser mistério.

---

## Coisas pequenas que ficaram no caminho

- O totem ainda não tem tela de configuração: o endereço do servidor entra por `--servidor` ou editando `~/.siarrn/totem.json` na mão.
- Não há tela para corrigir nome digitado errado no cadastro (`alunos.renomear` existe no servidor, mas sem interface).
- O painel da cozinha não deixa registrar quantos pratos foram de fato preparados (`refeicoes.definir_preparado` existe, sem interface). Sem esse número, a conta da sobra fica pela metade.
