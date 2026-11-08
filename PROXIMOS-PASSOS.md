# Próximos passos

As fases 1 e 2 estão prontas: totem com busca por nome e por QR, painel da cozinha, cartões impressos, app do aluno e os executáveis para instalar sem Python. O que o sistema já faz está no [CHANGELOG.md](CHANGELOG.md); as decisões de design e o porquê de cada uma, em [docs/](docs/2026-08-05-siarrn-design.md).

Este arquivo é a versão técnica. A mesma sequência, em linguagem de escola e com o que a direção precisa decidir em cada etapa, está no [ROADMAP.md](ROADMAP.md).

---

## O próximo passo não é código

**Rodar o sistema na escola.** Tudo o que existe até aqui foi testado com 120 alunos fictícios. O número que importa — quanto a previsão erra, quantos pratos sobram — só aparece com a fila de verdade, e cada semana sem uso é uma semana a menos de histórico para a previsão aprender.

Para isso falta:

- **Uma máquina para o totem** e outra (ou a mesma) para o servidor. Um notebook emprestado basta para começar.
- **Combinar a fila preferencial com a cozinha.** O software mostra quem confirmou presença; se ninguém for atendido primeiro por isso, confirmar não traz vantagem e o aplicativo não tem por que ser instalado. Essa conversa vale mais do que qualquer tela.
- **Instalar o app num celular de verdade.** Ele compila, é assinado e o servidor o entrega, mas nunca rodou num aparelho. Todo defeito sério deste projeto apareceu ao rodar, não nos testes.
- **Cópia de segurança do banco.** É o único item de código que bloqueia o piloto. Hoje tudo vive num `siarrn.db` só; se a máquina do servidor falhar, vai junto o histórico de que a previsão depende. Uma cópia diária com `sqlite3.Connection.backup` (seguro com o WAL ligado) para outra pasta ou pendrive, guardando as últimas N, resolve.
- **Uma semana de linha de base.** Antes de ligar, a cozinha anota do jeito atual quanto preparou e quanto sobrou. Sem esse número não dá para dizer, no fim do piloto, se a previsão erra menos que o método antigo.
- **A decisão da direção sobre os dados.** Nome, turma e dias de almoço de menores de idade. Quem acessa, por quanto tempo se guarda e se as famílias são avisadas é decisão da escola, não do código, mas precisa vir antes do primeiro aluno real.

Todo dia, **o painel da cozinha precisa ser aberto antes de servir**. É nessa hora que a previsão do dia fica guardada, e é ela que se compara depois com quantos almoçaram para saber quanto o sistema erra. Dia sem painel aberto é dia sem medida.

Nas primeiras semanas, a cozinha deve abrir **Corrigir cadastros** uma vez por dia. O cadastro é feito pelo aluno, na fila, com pressa, e duplicata é inevitável: cada aluno cadastrado duas vezes infla a previsão em cerca de um prato por até quatro semanas.

---

## Fase 3 — aprender, depois do piloto

Relatórios: o cardápio cruzado com o comparecimento, e a curva da sobra ao longo das semanas. O campo `refeicao.cardapio` já é preenchido e o `preparado` também; falta cruzar.

Fica para depois do piloto de propósito. Relatório sobre dado fictício só mostra o que o gerador de dados inventou, e o formato certo — o que a cozinha olha, de quanto em quanto tempo — só se descobre vendo a cozinha usar o painel que já existe.

---

## Coisas pequenas que ficaram no caminho

- Na lista de cadastros parecidos, um par que a cozinha ignora volta a aparecer da próxima vez. Guardar os descartes só vale a pena se a lista encher de falsos positivos na prática; com 120 alunos sem duplicata nenhuma, ela mostra um par.
- O cadastro na fila não avisa "parece que você já está cadastrado". Prevenir seria melhor que corrigir, mas é mais um passo com a fila parada atrás do aluno. Decidir depois de ver quantas duplicatas aparecem no piloto.
