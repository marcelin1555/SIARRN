# -*- mode: python ; coding: utf-8 -*-
# =====================================================================
# SIARRN — totem e painel da cozinha (PyInstaller)
#
#     pyinstaller siarrn-totem.spec
#
# Resultado em dist/SIARRN-Totem/
#
# As fotos NÃO entram no pacote: vão para dist/SIARRN-Totem/assets/fotos,
# ao lado do executável, porque a escola precisa poder trocá-las sem
# recompilar nada. O build.py copia a pasta para lá depois.
# =====================================================================

from pathlib import Path

PROJETO = Path.cwd()

_icone = PROJETO / "assets" / "siarrn.ico"
ICONE = str(_icone) if _icone.exists() else None

a = Analysis(
    ['totem.py'],
    pathex=[str(PROJETO)],
    binaries=[],
    datas=[('siarrn', 'siarrn')],
    hiddenimports=[
        'siarrn', 'siarrn.ui_tema', 'siarrn.ui_totem', 'siarrn.ui_inicio',
        'siarrn.ui_gestao', 'siarrn.ui_dialogos', 'siarrn.ui_cartoes',
        'siarrn.base_local', 'siarrn.fila_offline', 'siarrn.cliente_api',
        'siarrn.config_totem', 'siarrn.cartoes', 'siarrn.leitor_qr',
        'siarrn.texto',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'pandas', 'PyQt5', 'PyQt6',
        'PySide2', 'PySide6', 'IPython', 'jupyter', 'notebook',
        'pytest', 'sphinx',
    ],
    noarchive=False,
)

# O OpenCV traz uma DLL de trinta megabytes do ffmpeg, usada para abrir e
# gravar ARQUIVOS de vídeo. O totem só liga a webcam, que no Windows entra
# pelos backends nativos (DSHOW/MSMF) — a DLL nunca é carregada, e sem ela o
# pacote encolhe quase um sexto.
a.binaries = [b for b in a.binaries if "opencv_videoio_ffmpeg" not in b[0].lower()]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SIARRN-Totem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    # Sem console: o totem fica em tela cheia na fila do almoço, e uma janela
    # preta de terminal atrás dele denunciaria que aquilo é um programa solto
    # num computador — além de dar a alunos um lugar por onde mexer.
    console=False,
    disable_windowed_traceback=False,
    icon=ICONE,
)

coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name='SIARRN-Totem',
)
