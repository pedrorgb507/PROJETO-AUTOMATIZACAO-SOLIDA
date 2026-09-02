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
  3. manda UMA folha por trabalho de impressao

O passo 3 e o que garante frente apenas. A impressora esta configurada em
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
A4_MM = (210.0, 297.0)


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


def _montar_a4(imagens, destino, dpi=DPI_PROVA):
    """
    Monta as imagens em folhas A4 EM PE, centralizadas e com margem.

    A folha e sempre retrato porque e assim que a impressora esta configurada:
    mandar uma pagina deitada obrigaria a impressora a girar, que e onde o
    Ghostscript quebra. Arte deitada e girada aqui mesmo, na imagem.
    """
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None

    px = lambda mm: int(round(mm / 25.4 * dpi))
    folhas = []
    for caminho in imagens:
        im = Image.open(caminho).convert("RGB")
        if im.width > im.height:
            im = im.rotate(90, expand=True)      # deitada -> cabe em pe
        folha = Image.new("RGB", (px(A4_MM[0]), px(A4_MM[1])), "white")

        util = (folha.width - 2 * px(MARGEM_MM), folha.height - 2 * px(MARGEM_MM))
        escala = min(util[0] / im.width, util[1] / im.height)
        im = im.resize((max(1, int(im.width * escala)),
                        max(1, int(im.height * escala))), Image.LANCZOS)
        folha.paste(im, ((folha.width - im.width) // 2,
                         (folha.height - im.height) // 2))
        folhas.append(folha)

    folhas[0].save(destino, "PDF", resolution=dpi, save_all=True,
                   append_images=folhas[1:])
    return destino


def imprimir(pdf, impressora=None):
    """
    Imprime a prova: uma folha A4 por pagina, sempre so na frente.

    Devolve (impressora, quantidade_de_folhas).
    """
    alvo = impressora or IMPRESSORA
    os.makedirs(PASTA_CONTROLE, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="prova_", dir=PASTA_CONTROLE)
    try:
        imagens = _rasterizar(pdf, tmp)
        for i, imagem in enumerate(imagens):
            # um trabalho por folha: e assim que se garante frente apenas
            folha = _montar_a4([imagem], os.path.join(tmp, "f%03d.pdf" % i))
            enviar_para_impressora(folha, alvo)
        return alvo, len(imagens)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
