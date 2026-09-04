# -*- coding: utf-8 -*-
"""Tudo que fala com o Ghostscript."""

import os
import shutil
import subprocess
import tempfile

from .config import GS_EXE, IMPRESSORA, PASTA_CONTROLE


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


# Abaixo disso a tinta e considerada ausente: sujeira de arredondamento.
LIMIAR_TINTA = 0.0001


def cobertura_por_pagina(pdf):
    """
    [{"C": 0.06081, "M": 0.06079, "Y": 0.06080, "K": 0.05444}, ...]

    O inkcov cru: quanto de cada tinta a pagina usa, de 0 a 1. Uma linha
    por pagina, na ordem.
    """
    r = subprocess.run([GS, "-q", "-o", "-", "-sDEVICE=inkcov", pdf],
                       capture_output=True, text=True, timeout=3600)
    paginas = []
    for linha in r.stdout.splitlines():
        p = linha.split()
        if len(p) >= 5 and p[4] == "CMYK":
            paginas.append(dict(zip("CMYK", [float(v) for v in p[:4]])))
    return paginas


def tintas_da_cobertura(cob):
    """{'C','K'} - as tintas que a pagina usa de verdade."""
    return set(l for l in "CMYK" if cob[l] > LIMIAR_TINTA)


def tintas_por_pagina(pdf):
    """Lista de sets, uma por pagina: [{'M','K'}, {'K'}, ...]"""
    return [tintas_da_cobertura(c) for c in cobertura_por_pagina(pdf)]


def sem_cor_gritante(pdf, pagina=1, dpi=72, tolerancia=96):
    """
    True se nenhum pixel da pagina tiver cor de verdade.

    E a segunda pergunta da decisao do cinza, e serve so para pegar um
    caso que a conta da cobertura nao pega: uma arte com vermelho de um
    lado e ciano do outro pode fechar C, M e Y no mesmo total e passar por
    neutra. Aqui isso reprova, porque em ALGUM pixel os canais estao longe
    um do outro.

    A folga e larga (96 de 255) de proposito. Arte cinza de verdade nao
    tem canal igualzinho pixel a pixel: a borda do texto sai com ruido de
    anti-aliasing - num arquivo real, ate 39 de diferenca em 6% dos
    pixels. Com folga apertada, arte cinza legitima seria reprovada.

    Roda em dpi baixo, que e barato e basta para essa decisao. Na duvida
    (Ghostscript reclamou, imagem nao saiu) devolve False: erra para o
    lado da quadricromia, que e o que sempre foi feito.
    """
    from PIL import Image, ImageChops
    Image.MAX_IMAGE_PIXELS = None

    os.makedirs(PASTA_CONTROLE, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="ctp_neutro_", dir=PASTA_CONTROLE)
    try:
        alvo = os.path.join(tmp, "p.tif")
        r = subprocess.run(
            [GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-sDEVICE=tiff32nc",
             "-dFirstPage=%d" % pagina, "-dLastPage=%d" % pagina,
             "-r%d" % dpi, "-sOutputFile=" + alvo, pdf],
            capture_output=True, text=True, timeout=900)
        if r.returncode != 0 or not os.path.exists(alvo):
            return False
        with Image.open(alvo) as im:
            c, m, y = im.split()[:3]
        for a, b in ((c, m), (c, y), (m, y)):
            if max(ImageChops.difference(a, b).getextrema()) > tolerancia:
                return False
        return True
    except Exception:
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def separar_cinza(pdf, dpi, pasta_tmp, pagina=1):
    """
    Rasteriza UMA pagina em escala de cinza. Devolve o caminho do TIFF.

    E o caminho da arte de uma cor so: o preto composto vira um cinza so,
    uma chapa so. Diferente do tiffsep, aqui 0 e preto e 255 e branco.
    """
    alvo = os.path.join(pasta_tmp, "cinza.tif")
    r = subprocess.run(
        [GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-sDEVICE=tiffgray",
         "-dFirstPage=%d" % pagina, "-dLastPage=%d" % pagina,
         "-r%d" % dpi, "-sCompression=lzw",
         "-sOutputFile=" + alvo, pdf],
        capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(alvo):
        raise RuntimeError((r.stderr or "erro no Ghostscript")[:300])
    return alvo


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
