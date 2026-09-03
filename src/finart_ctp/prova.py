# -*- coding: utf-8 -*-
"""
A prova impressa.

Por que nao mandar o PDF direto para a impressora:
o -dFitPage do Ghostscript 10.03.1 quebra quando precisa GIRAR a pagina
para encaixar (arte deitada indo para folha em pe). Como a chapa e
510x400 mm deitada e a impressora esta em A4 em pe, era exatamente o caso.

Solucao: nao usar encaixe nenhum. A prova ja e montada aqui no tamanho
e no sentido exatos da folha:

  1. rasteriza a arte com o Ghostscript (sem encaixe)
  2. monta um A4 EM PE, girando a arte deitada, com margem
  3. escreve a etiqueta do formato numa faixa em branco, fora da arte
  4. manda UMA folha por trabalho de impressao

O passo 4 e o que garante frente apenas. A impressora esta configurada em
duplex; um trabalho de duas paginas sairia frente e verso na mesma folha.
Mandando um trabalho por pagina, nao ha verso para a impressora usar, e um
arquivo de 2 paginas sai em 2 folhas, cada uma so na frente.

O que vai para a impressora e sempre esse A4 gerado aqui, nunca o arquivo
do cliente. Assim um PDF esquisito nao tem como derrubar a impressao.
"""

import glob
import os
import shutil
import subprocess
import tempfile

from .config import IMPRESSORA, PASTA_CONTROLE
from .ghostscript import GS, enviar_para_impressora

DPI_PROVA = 150
MARGEM_MM = 6
FAIXA_ROTULO_MM = 14        # faixa em branco no alto, so para a etiqueta
ALTURA_TEXTO_MM = 7
A4_MM = (210.0, 297.0)

FONTES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
]


def _rasterizar(pdf, pasta, dpi=DPI_PROVA):
    """Uma imagem por pagina. Devolve os caminhos, em ordem."""
    r = subprocess.run(
        [GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-sDEVICE=jpeg", "-dJPEGQ=85",
         "-r%d" % dpi, "-sOutputFile=" + os.path.join(pasta, "p%03d.jpg"), pdf],
        capture_output=True, text=True, timeout=900)
    imagens = sorted(glob.glob(os.path.join(pasta, "p*.jpg")))
    if not imagens:
        raise RuntimeError((r.stderr or "nao consegui rasterizar")[:300])
    return imagens


def _fonte(tamanho):
    """Arial em negrito se existir; senao a fonte embutida do Pillow."""
    from PIL import ImageFont
    for caminho in FONTES:
        if os.path.exists(caminho):
            try:
                return ImageFont.truetype(caminho, tamanho)
            except OSError:
                pass
    return ImageFont.load_default()


def montar_folha(im, dpi=DPI_PROVA, etiqueta=""):
    """
    Uma folha A4 em pe com a arte centralizada e a etiqueta no canto.

    A arte deitada e girada aqui. Quando ha etiqueta, o alto da folha
    ganha uma faixa em branco e a arte desce para caber embaixo dela:
    o texto nunca cai por cima do desenho.
    """
    from PIL import Image, ImageDraw

    def px(mm):
        return int(round(mm / 25.4 * dpi))

    faixa = px(FAIXA_ROTULO_MM) if etiqueta else 0
    if im.width > im.height:
        im = im.rotate(90, expand=True)          # deitada -> cabe em pe

    folha = Image.new("RGB", (px(A4_MM[0]), px(A4_MM[1])), "white")
    util = (folha.width - 2 * px(MARGEM_MM),
            folha.height - 2 * px(MARGEM_MM) - faixa)
    escala = min(util[0] / im.width, util[1] / im.height)
    im = im.resize((max(1, int(im.width * escala)),
                    max(1, int(im.height * escala))), Image.LANCZOS)
    folha.paste(im, ((folha.width - im.width) // 2,
                     px(MARGEM_MM) + faixa + (util[1] - im.height) // 2))

    if etiqueta:
        ImageDraw.Draw(folha).text(
            (px(MARGEM_MM), px(MARGEM_MM)), etiqueta,
            fill="black", font=_fonte(px(ALTURA_TEXTO_MM)))
    return folha


def _montar_a4(imagens, destino, dpi=DPI_PROVA, etiquetas=None):
    """
    Monta as imagens em folhas A4 EM PE, centralizadas e com margem.

    A folha e sempre retrato porque e assim que a impressora esta
    configurada: mandar uma pagina deitada obrigaria a impressora a girar,
    que e onde o Ghostscript quebra. Arte deitada e girada aqui mesmo.

    etiquetas: um texto por pagina, escrito numa faixa em branco no alto
    da folha. A arte e empurrada para baixo dessa faixa, entao o texto
    nunca cai por cima do desenho.
    """
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None

    etiquetas = etiquetas or []
    folhas = [montar_folha(Image.open(c).convert("RGB"), dpi,
                           etiquetas[i] if i < len(etiquetas) else "")
              for i, c in enumerate(imagens)]

    folhas[0].save(destino, "PDF", resolution=dpi, save_all=True,
                   append_images=folhas[1:])
    return destino


def imprimir(pdf, impressora=None, etiquetas=None):
    """
    Imprime a prova: uma folha A4 por pagina, sempre so na frente.

    etiquetas: texto do formato por pagina ("SOLIDA F4", "SOLIDA F2").

    Devolve (impressora, quantidade_de_folhas).
    """
    alvo = impressora or IMPRESSORA
    os.makedirs(PASTA_CONTROLE, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="prova_", dir=PASTA_CONTROLE)
    try:
        imagens = _rasterizar(pdf, tmp)
        etiquetas = etiquetas or []
        for i, imagem in enumerate(imagens):
            # um trabalho por folha: e assim que se garante frente apenas
            folha = _montar_a4([imagem], os.path.join(tmp, "f%03d.pdf" % i),
                               etiquetas=etiquetas[i:i + 1])
            enviar_para_impressora(folha, alvo)
        return alvo, len(imagens)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
