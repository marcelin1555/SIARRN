# Onde paramos — 4 de agosto de 2026

Documento de retomada. Leia isto primeiro amanhã.

---

## Pronto, testado e commitado — não precisa mexer

O **servidor está completo e funcionando** (commit `14bc55b`). Python + SQLite, só biblioteca padrão, 70 testes passando:

- `siarrn/dados.py` — schema e acesso
- `siarrn/alunos.py` — auto-cadastro, busca por nome sem acento, código para o QR
- `siarrn/refeicoes.py` — declarações e consumos idempotentes
- `siarrn/previsao.py` — a regra de previsão, isolada do banco
- `siarrn/api.py` — HTTP/JSON
- `siarrn/seed.py` — 120 alunos fictícios com um mês de histórico

```bash
python siarrn.py --seed
python -m unittest discover -s tests -t .
```

Três correções de desempenho já estão dentro, todas medidas e não supostas: `synchronous=NORMAL` com WAL (158 ms → 5,9 ms por registro), HTTP/1.1 com keep-alive, e `garantir()` consultando antes de inserir. Sincronizar cem almoços caiu de 31,5 s para 807 ms. **Não desfazer nenhuma delas** — o comentário no código explica cada uma.

---

## A decisão de hoje: o totem sai do Java e vai para Python

O totem foi escrito em JavaFX, funcionou e passou no teste de queda de servidor. Mas o Java custou caro em atrito — Gradle, JDK, toolchain, JavaFX fora do JDK — e o custo não estava se pagando.

**Vai ser reescrito em Python + Tkinter**, como o SIGBEF.

### Por que isso é tecnicamente melhor, não só mais confortável

- **Uma linguagem no projeto inteiro.** Servidor e totem passam a compartilhar código de verdade: a normalização de nome deixa de existir duas vezes. Hoje ela está em `alunos.normalizar()` e de novo em `BaseLocal.normalizar()` — se as duas divergirem, um aluno some da busca do totem, e o erro aparece na frente da fila.
- **O tema do SIGBEF vira importável.** `ui_tema.py` deixa de ser referência e passa a ser código reaproveitado.
- **`ui_selfservice.py` do SIGBEF já é um terminal de autoatendimento em Tkinter.** É o mesmo problema do totem, já resolvido uma vez.
- **PyInstaller**, que você já usa e já tem script de build.
- **O design aprovado fica mais fácil, não mais difícil.** Ele é chapado, retangular, sem sombra e sem gradiente — que é exatamente onde o Tkinter é bom e o JavaFX exigia CSS. Os traços de contagem são um `Canvas` com `create_line`.

### O que fazer com `totem/`

Apagar. Está preservado no commit `14bc55b` se precisar consultar.

---

## O design aprovado

Segue o SIGBEF. As cores são as constantes de `sigbef/ui_tema.py`, sem aproximação:

| Uso | Valor |
|---|---|
| Faixa de cabeçalho, números de destaque | `#1F4E79` |
| Informação, blocos secundários | `#2E75B6` |
| Destaque em doses pequenas | `#F2A900` |
| Fundo | `#F5F7FA` |
| Confirmação, ação positiva | `#2E7D32` |
| Atenção | `#EF6C00` |
| Bordas | `#D5DAE0` |
| Texto | `#1A1A1A` |

**Regras de forma:** sem cantos arredondados, sem sombra, sem gradiente. Blocos de cor chapada. Tudo centralizado. Segoe UI / Segoe UI Semibold.

**Vocabulário de cor herdado do SIGBEF, com os mesmos significados:** verde é ação positiva, laranja é atenção, azul é informação. Quem já usa a biblioteca lê o refeitório sem aprender nada novo.

### Totem — busca

```
┌────────────────────────────────────────────┐
│  ███ faixa #1F4E79 ███                     │
│        Digite seu nome        (30px bold)  │
│  Depois toque no seu nome para registrar   │
├────────────────────────────────────────────┤
│  ┌──────────────────────────────────────┐  │
│  │ jo▏                       cursor âmbar│  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │ João Barbosa Rodrigues          1º A │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │ João Costa Souza                2º B │  │
│  └──────────────────────────────────────┘  │
│  120 alunos · sincronizado  [Não achei meu nome] │
└────────────────────────────────────────────┘
```

### Totem — confirmação

Tela inteira em `#2E7D32`, nome em branco 66px, régua âmbar curta embaixo, "Bom almoço!" e a turma. Sai sozinha depois de ~2,2 s.

### Cozinha

```
┌────────────────────────────────────────────┐
│  ███ faixa #1F4E79 ███  Cozinha            │
│  terça, 4 de agosto · Baião de dois        │
├────────────────────────────────────────────┤
│  ▔▔▔▔ filete âmbar ▔▔▔▔                    │
│           PREPARAR HOJE                    │
│              75 pratos       (66px #1F4E79)│
│                                            │
│  ┌─ verde ─┐ ┌─ laranja ─┐ ┌─ azul ─┐      │
│  │   37    │ │    18     │ │   65   │      │
│  │confirma-│ │ avisaram  │ │calados │      │
│  │ram      │ │ ausência  │ │~38 vêm │      │
│  └─────────┘ └───────────┘ └────────┘      │
│                                            │
│  JÁ ALMOÇARAM  ┼┼┼┼ ┼┼┼┼ ┼┼┼┼ III  33 de 75│
└────────────────────────────────────────────┘
```

**A assinatura são os traços de contagem.** Cada aluno que passa vira um risco, em grupos de cinco, desenhados com irregularidade proposital (ângulo e posição variando de forma determinística pelo índice) para parecer mão e não régua. É o gesto que o sistema aposentou — alguém riscando num papel de sala em sala — preservado como a forma de mostrar o dia. E funciona: dá pra ler a escala sem ler o número.

---

## Passo a passo de amanhã

1. **Apagar `totem/`** e o que o `.gitignore` tem de Java/Gradle.
2. **`siarrn/ui_tema.py`** — copiar de `sigbef/ui_tema.py`, cortando o que não se aplica (presets, personalização por banco). Só a paleta, as fontes e os helpers de estilo.
3. **`siarrn/base_local.py`** — cópia da lista de alunos em disco, com busca em memória. **Reusar `alunos.normalizar()`** em vez de reescrever.
4. **`siarrn/fila_offline.py`** — fila de almoços em JSON Lines. Comportamento a preservar do Java, que já foi testado:
   - grava e confirma na hora, nunca espera o servidor;
   - só remove da fila o que o servidor confirmou;
   - item sem `aluno_id` significa cadastro feito com o servidor fora — cria o aluno e registra o consumo na sincronização;
   - escrever em arquivo temporário e renomear, para queda de energia não corromper.
5. **`siarrn/ui_totem.py`** — tela da fila, conforme o desenho acima.
6. **`siarrn/ui_gestao.py`** — painel da cozinha, com o `Canvas` dos traços.
7. **`siarrn/totem.py`** — ponto de entrada, com o PIN e a alternância entre os dois modos.
8. Refazer a verificação: cem registros cronometrados, servidor derrubado no meio, servidor de volta, conferir que não duplicou.

---

## Comportamentos que não podem se perder na migração

O totem Java provou estes na prática — porte o comportamento, não o código:

- **A busca é local, em memória.** Nenhuma tecla digitada na fila depende do servidor. Medido: 4 ms.
- **O registro grava em disco e confirma na hora.** Medido: 0,6 ms por aluno. A sincronização é assunto de uma thread de fundo.
- **Ninguém vê vermelho.** O sistema nunca nega comida a aluno. Erro de rede é problema do totem, e o aluno não deveria nem perceber.
- **Tela cheia sem saída** no modo totem, e o modo gestão atrás de PIN, com atalho discreto (três toques no rodapé, ou `Ctrl+Alt+G`).
- **Reenviar não duplica.** A rota de consumo é idempotente do lado do servidor, então na dúvida o item continua na fila e tenta de novo.

---

## Pendência que não é código

A **fila preferencial precisa ser combinada com a cozinha** antes da fase 2. O software mostra quem confirmou; se a cozinha não atender essas pessoas primeiro, o incentivo não existe e a confirmação vira decoração.

---

## Depois disso (fase 2)

Cartões QR em papel, leitura por câmera, e o app do aluno. O app continua fora da fase 1 de propósito: só faz sentido pedir a cem adolescentes que instalem um APK depois que o sistema já estiver rodando e todo mundo tiver visto funcionar.
