# -*- mode: python ; coding: utf-8 -*-
# =====================================================================
# SIARRN — servidor (PyInstaller)
#
#     pyinstaller siarrn-servidor.spec
#
# Resultado em dist/SIARRN-Servidor/
#
# O servidor não usa Pillow, OpenCV nem qrcode: é biblioteca padrão pura.
# Por isso tudo isso é excluído aqui — sem as exclusões o PyInstaller varre o
# ambiente e enfia dependências do totem num programa que nunca vai usá-las,
# levando o pacote de uns quinze megabytes para mais de cem.
# =====================================================================

from pathlib import Path

PROJETO = Path.cwd()

a = Analysis(
    ['siarrn.py'],
    pathex=[str(PROJETO)],
    binaries=[],
    datas=[('siarrn', 'siarrn')],
    hiddenimports=[
        'siarrn', 'siarrn.dados', 'siarrn.alunos', 'siarrn.refeicoes',
        'siarrn.previsao', 'siarrn.api', 'siarrn.seed', 'siarrn.texto',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'cv2', 'numpy', 'PIL', 'qrcode', 'tkinter',
        'matplotlib', 'scipy', 'pandas', 'PyQt5', 'PyQt6',
        'PySide2', 'PySide6', 'IPython', 'jupyter', 'notebook',
        'pytest', 'sphinx',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SIARRN-Servidor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    # Console à mostra de propósito: é nele que aparece o endereço que o totem
    # e os celulares precisam usar, além dos erros. O servidor fica numa sala,
    # não na frente dos alunos.
    console=True,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name='SIARRN-Servidor',
)
