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

from . import ui_tema as tema
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
    def __init__(self, master, cliente, fila, ao_voltar) -> None:
        super().__init__(master, bg=tema.COR_FUNDO)
        self._cliente = cliente
        self._fila = fila
        self._ao_voltar = ao_voltar
        self._agendamento = None

        self._montar()

    # -----------------------------------------------------------------------
    # Montagem
    # -----------------------------------------------------------------------
    def _montar(self) -> None:
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

        for texto, comando in (("Voltar ao totem", self._voltar),
                               ("Atualizar agora", self.atualizar)):
            tk.Button(
                cabecalho, text=texto, command=comando,
                bg=tema.COR_SECUNDARIA, fg=tema.COR_TEXTO_CLARO,
                font=tema.fonte(12, forte=True), relief="flat", borderwidth=0,
                cursor="hand2", padx=tema.px(16), pady=tema.px(8),
                activebackground=tema._ajustar_cor(tema.COR_SECUNDARIA, 0.85),
                activeforeground=tema.COR_TEXTO_CLARO,
            ).pack(side="right", padx=(0, tema.px(20)))

        corpo = tk.Frame(self, bg=tema.COR_FUNDO)
        corpo.pack(fill="both", expand=True, padx=tema.px(40), pady=tema.px(24))

        self._montar_destaque(corpo)
        self._montar_blocos(corpo)
        self._montar_contagem(corpo)

        self._rodape = tk.Label(
            self, bg=tema.COR_FUNDO, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(tema.TAM_RODAPE),
        )
        self._rodape.pack(side="bottom", anchor="w", padx=tema.px(40), pady=tema.px(14))

    def _montar_destaque(self, pai: tk.Misc) -> None:
        bloco = tk.Frame(pai, bg=tema.COR_CARD,
                         highlightbackground=tema.COR_BORDA, highlightthickness=2)
        bloco.pack(fill="x")

        # Filete âmbar: o toque de destaque do SIGBEF, em dose pequena.
        tk.Frame(bloco, bg=tema.COR_DESTAQUE, height=tema.px(6)).pack(fill="x")

        tk.Label(
            bloco, text="PREPARAR HOJE", bg=tema.COR_CARD, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(tema.TAM_GESTAO_ROTULO, forte=True),
        ).pack(pady=(tema.px(16), 0))

        self._numero = tk.Label(
            bloco, text="—", bg=tema.COR_CARD, fg=tema.COR_PRIMARIA,
            font=tema.fonte(tema.TAM_GESTAO_NUMERO, forte=True),
        )
        self._numero.pack()

        self._explicacao = tk.Label(
            bloco, text="", bg=tema.COR_CARD, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(tema.TAM_GESTAO_DETALHE),
        )
        self._explicacao.pack(pady=(0, tema.px(18)))

    def _montar_blocos(self, pai: tk.Misc) -> None:
        faixa = tk.Frame(pai, bg=tema.COR_FUNDO)
        faixa.pack(fill="x", pady=tema.px(16))

        self._blocos = {}
        definicoes = (
            ("sim", tema.COR_SUCESSO, "confirmaram presença"),
            ("nao", tema.COR_AVISO, "avisaram ausência"),
            ("silenciosos", tema.COR_SECUNDARIA, "não declararam"),
        )

        for coluna, (chave, cor, rotulo) in enumerate(definicoes):
            bloco = tk.Frame(faixa, bg=cor)
            bloco.grid(row=0, column=coluna, sticky="ew", padx=(0 if coluna == 0 else tema.px(14), 0))
            faixa.columnconfigure(coluna, weight=1)

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
        bloco = tk.Frame(pai, bg=tema.COR_CARD,
                         highlightbackground=tema.COR_BORDA, highlightthickness=2)
        bloco.pack(fill="both", expand=True)

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

        self._comparacao = tk.Label(
            bloco, text="", bg=tema.COR_CARD, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(tema.TAM_GESTAO_DETALHE),
        )
        self._comparacao.pack(anchor="w", padx=tema.px(20), pady=(0, tema.px(14)))

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
