# Novidades do SIARRN

Escrito para quem usa o sistema — direção, cozinha e alunos. Quem for mexer no código encontra o detalhe técnico no histórico do git.

---

## Versão 0.3.1 — 7 de novembro de 2026

### A previsão guardada é a que a cozinha viu

O painel recalcula o número o dia inteiro, e cada aluno que se cadastra na fila entra na conta. Até aqui, o número guardado no fim do dia era o último calculado, já inflado por quem se cadastrou depois de a comida estar pronta. Comparar esse número com o que de fato saiu faria a previsão parecer pior do que é.

Agora o número guardado congela no primeiro almoço registrado. A tela continua mostrando a conta ao vivo; o que fica para comparar depois é o número da hora de cozinhar.

Para isso funcionar, **a cozinha precisa abrir o painel antes de começar a servir**. Dia em que ninguém abre o painel fica sem previsão guardada.

### O totem se configura pela tela

Na primeira vez que o totem abre numa máquina, ele pergunta o endereço do servidor e um PIN novo para a cozinha. Antes, sem configuração, ele procurava o servidor na própria máquina, abria em tela cheia e ficava fora do ar sem avisar ninguém. E o PIN ficava `1234` para sempre, a menos que alguém editasse um arquivo escondido.

Depois da instalação, as duas coisas mudam no painel da cozinha, no botão **Este totem**. Ao salvar, o painel tenta o endereço novo na hora: ou os números aparecem, ou aparece o aviso de servidor fora do ar.

O botão de voltar ao totem também deixou de ficar cortado em telas estreitas.

---

## Versão 0.3.0 — 28 de outubro de 2026

### A cozinha corrige cadastros duplicados

O aluno se cadastra sozinho, na fila, com pressa. Quando não se acha na busca — porque digitou "Jao" em vez de "João" — ele toca em "não encontrei meu nome" e vira duas pessoas no sistema.

Isso não era só bagunça na lista. O cadastro abandonado continuava entrando na previsão pelo hábito antigo, e o novo entrava pela média da escola: **o mesmo aluno contado quase duas vezes, por até quatro semanas.** Medido com 120 alunos, doze duplicatas faziam a previsão pedir nove pratos a mais.

No painel, o botão **Corrigir cadastros** mostra os nomes que podem ser da mesma pessoa, com a turma e a data de cadastro de cada um. A cozinha escolhe qual nome fica e os dois viram um só, com todos os almoços juntos.

**O sistema nunca junta ninguém sozinho.** Não há regra que separe erro de digitação de irmão: "Gabriel Costa" e "Gabriela Costa" se parecem mais do que "Jao Pedro" e "João Pedro". Quem decide é quem conhece os alunos.

Os dois cartões continuam valendo depois da junção, e o celular também. Um almoço registrado offline no cadastro antigo chega ao servidor e conta normalmente.

Na mesma tela dá para corrigir um nome digitado errado. Os almoços já registrados continuam com o aluno.

---

## Versão 0.2.0 — 1 de outubro de 2026

### As telas agora parecem todas do mesmo sistema

O totem tinha duas aparências. A tela de apresentação era colorida e viva; as
telas de uso — a busca do aluno, o painel da cozinha, as janelinhas de cadastro
— eram cinzas e quadradas. O aluno tocava numa e caía na outra.

Agora é tudo a mesma linguagem: **fundos em degradê azul, cantos arredondados e
botões redondos**, com as mesmas cores de sempre. Verde continua sendo "deu
certo", laranja continua sendo "atenção", azul continua sendo "informação".

Mudanças que dá para ver na fila:

- **O campo de digitar o nome ficou grande e destacado**, num cartão branco com
  contorno dourado sobre a faixa azul. É a única coisa que o aluno precisa
  fazer, e agora é a coisa mais visível da tela.
- **O cardápio do dia aparece também na tela de busca.** Antes só estava na
  apresentação: quem tocava na tela perdia a informação e tinha de esperar o
  totem voltar sozinho.
- **A tela verde diz o que tem no prato.** Antes desejava bom almoço sem dizer
  de quê.
- **Os nomes nunca mais aparecem cortados pela metade.** A lista mostra só os
  que cabem inteiros e, quando sobram outros, avisa para digitar mais letras.
- **O cadastro do primeiro almoço ficou com letras maiores.** Ele acontece com
  a fila parada atrás do aluno, e os campos eram pequenos demais para isso.

No painel da cozinha, o número grande e os três blocos coloridos ganharam
cantos arredondados, e a tela foi reorganizada para **caber inteira em monitores
menores** — antes, numa tela de 768 pixels de altura, o espaço de informar o
cardápio ficava fora da tela.

Nada disso muda o funcionamento: a busca continua local, a fila continua
andando com a internet caída, e ninguém continua sendo recusado.

---

## Versão 0.1.0 — 5 de agosto de 2026

Primeira versão que roda de ponta a ponta. Já dá para instalar numa máquina, ligar na fila do almoço e começar a medir.

### O aplicativo do aluno

Três telas, e nada além disso: o **cardápio do dia**, os botões de avisar se vem ou não, e o **QR pessoal** para mostrar na fila. É o mesmo código do cartão de papel — quem tem celular não precisa carregar papel, e quem não tem continua atendido.

Na primeira vez o app pergunta o endereço do sistema (a escola informa, num cartaz perto do refeitório) e quem é o dono do aparelho. Depois disso, abre direto no dia de hoje.

O aluno instala abrindo `http://<endereço do sistema>/siarrn.apk` no navegador do celular. O arquivo tem 1,2 MB.

**Avisar continua sendo um favor, não uma obrigação.** Quem não disser nada entra na conta pelo próprio hábito, e o texto do app diz isso com todas as letras. E o QR aparece mesmo sem conexão — é ele que resolve a fila.

### Dá para instalar sem ter Python

O sistema virou dois programas prontos, um do servidor e um do totem. Copie a pasta, dê um duplo clique, e funciona — não é preciso instalar nada antes.

As fotos da tela de apresentação ficam numa pasta ao lado do programa, então trocá-las continua sendo copiar arquivos.

### Cartões com QR, impressos em papel comum

Cada aluno tem um código próprio, e agora a cozinha consegue imprimir os cartões: no painel, o botão **Cartões dos alunos** gera uma folha pronta para recortar, com o QR, o nome e a turma de cada um. Dez por página, papel comum, sem impressora especial.

Depois da primeira leva, dá para imprimir só quem se cadastrou nos últimos dias, em vez de repetir as doze folhas inteiras.

### O totem lê o cartão pela câmera

Uma webcam comum apontada para a fila. O aluno mostra o cartão — ou o celular, quando o aplicativo existir — e o almoço é registrado em cerca de um segundo, contra três ou quatro digitando o nome. Com cem pessoas esperando, essa diferença é a fila inteira andando.

Funciona até na tela de apresentação: quem mostra o cartão vê o próprio nome em verde sem tocar em nada.

**A câmera é um atalho, nunca uma exigência.** Se ela não existir, falhar ao abrir, ou não enxergar um cartão amassado, nada trava: a busca por nome continua na tela o tempo todo, e o convite para usar o cartão só aparece quando a câmera está mesmo funcionando.

### O totem tem uma tela de apresentação

Quando ninguém está usando, o totem mostra as fotos do refeitório num painel à esquerda e, à direita, o nome do sistema com **o cardápio do dia** em letras grandes. Dá para saber o que tem no almoço do outro lado do refeitório, sem encostar em nada.

Um toque em qualquer lugar da tela leva à busca — não é preciso acertar o botão redondo. Depois de um tempo parado, o totem volta sozinho para a apresentação.

As fotos ficam em `assets/fotos/`: é só colocar os arquivos na pasta, sem precisar editar nada antes. Sem fotos, o painel fica no azul da escola e todo o resto continua igual.

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

### A conta da sobra fecha

A cozinha informa no painel o cardápio do dia e quantos pratos preparou. Com isso, a tela passa a dizer não só quantos almoçaram, mas quanto sobrou — *"92 preparados · sobraram 18"* —, destacando quando a diferença é grande demais.

É a conta que o sistema existe para melhorar. Sem esse número, dava para saber quantos comeram, mas não quanto foi para o lixo.

### O painel da cozinha fica protegido

O totem abre em tela cheia, sem saída visível, porque fica sozinho numa fila cheia de gente. O painel da cozinha entra por três toques no rodapé ou um atalho de teclado, sempre com PIN.

---

### O que ainda não existe

- **Relatórios.** Cruzar o cardápio do dia com quantos apareceram — é assim que se descobre, por exemplo, que peixe traz menos gente. E acompanhar a sobra ao longo das semanas, não só no dia.

### Antes de a próxima fase valer a pena

A fila preferencial precisa ser combinada com a cozinha. O sistema mostra na tela quem confirmou; se ninguém for atendido primeiro por isso, confirmar não traz vantagem nenhuma e o aplicativo nasce sem motivo para ser usado.

---

### Para quem mexe no código

Servidor em Python com SQLite e totem em Tkinter. O servidor roda só com a biblioteca padrão; o totem usa Pillow (fotos), qrcode (cartões) e OpenCV (câmera), e degrada sem nenhum dos três. 156 testes automatizados.

Nesta versão o totem foi reescrito: existiu primeiro em JavaFX e passou nos testes, mas foi migrado para Python. A migração eliminou a regra de busca de nomes duplicada em duas linguagens, que era um erro esperando para acontecer na frente da fila.

Duas correções de desempenho, ambas medidas: o servidor passou a falar HTTP/1.1 com conexão reaproveitada, e a conexão do SQLite deixou de ser aberta e fechada a cada operação — no modo WAL, fechá-la disparava um *checkpoint* a cada escrita. Registrar um almoço caiu de 165 ms para 0,5 ms, e sincronizar cem almoços de 18,5 s para 237 ms.
