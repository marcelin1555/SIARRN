# Para onde o SIARRN vai

Este documento é para a direção da escola. Ele diz o que o sistema já faz, o que vem depois, e — principalmente — o que precisa ser decidido pela escola para cada passo acontecer.

Não há datas. Cada etapa só começa quando a anterior mostrar o que tinha que mostrar. Foi pular essa conferência que fez o formulário online morrer: o número que ele entregava parecia certo e ninguém tinha como saber que não era.

---

## Hoje: pronto para testar

- O aluno registra o almoço no totem em cerca de três segundos, pelo nome ou mostrando o cartão.
- A fila não para se a internet cair: o totem guarda e envia depois.
- A cozinha vê quantos pratos preparar e de onde saiu o número.
- Existe um aplicativo para o aluno avisar se vem e mostrar o próprio cartão no celular.
- **Ninguém fica sem comer.** Quem não avisou passa igual.

Tudo isso foi testado com 120 alunos inventados. Com alunos de verdade, ainda nada.

---

## Etapa 0 — Antes de ligar

O que a escola precisa fazer:

- **Medir como é hoje.** Durante uma semana, do jeito atual, anotar quantos pratos foram preparados e quanto sobrou. É contra esse número que o sistema vai ser comparado. Sem ele, no fim do piloto ninguém consegue dizer se melhorou.
- **Decidir sobre os dados dos alunos.** O sistema guarda nome, turma e em que dias cada aluno almoçou. São dados de menores de idade, e a lei (LGPD) pede cuidado especial com eles. A escola precisa definir quem pode ver esses dados, por quanto tempo ficam guardados e se as famílias devem ser avisadas ou consultadas. Isto não é orientação jurídica: vale ouvir a secretaria de educação.
- **Separar um computador** para o totem e outro (ou o mesmo) para guardar os dados. Um notebook emprestado basta para começar. Uma webcam comum é opcional.
- **Combinar com a cozinha a fila preferencial.** Quem avisou que vem é atendido primeiro. Sem esse acordo, avisar não traz vantagem nenhuma, ninguém usa o aplicativo e a previsão fica só com o hábito de cada aluno.

O que fica do lado do sistema:

- **Cópia de segurança automática.** Hoje os dados ficam num único arquivo, no computador do servidor. Se esse computador falhar no meio do piloto, perde-se o histórico — e é dele que a previsão depende. Isso precisa existir antes de entrar o primeiro aluno de verdade.
- Gerar de novo os programas de instalação com as últimas correções.

**Pronto para seguir quando:** as quatro coisas da escola estiverem resolvidas e a cópia de segurança funcionando.

---

## Etapa 1 — Piloto

Cerca de quatro semanas de aula com o totem na fila.

A previsão precisa de uns vinte almoços de histórico para deixar de se apoiar na média da escola e passar a usar o hábito de cada aluno. Antes disso o número é mais cauteloso, e o painel avisa.

A cozinha passa a ter uma rotina de poucos minutos por dia:

- **abrir o painel antes de servir** — é nessa hora que a previsão do dia fica guardada para comparar depois;
- **informar quantos pratos preparou** — sem isso o sistema sabe quantos comeram, mas não quanto sobrou;
- **corrigir cadastros repetidos** — o aluno se cadastra sozinho, na fila, com pressa, e às vezes vira duas pessoas.

**Pronto para seguir quando:**

- a fila não ficou mais lenta do que era;
- quase todo almoço servido foi registrado no totem;
- a previsão errou menos do que o número que a cozinha usava antes (o da Etapa 0).

Se a fila ficar mais lenta, o piloto para e isso se resolve primeiro. Nada mais importa se a fila não anda.

---

## Etapa 2 — Aprender

Depois de uns dois meses de dados de verdade, o sistema passa a responder perguntas que hoje ninguém consegue responder:

- **Quanto a previsão erra**, dia a dia, e se está melhorando.
- **Quanto sobra por semana**, e se a sobra está caindo.
- **Que cardápio traz mais ou menos gente.** Se dia de peixe vem menos aluno, a cozinha pode preparar menos nesse dia.

Essas telas só serão feitas depois do piloto, de propósito. O formato certo — o que a cozinha olha e de quanto em quanto tempo — só se descobre vendo a cozinha usar o que já existe.

**Pronto para seguir quando:** a sobra tiver caído em relação à Etapa 0, ou ficar claro por que não caiu.

---

## Etapa 3 — Ampliar

Só se a Etapa 2 mostrar que vale a pena:

- **Lanche**, além do almoço. O sistema já foi feito com espaço para isso.
- **Avisar na hora do cadastro** "parece que você já está cadastrado", para evitar o aluno duplicado em vez de corrigir depois. Depende de quantos duplicados aparecerem no piloto.
- **Mais de um totem**, se a fila for grande demais para um só.

---

## O que não está nos planos

De propósito, e não por falta de tempo:

- **Negar comida a qualquer aluno.** O sistema nunca recusa ninguém. Avisar dá fila preferencial, não direito ao prato.
- **Controle de estoque ou custo por prato.** É outro sistema, com outro dono.
- **Ligação com o sistema da secretaria.** O cadastro se faz na própria fila, um aluno por vez.
- **Publicar o aplicativo na loja do Google.** Ele é instalado direto da rede da escola.

---

O detalhe técnico de cada passo está em [PROXIMOS-PASSOS.md](PROXIMOS-PASSOS.md). O que já mudou, versão por versão, está em [CHANGELOG.md](CHANGELOG.md).
