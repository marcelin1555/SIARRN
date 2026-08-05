# Novidades do SIARRN

Escrito para quem usa o sistema — direção, cozinha e alunos. Quem for mexer no código encontra o detalhe técnico no histórico do git.

---

## Versão 0.1.0 — 5 de agosto de 2026

Primeira versão que roda de ponta a ponta. Já dá para instalar numa máquina, ligar na fila do almoço e começar a medir.

### A cozinha passa a saber quantos pratos preparar

Um painel mostra o número do dia em letras grandes, com a explicação de onde ele saiu: quantos confirmaram presença, quantos avisaram que não vêm, e quantos não disseram nada — esses últimos entram na conta pelo hábito de cada um, não por chute.

O painel também diz honestamente o quanto dá para confiar no número. Nas primeiras semanas ele avisa que ainda está se apoiando na média da escola; conforme o histórico cresce, passa a dizer que está baseado no hábito observado.

### O totem da fila conta quem realmente almoçou

Este é o dado que a escola nunca teve. O aluno digita as primeiras letras do nome, toca no seu nome, e a tela fica verde. Leva três segundos e não precisa de carteirinha, matrícula ou celular.

Ao longo do dia, o painel da cozinha mostra a contagem crescendo em traços riscados — o mesmo gesto de quem contava no papel, que é o que este sistema veio substituir.

### Quem chega novo se cadastra na própria fila

Ninguém precisa cadastrar a escola inteira antes de começar. Na primeira vez que o aluno almoça, ele toca em "não encontrei meu nome", digita nome e turma, e já é servido. A base se constrói sozinha, um aluno por vez.

### Funciona com a internet caída

Se a rede oscilar no meio do almoço, o totem continua achando os nomes e registrando normalmente — a fila não para. Quando a conexão volta, tudo o que ficou guardado sobe sozinho, sem contar ninguém duas vezes. Isso vale inclusive para quem se cadastrou durante a queda.

### Ninguém fica sem comer

O sistema nunca recusa um aluno. Quem não confirmou presença passa igual e é registrado normalmente; confirmar dá direito à fila preferencial, não ao prato. Nenhuma tela do totem mostra vermelho.

### O painel da cozinha fica protegido

O totem abre em tela cheia, sem saída visível, porque fica sozinho numa fila cheia de gente. O painel da cozinha entra por três toques no rodapé ou um atalho de teclado, sempre com PIN.

---

### O que ainda não existe

- **Aplicativo do aluno.** Confirmar presença pelo celular vem na próxima fase.
- **Cartões com QR code.** Vão acelerar a fila de três segundos para um, e podem ser impressos em papel comum.
- **Relatórios.** Cruzar o cardápio do dia com quantos apareceram — é assim que se descobre, por exemplo, que peixe traz menos gente.

### Antes de a próxima fase valer a pena

A fila preferencial precisa ser combinada com a cozinha. O sistema mostra na tela quem confirmou; se ninguém for atendido primeiro por isso, confirmar não traz vantagem nenhuma e o aplicativo nasce sem motivo para ser usado.

---

### Para quem mexe no código

Servidor em Python com SQLite, totem e painel em Tkinter, tudo com biblioteca padrão — nenhuma dependência externa. 94 testes automatizados.

Nesta versão o totem foi reescrito: existiu primeiro em JavaFX e passou nos testes, mas foi migrado para Python. A migração eliminou a regra de busca de nomes duplicada em duas linguagens, que era um erro esperando para acontecer na frente da fila.

Duas correções de desempenho, ambas medidas: o servidor passou a falar HTTP/1.1 com conexão reaproveitada, e a conexão do SQLite deixou de ser aberta e fechada a cada operação — no modo WAL, fechá-la disparava um *checkpoint* a cada escrita. Registrar um almoço caiu de 165 ms para 0,5 ms, e sincronizar cem almoços de 18,5 s para 237 ms.
