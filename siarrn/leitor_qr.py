"""
SIARRN — Leitura do QR pela câmera

Uma webcam comum apontada para a fila. O aluno mostra o cartão (ou o celular) e
o almoço é registrado em cerca de um segundo, contra três ou quatro digitando o
nome. Com cem pessoas na fila, essa diferença é a fila inteira andando.

A regra que governa este módulo: **a câmera é um atalho, nunca um requisito.**
Se ela não existir, falhar ao abrir, cair no meio do almoço ou simplesmente não
enxergar o cartão amassado de alguém, nada trava — a busca por nome continua na
tela o tempo todo. Por isso nenhum erro aqui é propagado: vão para o arquivo
de registro e o leitor se marca como indisponível.

Decisões vindas de medição
--------------------------
A leitura tenta a imagem em três formas, nessa ordem: como veio, com contraste
equalizado, e binarizada de forma adaptativa. Cada etapa só roda se a anterior
falhar. Nos testes com o cartão pequeno, torto e fora de foco, foi justamente a
cadeia que salvou os casos difíceis — a primeira tentativa dá conta do caso
fácil, e o custo extra só aparece quando já ia falhar de qualquer jeito.
"""
from __future__ import annotations

import threading
import time

from . import log

try:
    import cv2
    import numpy as np
    OPENCV_DISPONIVEL = True
except ImportError:  # pragma: no cover - depende do ambiente
    OPENCV_DISPONIVEL = False

# Resolução de captura. Mais que isso não melhora a leitura de um QR a meio
# metro e só custa processamento numa máquina que pode ser velha.
LARGURA, ALTURA = 640, 480

# Quadros por segundo processados. A câmera entrega trinta; decodificar todos
# seria desperdício, e oito já pega o cartão no instante em que ele aparece.
QUADROS_POR_SEGUNDO = 8

# O mesmo código não é reenviado nesse intervalo. Sem isso, um cartão largado na
# frente da câmera dispararia o registro dezenas de vezes por minuto — o servidor
# ignoraria as repetições, mas a tela ficaria piscando a confirmação sem parar.
SEGUNDOS_ENTRE_REPETICOES = 6.0

# Se a câmera não abrir, tenta de novo de tempos em tempos: ela pode ter sido
# conectada depois de o totem já estar ligado.
SEGUNDOS_ENTRE_TENTATIVAS = 30.0


def decodificar(quadro) -> str:
    """Extrai o texto de um QR no quadro, ou string vazia.

    Recebe um quadro colorido da câmera e devolve o conteúdo do primeiro QR
    encontrado.
    """
    if not OPENCV_DISPONIVEL:
        return ""

    cinza = cv2.cvtColor(quadro, cv2.COLOR_BGR2GRAY) if quadro.ndim == 3 else quadro
    detector = cv2.QRCodeDetector()

    for preparar in (
        lambda imagem: imagem,
        cv2.equalizeHist,
        lambda imagem: cv2.adaptiveThreshold(
            imagem, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 5
        ),
    ):
        try:
            texto, _, _ = detector.detectAndDecode(preparar(cinza))
        except cv2.error:
            continue
        if texto:
            return texto.strip()

    return ""


class LeitorQR:
    """Câmera lendo QR em segundo plano.

    `ao_ler` é chamado **de uma thread de fundo**, com o texto lido. Quem usa
    precisa devolver o trabalho à interface (no Tk, com `after`).
    """

    def __init__(self, ao_ler, indice_camera: int = 0) -> None:
        self._ao_ler = ao_ler
        self._indice = indice_camera
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None
        self._camera = None
        self._ultimo_codigo = ""
        self._ultimo_instante = 0.0
        self.disponivel = False
        self.motivo_indisponivel = "" if OPENCV_DISPONIVEL else "OpenCV não instalado"

    # -----------------------------------------------------------------------
    # Ciclo de vida
    # -----------------------------------------------------------------------
    def iniciar(self) -> None:
        if not OPENCV_DISPONIVEL or self._thread is not None:
            return
        self._parar.clear()
        self._thread = threading.Thread(target=self._laco, daemon=True)
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        self._liberar()

    def _liberar(self) -> None:
        if self._camera is not None:
            try:
                self._camera.release()
            except cv2.error:
                pass
            self._camera = None
        self.disponivel = False

    # -----------------------------------------------------------------------
    # Captura
    # -----------------------------------------------------------------------
    def _abrir(self) -> bool:
        try:
            camera = cv2.VideoCapture(self._indice)
            if not camera.isOpened():
                camera.release()
                self.motivo_indisponivel = "câmera não encontrada"
                return False

            camera.set(cv2.CAP_PROP_FRAME_WIDTH, LARGURA)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTURA)
            # Buffer curto: o totem quer o quadro de agora, não o de dois
            # segundos atrás, que mostraria o cartão de quem já foi servido.
            camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            self._camera = camera
            self.disponivel = True
            self.motivo_indisponivel = ""
            return True
        except cv2.error as erro:
            self.motivo_indisponivel = str(erro) or "falha ao abrir a câmera"
            return False

    def _laco(self) -> None:
        intervalo = 1.0 / QUADROS_POR_SEGUNDO

        while not self._parar.is_set():
            if self._camera is None and not self._abrir():
                # Sem câmera o totem segue normal, com busca por nome. Tenta de
                # novo mais tarde, caso alguém a conecte durante o almoço.
                log.aviso(f"Leitor de QR indisponível: {self.motivo_indisponivel}")
                if self._parar.wait(SEGUNDOS_ENTRE_TENTATIVAS):
                    return
                continue

            try:
                capturou, quadro = self._camera.read()
            except cv2.error as erro:
                log.aviso(f"Falha ao ler da câmera: {erro}")
                self._liberar()
                continue

            if not capturou or quadro is None:
                # A câmera foi desconectada no meio do almoço. Solta e tenta
                # reabrir; a fila continua andando pela busca por nome.
                self._liberar()
                continue

            codigo = decodificar(quadro)
            if codigo:
                self._talvez_avisar(codigo)

            self._parar.wait(intervalo)

    def _talvez_avisar(self, codigo: str) -> None:
        agora = time.monotonic()
        mesmo_codigo = codigo == self._ultimo_codigo
        if mesmo_codigo and (agora - self._ultimo_instante) < SEGUNDOS_ENTRE_REPETICOES:
            return

        self._ultimo_codigo = codigo
        self._ultimo_instante = agora

        try:
            self._ao_ler(codigo)
        except Exception as erro:  # noqa: BLE001
            # Um erro no tratamento não pode matar a thread da câmera: ela
            # pararia de ler em silêncio pelo resto do almoço.
            log.aviso(f"Erro ao tratar o código lido: {erro}")

    def esquecer_ultimo(self) -> None:
        """Permite reler o mesmo código imediatamente.

        Usado quando o registro anterior não deu certo — a pessoa mostra o
        cartão de novo e não deveria esperar o intervalo de repetição.
        """
        self._ultimo_codigo = ""
        self._ultimo_instante = 0.0
