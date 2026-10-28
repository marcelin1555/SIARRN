"""
SIARRN — O painel da cozinha

Responde uma pergunta só — **quantos pratos preparar** — e põe todo o resto em
segundo plano. O número grande é o produto inteiro do sistema; os blocos abaixo
existem para explicar de onde ele veio, porque um número sem explicação é
exatamente o que fez a escola parar de acreditar no sistema anterior.

Os blocos coloridos herdam o vocabulário do SIGBEF, com os mesmos significados:
verde é ação positiva, laranja é atenção, azul é informação.
"""
from __future__ import annotations

import threading
import tkinter as tk

from . import ui_formas as formas, ui_tema as tema
from .cliente_api import ErroDeRede

MILISSEGUNDOS_ATUALIZACAO = 15_000


class ContagemEmTracos(tk.Canvas):
    """A contagem do dia, riscada como se fosse à mão.

    É a assinatura do sistema. Antes do SIARRN, alguém passava de sala em sala
    riscando num papel quantos iam almoçar — e é esse gesto, o que o sistema
    aposentou, que virou a forma de mostrar o dia. Também funciona como
    informação: dá pra ler a escala de longe sem ler o número.

    O desvio de cada risco é **determinístico**, derivado do índice. Com desvio
    sorteado, a contagem inteira mudaria de aparência a cada atualização e
    ficaria tremendo na parede da cozinha.
    """

    ALTURA_RISCO = 26
    ESPACO_RISCO = 13
    ESPACO_GRUPO = 30
    ESPACO_LINHA = 44

    def __init__(self, pai: tk.Misc, **kwargs) -> None:
        super().__init__(
            pai, bg=tema.COR_CARD, highlightthickness=0,
            height=tema.px(self.ESPACO_LINHA * 2), **kwargs,
        )
        self._total = 0
        self.bind("<Configure>", lambda e: self._desenhar())

    def definir(self, total: int) -> None:
        if total != self._total:
            self._total = max(0, total)
            self._desenhar()

    @staticmethod
    def _desvio(semente: int, amplitude: float) -> float:
        """Deslocamento estável para um risco, a partir do seu índice."""
        embaralhado = (semente * 2_654_435_761) % 1_000
        return (embaralhado / 1_000.0) * 2 * amplitude - amplitude

    def _desenhar(self) -> None:
        self.delete("all")
        if self._total <= 0:
            return

        largura = max(self.winfo_width(), 1)
        altura_risco = tema.px(self.ALTURA_RISCO)
        espaco_risco = tema.px(self.ESPACO_RISCO)
        espaco_grupo = tema.px(self.ESPACO_GRUPO)
        espaco_linha = tema.px(self.ESPACO_LINHA)
        margem = tema.px(4)

        largura_grupo = espaco_risco * 4 + espaco_grupo
        grupos_por_linha = max(1, int((largura - margem * 2) // largura_grupo))
        linhas_disponiveis = max(1, int(self.winfo_height() // espaco_linha))
        grupos_cabem = grupos_por_linha * linhas_disponiveis

        grupos_totais = (self._total + 4) // 5
        grupos_desenhados = min(grupos_totais, grupos_cabem)
        # Se não couber tudo, o rótulo ao lado continua dizendo o número exato —
        # os riscos passam a ser escala, não inventário.
        riscos_a_desenhar = min(self._total, grupos_desenhados * 5)

        indice = 0
        for numero_grupo in range(grupos_desenhados):
            coluna = numero_grupo % grupos_por_linha
            linha = numero_grupo // grupos_por_linha
            base_x = margem + coluna * largura_grupo
            base_y = margem + linha * espaco_linha

            restantes = riscos_a_desenhar - numero_grupo * 5
            neste_grupo = min(5, restantes)

            for posicao in range(min(4, neste_grupo)):
                x = base_x + posicao * espaco_risco
                topo = base_y + self._desvio(indice, tema.px(2))
                fundo = base_y + altura_risco + self._desvio(indice + 7, tema.px(2))
                self.create_line(
                    x + self._desvio(indice + 3, tema.px(1)), topo,
                    x + self._desvio(indice + 11, tema.px(1)), fundo,
                    fill=tema.COR_PRIMARIA, width=tema.px(3), capstyle="round",
                )
                indice += 1

            if neste_grupo == 5:
                # O quinto risco cruza os quatro anteriores, como na contagem
                # feita à mão.
                self.create_line(
                    base_x - tema.px(5), base_y + altura_risco - tema.px(4),
                    base_x + espaco_risco * 3 + tema.px(6), base_y + tema.px(4),
                    fill=tema.COR_PRIMARIA, width=tema.px(3), capstyle="round",
                )
                indice += 1


class TelaGestao(tk.Frame):
    def __init__(self, master, cliente, fila, base, ao_voltar) -> None:
        super().__init__(master, bg=tema.COR_FUNDO)
        self._cliente = cliente
        self._fila = fila
        self._base = base
        self._ao_voltar = ao_voltar
        self._agendamento = None

        self._montar()

    # -----------------------------------------------------------------------
    # Montagem
    # -----------------------------------------------------------------------
    def _montar(self) -> None:
        # Azul chapado, e de propósito: num cabeçalho desta altura um degradê
        # seria imperceptível, e ele termina exatamente na cor com que a faixa
        # alta do totem termina. As duas telas se encontram no mesmo azul.
        cabecalho = tk.Frame(self, bg=tema.COR_PRIMARIA)
        cabecalho.pack(fill="x")

        textos = tk.Frame(cabecalho, bg=tema.COR_PRIMARIA)
        textos.pack(side="left", padx=tema.px(28), pady=tema.px(16))
        tk.Label(
            textos, text="Cozinha", bg=tema.COR_PRIMARIA, fg=tema.COR_TEXTO_CLARO,
            font=tema.fonte(tema.TAM_GESTAO_TITULO, forte=True),
        ).pack(anchor="w")
        self._subtitulo = tk.Label(
            textos, text="carregando…", bg=tema.COR_PRIMARIA, fg=tema.COR_PRIMARIA_SUAVE,
            font=tema.fonte(tema.TAM_GESTAO_ROTULO),
        )
        self._subtitulo.pack(anchor="w")

        # Empacotados na ordem inversa de propósito: `side="right"` empilha da
        # direita para a esquerda, então esta ordem é a que aparece na tela da
        # esquerda para a direita. A versão anterior lia ao contrário e
        # qualquer um que mexesse depois tropeçaria nisso.
        for texto, comando in (("Corrigir cadastros", self._abrir_cadastros),
                               ("Cartões dos alunos", self._abrir_cartoes),
                               ("Atualizar agora", self.atualizar),
                               ("Voltar ao totem", self._voltar)):
            formas.BotaoArredondado(
                cabecalho, text=texto, command=comando,
                bg=tema.COR_SECUNDARIA, font=tema.fonte(12, forte=True),
                padx=tema.px(18), pady=tema.px(9), fundo=tema.COR_PRIMARIA,
            ).pack(side="right", padx=(0, tema.px(16)), pady=tema.px(14))

        corpo = tk.Frame(self, bg=tema.COR_FUNDO)
        corpo.pack(fill="both", expand=True, padx=tema.px(34), pady=tema.px(14))

        self._rodape = tk.Label(
            self, bg=tema.COR_FUNDO, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(tema.TAM_RODAPE),
        )
        self._rodape.pack(side="bottom", anchor="w", padx=tema.px(34), pady=tema.px(10))

        # A ordem importa e não é cosmética: o `pack` atende os widgets na
        # ordem em que são declarados, e a contagem pede `expand=True`. Se ela
        # viesse antes, consumiria o que sobra e o formulário da cozinha —
        # a única parte desta tela em que alguém digita — ficaria fora da tela
        # numa máquina de 768px de altura.
        self._montar_destaque(corpo)
        self._montar_blocos(corpo)
        self._montar_registro(corpo)
        self._montar_contagem(corpo)

    def _montar_destaque(self, pai: tk.Misc) -> None:
        # Filete âmbar no topo: o toque de destaque do SIGBEF, em dose pequena.
        cartao = formas.CartaoArredondado(pai, filete=tema.COR_DESTAQUE)
        cartao.pack(fill="x")
        bloco = cartao.interior

        tk.Label(
            bloco, text="PREPARAR HOJE", bg=tema.COR_CARD, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(tema.TAM_GESTAO_ROTULO, forte=True),
        ).pack(pady=(tema.px(12), 0))

        self._numero = tk.Label(
            bloco, text="—", bg=tema.COR_CARD, fg=tema.COR_PRIMARIA,
            font=tema.fonte(tema.TAM_GESTAO_NUMERO, forte=True),
        )
        self._numero.pack()

        self._explicacao = tk.Label(
            bloco, text="", bg=tema.COR_CARD, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(tema.TAM_GESTAO_DETALHE),
        )
        self._explicacao.pack(pady=(0, tema.px(14)))

    def _montar_blocos(self, pai: tk.Misc) -> None:
        faixa = tk.Frame(pai, bg=tema.COR_FUNDO)
        faixa.pack(fill="x", pady=tema.px(12))

        self._blocos = {}
        definicoes = (
            ("sim", tema.COR_SUCESSO, "confirmaram presença"),
            ("nao", tema.COR_AVISO, "avisaram ausência"),
            ("silenciosos", tema.COR_SECUNDARIA, "não declararam"),
        )

        for coluna, (chave, cor, rotulo) in enumerate(definicoes):
            cartao = formas.CartaoArredondado(faixa, cor=cor)
            cartao.grid(row=0, column=coluna, sticky="ew",
                        padx=(0 if coluna == 0 else tema.px(14), 0))
            faixa.columnconfigure(coluna, weight=1)
            bloco = cartao.interior

            numero = tk.Label(
                bloco, text="—", bg=cor, fg=tema.COR_TEXTO_CLARO,
                font=tema.fonte(tema.TAM_GESTAO_BLOCO, forte=True),
            )
            numero.pack(pady=(tema.px(12), 0))

            detalhe = tk.Label(
                bloco, text=rotulo, bg=cor, fg=tema.COR_TEXTO_CLARO,
                font=tema.fonte(tema.TAM_GESTAO_BLOCO_TEXTO),
            )
            detalhe.pack(pady=(0, tema.px(12)))

            self._blocos[chave] = (numero, detalhe)

    def _montar_contagem(self, pai: tk.Misc) -> None:
        cartao = formas.CartaoArredondado(pai)
        cartao.pack(fill="both", expand=True)
        bloco = cartao.interior

        topo = tk.Frame(bloco, bg=tema.COR_CARD)
        topo.pack(fill="x", padx=tema.px(20), pady=(tema.px(14), 0))

        tk.Label(
            topo, text="JÁ ALMOÇARAM", bg=tema.COR_CARD, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(tema.TAM_GESTAO_ROTULO, forte=True),
        ).pack(side="left")

        self._servidos = tk.Label(
            topo, text="—", bg=tema.COR_CARD, fg=tema.COR_TEXTO,
            font=tema.fonte(tema.TAM_GESTAO_DETALHE, forte=True),
        )
        self._servidos.pack(side="right")

        self._contagem = ContagemEmTracos(bloco)
        self._contagem.pack(fill="both", expand=True, padx=tema.px(20), pady=tema.px(12))

        rodape_bloco = tk.Frame(bloco, bg=tema.COR_CARD)
        rodape_bloco.pack(fill="x", padx=tema.px(20), pady=(0, tema.px(14)))

        self._comparacao = tk.Label(
            rodape_bloco, text="", bg=tema.COR_CARD, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(tema.TAM_GESTAO_DETALHE),
        )
        self._comparacao.pack(side="left")

        # A sobra é o número que o projeto existe para reduzir. Fica ao lado da
        # contagem porque só significa alguma coisa em relação a ela.
        self._sobra = tk.Label(
            rodape_bloco, text="", bg=tema.COR_CARD, fg=tema.COR_TEXTO,
            font=tema.fonte(tema.TAM_GESTAO_DETALHE, forte=True),
        )
        self._sobra.pack(side="right")

    def _montar_registro(self, pai: tk.Misc) -> None:
        """Os dois dados que o sistema não tem como descobrir sozinho.

        O cardápio e a quantidade preparada só existem na cabeça de quem
        cozinhou. Sem eles o sistema sabe quantos comeram, mas não quanto foi
        jogado fora nem por quê — e essas são justamente as duas perguntas que
        levam à redução da sobra.
        """
        recipiente = tk.Frame(pai, bg=tema.COR_FUNDO)
        recipiente.pack(side="bottom", fill="x")

        # Um filete separa: o que está acima é o que o sistema sabe, o que está
        # abaixo é o que só a cozinha pode informar. Uma caixa a mais numa tela
        # já cheia de caixas não ajudaria ninguém.
        tk.Frame(recipiente, bg=tema.COR_BORDA, height=1).pack(
            fill="x", pady=(tema.px(14), 0)
        )

        faixa = tk.Frame(recipiente, bg=tema.COR_FUNDO)
        faixa.pack(fill="x", pady=(tema.px(10), 0))

        tk.Label(
            faixa, text="Cardápio de hoje", bg=tema.COR_FUNDO, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(tema.TAM_GESTAO_ROTULO),
        ).grid(row=0, column=0, sticky="w")

        self._campo_cardapio = tk.Entry(
            faixa, font=tema.fonte(tema.TAM_GESTAO_DETALHE),
            relief="solid", borderwidth=1, highlightthickness=0,
            bg="white", fg=tema.COR_TEXTO, insertbackground=tema.COR_DESTAQUE,
        )
        self._campo_cardapio.grid(row=1, column=0, sticky="ew", ipady=tema.px(6))

        tk.Label(
            faixa, text="Pratos preparados", bg=tema.COR_FUNDO, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(tema.TAM_GESTAO_ROTULO),
        ).grid(row=0, column=1, sticky="w", padx=(tema.px(14), 0))

        self._campo_preparado = tk.Entry(
            faixa, font=tema.fonte(tema.TAM_GESTAO_DETALHE), width=7, justify="center",
            relief="solid", borderwidth=1, highlightthickness=0,
            bg="white", fg=tema.COR_TEXTO, insertbackground=tema.COR_DESTAQUE,
        )
        self._campo_preparado.grid(row=1, column=1, sticky="w", padx=(tema.px(14), 0),
                                   ipady=tema.px(6))

        self._botao_salvar = formas.BotaoArredondado(
            faixa, text="Salvar", command=self._salvar_registro,
            bg=tema.COR_PRIMARIA, font=tema.fonte(12, forte=True),
            padx=tema.px(22), pady=tema.px(9),
        )
        self._botao_salvar.grid(row=1, column=2, sticky="w", padx=(tema.px(12), 0))

        self._aviso_registro = tk.Label(
            faixa, text="", bg=tema.COR_FUNDO, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(tema.TAM_GESTAO_ROTULO),
        )
        self._aviso_registro.grid(row=2, column=0, columnspan=3, sticky="w",
                                  pady=(tema.px(6), 0))

        faixa.columnconfigure(0, weight=1)

        self._campo_cardapio.bind("<Return>", lambda e: self._salvar_registro())
        self._campo_preparado.bind("<Return>", lambda e: self._salvar_registro())

    # -----------------------------------------------------------------------
    # Registro do que só a cozinha sabe
    # -----------------------------------------------------------------------
    def _salvar_registro(self) -> None:
        cardapio = self._campo_cardapio.get().strip()
        texto_preparado = self._campo_preparado.get().strip()

        preparado = None
        if texto_preparado:
            try:
                preparado = int(texto_preparado)
                if preparado < 0:
                    raise ValueError
            except ValueError:
                self._aviso_registro.configure(
                    text="Pratos preparados precisa ser um número inteiro.",
                    fg=tema.COR_AVISO,
                )
                self._campo_preparado.focus_set()
                return

        if not cardapio and preparado is None:
            self._aviso_registro.configure(text="Nada para salvar.", fg=tema.COR_TEXTO_SUAVE)
            return

        self._botao_salvar.configure(state="disabled")
        self._aviso_registro.configure(text="Salvando…", fg=tema.COR_TEXTO_SUAVE)
        threading.Thread(
            target=self._enviar_registro, args=(cardapio, preparado), daemon=True
        ).start()

    def _enviar_registro(self, cardapio: str, preparado: int | None) -> None:
        try:
            if cardapio:
                self._cliente.definir_cardapio(cardapio)
            if preparado is not None:
                self._cliente.definir_preparado(preparado)
        except ErroDeRede as erro:
            # Diferente do totem, aqui a falha precisa aparecer: a cozinha está
            # esperando a confirmação e pode digitar de novo mais tarde.
            self.after(0, lambda: self._registro_falhou(str(erro)))
            return
        self.after(0, self._registro_salvo)

    def _registro_salvo(self) -> None:
        self._botao_salvar.configure(state="normal")
        self._aviso_registro.configure(text="Salvo.", fg=tema.COR_SUCESSO)
        self._campo_preparado.delete(0, "end")
        self.atualizar()

    def _registro_falhou(self, motivo: str) -> None:
        self._botao_salvar.configure(state="normal")
        self._aviso_registro.configure(
            text=f"Não foi possível salvar ({motivo}). Tente de novo.", fg=tema.COR_AVISO
        )

    # -----------------------------------------------------------------------
    # Ciclo de vida
    # -----------------------------------------------------------------------
    def iniciar(self) -> None:
        """Começa a atualizar sozinho. A cozinha não deve precisar clicar em nada."""
        self.atualizar()
        self._reagendar()

    def _reagendar(self) -> None:
        self._agendamento = self.after(MILISSEGUNDOS_ATUALIZACAO, self._ciclo)

    def _ciclo(self) -> None:
        self.atualizar()
        self._reagendar()

    def parar(self) -> None:
        if self._agendamento is not None:
            self.after_cancel(self._agendamento)
            self._agendamento = None

    def _voltar(self) -> None:
        self.parar()
        self._ao_voltar()

    def _abrir_cadastros(self) -> None:
        from . import ui_cadastros
        ui_cadastros.abrir(self, self._cliente, self._base)

    def _abrir_cartoes(self) -> None:
        from . import ui_cartoes
        ui_cartoes.abrir(self, self._base)

    # -----------------------------------------------------------------------
    # Atualização
    # -----------------------------------------------------------------------
    def atualizar(self) -> None:
        # Consulta fora da thread da interface: se o servidor demorar, a janela
        # não pode congelar na frente de quem está esperando o número.
        threading.Thread(target=self._consultar, daemon=True).start()

    def _consultar(self) -> None:
        try:
            painel = self._cliente.painel_de_hoje()
        except ErroDeRede as erro:
            self.after(0, lambda: self._sem_servidor(str(erro)))
            return
        self.after(0, lambda: self._preencher(painel))

    def _preencher(self, painel: dict) -> None:
        previsto = painel.get("previsto", 0)
        consumidos = painel.get("consumidos", 0)

        self._numero.configure(text=f"{previsto} pratos")
        self._explicacao.configure(text=self._texto_da_confianca(painel.get("confianca")))

        self._subtitulo.configure(text=self._texto_do_subtitulo(painel))

        self._blocos["sim"][0].configure(text=str(painel.get("sim", 0)))
        self._blocos["nao"][0].configure(text=str(painel.get("nao", 0)))
        self._blocos["silenciosos"][0].configure(text=str(painel.get("silenciosos", 0)))
        self._blocos["silenciosos"][1].configure(
            text=f"não declararam · uns {round(painel.get('silenciosos_estimados', 0))} virão"
        )

        self._contagem.definir(consumidos)
        self._servidos.configure(text=f"{consumidos} de {previsto}")
        self._comparacao.configure(text=self._texto_da_comparacao(previsto, consumidos))

        texto_sobra, cor_sobra = self._texto_da_sobra(painel.get("preparado"), consumidos)
        self._sobra.configure(text=texto_sobra, fg=cor_sobra)
        self._mostrar_cardapio_atual(painel.get("cardapio") or "")

        self._rodape.configure(
            text=f"Atualizado agora  ·  {painel.get('total_alunos', 0)} alunos na base"
                 f"  ·  {self._texto_dos_pendentes()}"
        )

    @staticmethod
    def _texto_do_subtitulo(painel: dict) -> str:
        cardapio = (painel.get("cardapio") or "").strip()
        data = painel.get("data", "")
        return f"{data} · {cardapio}" if cardapio else f"{data} · cardápio não informado"

    @staticmethod
    def _texto_da_confianca(confianca: str | None) -> str:
        return {
            "boa": "Baseado no hábito observado dos alunos.",
            "parcial": "Ainda apoiado na média da escola para boa parte dos alunos.",
            "sem_dados": "Sem histórico ainda — hoje o sistema conta todo mundo.",
        }.get(confianca or "", "")

    @staticmethod
    def _texto_da_comparacao(previsto: int, consumidos: int) -> str:
        """A frase que fecha o ciclo do dia.

        Só faz sentido depois que a fila passou: comparar previsão com consumo
        às onze da manhã diria apenas que ninguém almoçou ainda.
        """
        if consumidos == 0:
            return "A comparação entre previsto e servido aparece conforme a fila anda."
        diferenca = consumidos - previsto
        if diferenca == 0:
            return "A previsão bateu exatamente com o que foi servido."
        if diferenca < 0:
            return f"Até agora, {abs(diferenca)} a menos que o previsto."
        return f"Já passou {diferenca} do previsto."

    @staticmethod
    def _texto_da_sobra(preparado, consumidos: int) -> tuple[str, str]:
        """A conta que o sistema existe para melhorar.

        Enquanto a cozinha não informar quanto preparou, dá para saber quantos
        comeram mas não quanto foi para o lixo — e é o desperdício, não a
        contagem, que motivou o projeto.

        Faltar é sinalizado com a mesma cor de atenção que sobrar muito: aluno
        sem almoço é pior que comida jogada fora, e as duas coisas pedem
        correção no dia seguinte.
        """
        if not isinstance(preparado, int):
            return "informe quanto foi preparado", tema.COR_TEXTO_SUAVE

        diferenca = preparado - consumidos

        if diferenca < 0:
            faltaram = abs(diferenca)
            return f"faltaram {faltaram} " + ("prato" if faltaram == 1 else "pratos"), tema.COR_AVISO
        if diferenca == 0:
            return f"{preparado} preparados · não sobrou nada", tema.COR_SUCESSO

        # Uma sobra pequena é margem de segurança razoável; grande é desperdício.
        cor = tema.COR_AVISO if diferenca > max(3, preparado * 0.10) else tema.COR_SUCESSO
        return f"{preparado} preparados · sobraram {diferenca}", cor

    def _mostrar_cardapio_atual(self, cardapio: str) -> None:
        """Traz o cardápio já salvo para o campo, sem atropelar quem digita.

        O painel se atualiza sozinho a cada quinze segundos; sobrescrever o
        campo nesse intervalo apagaria o que a cozinha estivesse escrevendo.
        """
        if not cardapio:
            return
        if self._campo_cardapio.get().strip():
            return
        if self.focus_get() is self._campo_cardapio:
            return
        self._campo_cardapio.insert(0, cardapio)

    def _texto_dos_pendentes(self) -> str:
        pendentes = self._fila.pendentes()
        return "fila sincronizada" if pendentes == 0 else f"{pendentes} almoços a enviar"

    def _sem_servidor(self, motivo: str) -> None:
        self._explicacao.configure(
            text="Sem contato com o servidor — mostrando o último número conhecido."
        )
        self._rodape.configure(
            text=f"Servidor fora do ar ({motivo})  ·  {self._texto_dos_pendentes()}"
        )
