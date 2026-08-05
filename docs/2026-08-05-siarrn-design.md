# SIARRN — Sistema Integrado de Almoço e Refeição

> Documento de design. Escrito em 2026-08-05, antes da primeira linha de código.
>
> **Revisado no mesmo dia, depois da fase 1:** o totem foi escrito em JavaFX,
> funcionou e passou na verificação, mas o custo de atrito do Java (Gradle, JDK,
> JavaFX fora do JDK) não se pagou. **Passa a ser Python + Tkinter**, como o
> SIGBEF. O ganho vai além do conforto: a normalização de nome deixa de existir
> em duas linguagens, o tema do SIGBEF vira código reaproveitado em vez de
> referência, e o empacotamento passa a ser o PyInstaller que o projeto irmão já
> usa. Os trechos abaixo que citam JavaFX estão mantidos como registro da
> decisão anterior. O plano de migração está em `PROXIMOS-PASSOS.md`.

## Contexto

A escola serve almoço para 100+ alunos e não sabe quantos vão aparecer. Hoje alguém passa de sala em sala perguntando e anotando, depois repassa o total à cozinha. Já se tentou substituir isso por um Google Forms com prazo de envio; não durou meio ano.

O Forms falhou por um motivo específico e diagnosticável: **o registro não tinha consequência**. Dava para almoçar sem ter declarado, então declarar virou favor — e favor se esquece. Alunos burlavam, a adesão caiu, o prazo rígido excluía quem decidia tarde, e quem não tinha celular ficava de fora de qualquer jeito. O número que chegava à cozinha era ficção, e ninguém alimenta por muito tempo um número que sabe ser ficção.

A consequência prática é **sobra de comida**. O número declarado já vem inflado, e a cozinha ainda soma margem por medo de faltar. Desperdício é o preço do chute.

O SIARRN existe para dar à cozinha um número em que ela possa confiar. Faz isso medindo o que nunca foi medido — **quem realmente almoçou** — e usando essa verdade histórica como piso, com as declarações dos alunos por cima como refinamento.

Resultado esperado: em um mês, a cozinha troca a margem de medo por dados, e a sobra cai.

---

## Decisões de projeto

| Decisão | Escolha | Por quê |
|---|---|---|
| Ponto de verificação | Totem na fila, antes do balcão | Não há controle na entrada, mas ninguém almoça sem passar pela pessoa que serve. Esse é o gargalo real. |
| Custo pra cozinha | Zero | Quem está com a concha não digita nada. O aluno se identifica sozinho; a servente só olha a cor da tela. |
| Identificação | QR (papel ou app), com busca por nome como alternativa | O mesmo código serve impresso ou na tela. Quem esqueceu os dois passa pelo nome — a fila nunca trava. |
| Quem não confirmou | Passa igual, em fila não preferencial | Almoço é direito, não benefício condicionado. Bloquear negaria comida a aluno e o sistema seria desligado na primeira reclamação. |
| Cadastro | Auto-cadastro no 1º uso | Não depende de secretaria, autorização ou planilha. O projeto pode começar numa terça-feira qualquer. |
| Servidor | Python + SQLite, local na escola | Há Wi-Fi que os alunos alcançam. Sem custo de hospedagem, e funciona mesmo se a internet cair. |
| Totem + cozinha | ~~JavaFX~~ → **Python + Tkinter**, um programa com dois modos | Um executável só pra escola instalar. Compartilha código com o servidor e reaproveita o tema e o terminal de autoatendimento do SIGBEF. |
| App do aluno | Kotlin + Jetpack Compose | Nativo e bonito com pouco código. Material 3 e animação saem de graça; Kotlin já usado no `sigbef-mobile`. |
| Refeições | Só almoço, modelo aberto | Campo `turno` já existe; suportar lanche depois não exige migração. |

Nenhuma interface web no projeto. O servidor Python expõe apenas API JSON e o arquivo do APK para download.

**Riscos conhecidos:**

- JavaFX exige JVM e não roda em tablet Android. Se a escola liberar tablet em vez de PC, o totem precisa ser repensado.
- Leitura de QR por webcam (captura, foco, iluminação de refeitório) é a parte tecnicamente mais trabalhosa. O fallback por nome existe justamente para isso.
- Distribuição do APK sem Play Store passa pelo aviso de "fontes desconhecidas" e vai derrubar a adesão. **O desenho absorve isso**, porque declaração nunca foi requisito — quem não instalar entra na conta pelo histórico.
- São três frentes (servidor, JavaFX, Android) para uma pessoa. É mais do que o SIGBEF carrega hoje.

**Requisito não-técnico, e bloqueante:** a fila preferencial só existe se a cozinha combinar de atender primeiro quem está em verde. Sem esse acordo, o incentivo é só uma cor na tela. **Fechar isso com a cozinha antes de programar a fase 2.**

---

## A regra que sustenta o sistema

```
previsão = quem declarou SIM
         + Σ (taxa histórica de comparecimento de cada silencioso)
         − quem declarou NÃO
```

Quem declarou conta inteiro. Quem avisou ausência sai. **Quem não fez nada não é ignorado nem contado cheio — entra pela própria probabilidade histórica.**

É isso que impede o SIARRN de morrer como o Forms morreu. Com adesão zero às declarações ele vira média histórica pura e ainda entrega número útil; com adesão total vira contagem exata; no meio, degrada suavemente. **Não existe cenário em que ele quebra.** Adesão é ganho, nunca requisito.

```
taxa_historica(aluno) = consumos / refeições oferecidas, nas últimas 20
  se histórico < 3 refeições → usa a taxa média da escola
```

O fallback para a média da escola impede a primeira semana de cada aluno novo de envenenar a previsão.

---

## Identificação: um código, três caminhos

Cada aluno recebe um código aleatório curto no cadastro. Esse código vira QR — e o **mesmo** QR funciona:

1. **No app** — a tela inicial mostra o próprio QR, em brilho alto.
2. **Impresso em papel** — a tela de gestão gera e imprime folhas de cartões (QR + nome + turma) pra recortar. Custo: papel e tinta. Atende quem não tem celular.
3. **Esqueceu os dois** — busca por nome no totem, três letras, toca no seu nome.

O código é aleatório em vez de sequencial. Não é segurança (ninguém ganha nada se passando por outro, já que todos têm direito ao almoço) — é só evitar que alguém gere o cartão de outro por brincadeira.

---

## Estrutura

```
SIARRN/
├── siarrn.py                    ponto de entrada do servidor
├── siarrn/
│   ├── dados.py                 schema SQLite + acesso        (não depende de nada)
│   ├── alunos.py                cadastro, busca normalizada, geração de código
│   ├── refeicoes.py             declarações e consumos
│   ├── previsao.py              a regra acima — recebe números, devolve número
│   ├── api.py                   HTTP/JSON + download do APK
│   └── seed.py                  alunos fictícios pra teste de carga
├── totem/                       JavaFX (Gradle) — dois modos
│   └── src/main/java/.../
│       ├── App.java             escolhe o modo na inicialização
│       ├── totem/TotemView      tela cheia da fila
│       ├── gestao/GestaoView    painel da cozinha (entra por PIN)
│       ├── gestao/Cartoes       gera QR (ZXing) e imprime (PrinterJob)
│       ├── rede/ApiClient       fala com o servidor
│       ├── local/FilaOffline    grava e sincroniza
│       └── qr/LeitorQR          webcam + ZXing
├── app-aluno/                   Kotlin + Jetpack Compose
├── tests/
└── docs/
```

`previsao.py` **não toca no banco, de propósito.** É a peça que será ajustada dezenas de vezes conforme dados reais chegam, e precisa ser testável isoladamente.

### Modelo de dados

```sql
aluno(id, nome, nome_busca, turma, codigo, criado_em)
refeicao(id, data, turno, cardapio, previsto, preparado)
declaracao(aluno_id, refeicao_id, vai, declarado_em)
consumo(aluno_id, refeicao_id, registrado_em, origem)

UNIQUE(consumo.aluno_id, consumo.refeicao_id)
UNIQUE(aluno.codigo)
```

`nome_busca` é o nome normalizado (minúsculo, sem acento) — busca rápida e tolerante.
`origem` distingue QR de busca por nome — útil pra saber se vale investir em cartões melhores.
O índice único em `consumo` garante que ninguém seja contado duas vezes, **e é o que torna a sincronização do totem offline segura.**

### Contrato HTTP (JSON)

```
GET  /api/alunos/busca?q=joa   → [{id, nome, turma}]
GET  /api/alunos/codigo/{cod}  → {id, nome, turma, declarou}
GET  /api/alunos/todos         → base local do totem e impressão de cartões
POST /api/alunos               {nome, turma}  → devolve o código gerado
GET  /api/refeicao/hoje        → {id, data, turno, cardapio}
POST /api/consumo              {aluno_id, refeicao_id, registrado_em, origem}   idempotente
POST /api/declaracao           {aluno_id, refeicao_id, vai}
GET  /api/cozinha/hoje         → {previsto, sim, nao, silenciosos_estimados, consumidos}
GET  /siarrn.apk               instalação do app do aluno
```

A idempotência de `POST /api/consumo` permite ao totem reenviar a fila offline sem duplicar.

---

## Requisito de sobrevivência: o totem nunca trava

Se a rede oscilar ou o servidor cair com cem pessoas na fila, a fila não espera — e a cozinha nunca mais confia no sistema.

**O totem grava localmente e sincroniza depois, sempre.** Ele nunca depende do servidor para responder ao aluno: registra no arquivo local, mostra a tela colorida imediatamente, e envia quando der. Isso não é refinamento; é a diferença entre o projeto viver ou morrer no primeiro dia.

Para funcionar offline, o totem baixa a lista de alunos (id, nome, código, turma) no início de cada dia.

Demais casos da vida escolar:

- **Câmera não lê** (luz, foco, QR amassado) — dois segundos tentando e a tela oferece a busca por nome.
- **Esqueceu o cartão e o celular** — busca por nome, dez segundos.
- **Homônimos** — a turma aparece junto do nome na lista.
- **Passou duas vezes** — vê "já registrado", mas não é impedido de comer. O índice único cuida da contagem.
- **Nome não aparece** — auto-cadastro na própria tela do totem: nome + turma, e o código já é gerado.
- **Nome digitado errado** — corrigido e mesclado no modo gestão.
- **Aluno mexendo no totem** — o modo gestão entra por atalho discreto mais PIN de quatro dígitos. O totem fica em tela cheia, sem saída visível.

---

## Aparência

O projeto precisa parecer produto, porque é com ele que se pede o equipamento.

**Totem** — se resolve a três metros de distância: nome grande, cor ocupando a tela, zero texto explicativo. **Verde = confirmou** (fila preferencial). **Azul = não confirmou** (passa igual). Ninguém vê vermelho: o sistema nunca nega comida a aluno. JavaFX aceita CSS de verdade, e o SIGBEF já tem identidade visual que vale reaproveitar.

**Gestão** — responde uma pergunta só, quantos pratos preparar, com o resto em segundo plano.

**App do aluno** — três telas e nada mais: quem sou eu (uma vez), o dia de hoje (cardápio + vou/não vou), e meu QR. Material 3 com cor dinâmica, transições suaves, um botão grande. É o app mais simples do mundo, e é justamente por isso que dá pra deixar bonito.

---

## Fases

A ordem importa mais que o escopo: cada fase entrega valor sozinha, então uma parada no meio do caminho para valendo alguma coisa.

**Fase 1 — medir.** Servidor (`dados`, `alunos`, `refeicoes`, `api`), totem JavaFX com busca por nome, modo gestão com o painel da cozinha. Já produz o número real de almoços, que nunca existiu. **É a demonstração para pedir equipamento.**

**Fase 2 — identificar e prever.** Códigos, impressão de cartões, leitura de QR no totem, app Android com declaração e QR, `previsao` completa. *(Depende do acordo da fila preferencial com a cozinha.)*

**Fase 3 — aprender.** Cardápio, relatórios, correlação cardápio × comparecimento, administração de alunos.

A busca por nome vem antes do QR de propósito: ela já faz a fila andar, não custa nada, e garante que a fase 2 seja otimização e não pré-requisito. Pelo mesmo motivo o app fica na fase 2 — o sistema precisa provar valor antes de pedir a cem adolescentes que instalem um APK.

---

## Verificação

**Por peça:**

- `previsao` isolada, sem banco: adesão 0%, adesão 100%, aluno sem histórico, todos declarando ausência.
- Busca por nome: acentos, maiúsculas, nome parcial, dois homônimos na mesma turma.
- `POST /api/consumo` chamado duas vezes com os mesmos dados → um único registro.
- Código gerado é único, e o QR correspondente decodifica de volta para o mesmo aluno.

**Ponta a ponta**, com `seed.py` gerando 120 alunos fictícios:

1. `python siarrn.py` sobe o servidor.
2. Abrir o totem, entrar no modo gestão pelo PIN e conferir o painel da cozinha.
3. Instalar o APK num celular pela rede local, escolher um aluno e confirmar presença — o número muda na gestão.
4. Imprimir uma folha de cartões e conferir que os QR de papel leem no totem.
5. Registrar 100 consumos seguidos, misturando QR e busca por nome. **Cronometrar.** Se a fila não anda, nada mais importa.
6. Derrubar o servidor no meio dos registros: o totem tem que continuar respondendo normalmente.
7. Subir o servidor de volta e confirmar que a fila local sincronizou sem duplicar nada.
8. Conferir na gestão que o total bate com o que foi registrado.

O passo 6 é o mais importante da lista. É a falha que mata o projeto.

---

## Fora de escopo (v1)

Qualquer interface web; senha ou autenticação do aluno (todos têm direito ao almoço, não há vaga escassa a disputar); RFID/NFC (migração futura troca só o leitor); publicação na Play Store; integração com sistema da secretaria; controle de estoque ou de custo por prato.
