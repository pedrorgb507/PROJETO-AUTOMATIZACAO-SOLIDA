# -*- coding: utf-8 -*-
"""Tudo que fala com o Ghostscript."""

import os
import shutil
import subprocess

from .config import GS_EXE, IMPRESSORA


def achar_ghostscript():
    """Devolve o caminho do gswin64c.exe, ou None se nao existir."""
    if GS_EXE:
        return GS_EXE
    for c in ["gswin64c", "gswin32c", "gs"]:
        p = shutil.which(c)
        if p:
            return p
    for base in [r"C:\Program Files\gs", r"C:\Program Files (x86)\gs"]:
        if os.path.isdir(base):
            for v in sorted(os.listdir(base), reverse=True):
                exe = os.path.join(base, v, "bin", "gswin64c.exe")
                if os.path.exists(exe):
                    return exe
    return None


GS = achar_ghostscript()


def tintas_por_pagina(pdf):
    """
    Lista de sets, uma por pagina: [{'M','K'}, {'K'}, ...]

    O inkcov imprime uma linha por pagina, na ordem.
    """
    r = subprocess.run([GS, "-q", "-o", "-", "-sDEVICE=inkcov", pdf],
                       capture_output=True, text=True, timeout=3600)
    paginas = []
    for linha in r.stdout.splitlines():
        p = linha.split()
        if len(p) >= 5 and p[4] == "CMYK":
            usadas = set()
            for valor, letra in zip(p[:4], "CMYK"):
                if float(valor) > 0.0001:
                    usadas.add(letra)
            paginas.append(usadas)
    return paginas


def separar_tintas(pdf, dpi, pasta_tmp, pagina=1):
    """
    Roda o tiffsep em UMA pagina.
    Gera s(Cyan).tif, s(Magenta).tif, ... dentro de pasta_tmp.
    """
    r = subprocess.run(
        [GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-sDEVICE=tiffsep",
         "-dFirstPage=%d" % pagina, "-dLastPage=%d" % pagina,
         "-r%d" % dpi, "-sCompression=lzw",
         "-sOutputFile=" + os.path.join(pasta_tmp, "s.tif"), pdf],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "erro no Ghostscript")[:300])


def enviar_para_impressora(pdf, impressora=None, timeout=900):
    """
    Manda um PDF para uma impressora do Windows.

    Usa o proprio Ghostscript (device mswinpr2), entao nao depende de ter
    Acrobat instalado nem de qual programa abre PDF na maquina.

    Espere um PDF ja no tamanho E no sentido da folha: quem monta isso
    e o prova.py. Aqui nao ha encaixe nenhum, de proposito.
    """
    alvo = impressora or IMPRESSORA
    r = subprocess.run(
        [GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-dNoCancel",
         "-sDEVICE=mswinpr2",
         "-sOutputFile=%printer%" + alvo, pdf],
        capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "erro ao imprimir")[:300])
    return alvo
