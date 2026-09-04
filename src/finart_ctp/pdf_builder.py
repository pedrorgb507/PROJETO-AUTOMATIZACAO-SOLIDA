# -*- coding: utf-8 -*-
"""
Montagem do PDF final contendo APENAS as tintas usadas.

Substitui o que antes era feito na mao no Photoshop / InDesign.
"""

import zlib

from .config import CMYK_PDF, NOMES_TINTA


def _tint_transform(letras):
    """PostScript que converte as N tintas de volta para CMYK."""
    n = len(letras)
    corpo = []
    for canal in "CMYK":
        if canal in letras:
            pos = letras.index(canal)
            corpo.append("%d index" % (n - 1 - pos + len(corpo)))
        else:
            corpo.append("0")
    corpo.append("%d %d roll" % (n + 4, 4))
    corpo.extend(["pop"] * n)
    return "{ " + " ".join(corpo) + " }"


def _gravar(saida, objs, fluxos):
    """Escreve o PDF: objetos numerados a partir de 1, xref e trailer."""
    with open(saida, "wb") as f:
        f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for i, corpo in enumerate(objs, start=1):
            offsets.append(f.tell())
            f.write(b"%d 0 obj\n" % i)
            f.write(corpo)
            if i in fluxos:
                f.write(b"\nstream\n" + fluxos[i] + b"\nendstream")
            f.write(b"\nendobj\n")
        xref = f.tell()
        f.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1))
        for off in offsets:
            f.write(b"%010d 00000 n \n" % off)
        f.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
                % (len(objs) + 1, xref))


def _faixa_centralizada(im, y0, y1, alvo_w, dx, dy, fundo):
    """
    Um pedaco horizontal da imagem, ja no tamanho da chapa.

    O que sobra da arte e cortado, o que falta vira 'fundo' (255, que e
    branco tanto no tiffsep invertido quanto no tiffgray).
    """
    from PIL import Image
    faixa = Image.new(im.mode, (alvo_w, y1 - y0), fundo)
    origem_y0 = max(0, y0 - dy)                  # o que da arte cai aqui
    origem_y1 = min(im.height, y1 - dy)
    if origem_y1 > origem_y0:
        pedaco = im.crop((0, origem_y0, im.width, origem_y1))
        faixa.paste(pedaco, (dx, origem_y0 + dy - y0))    # paste corta sozinho
    return faixa


def _comprimir(imgs, w, h, linhas_bloco, alvo=None):
    """
    Entrelaca as bandas em faixas e comprime tudo de uma vez.

    Com 'alvo' (largura, altura em pixels), a arte entra CENTRALIZADA
    nesse tamanho: sobra cortada dos dois lados, falta preenchida de
    branco. E feito faixa a faixa, e nao numa imagem inteira - uma chapa
    de 1000 dpi tem 316 milhoes de pixels POR TINTA, e montar isso na
    memoria derrubaria a maquina.
    """
    n = len(imgs)
    alvo_w, alvo_h = alvo if alvo else (w, h)
    dx, dy = (alvo_w - w) // 2, (alvo_h - h) // 2
    centralizar = (alvo_w, alvo_h) != (w, h)

    comp = zlib.compressobj(6)
    partes = []
    for y0 in range(0, alvo_h, linhas_bloco):
        y1 = min(y0 + linhas_bloco, alvo_h)
        if centralizar:
            faixas = [_faixa_centralizada(im, y0, y1, alvo_w, dx, dy,
                                          255).tobytes() for im in imgs]
        else:
            faixas = [im.crop((0, y0, w, y1)).tobytes() for im in imgs]
        if n == 1:
            bloco = faixas[0]
        else:
            bloco = bytearray(len(faixas[0]) * n)
            for i, f in enumerate(faixas):
                bloco[i::n] = f
            bloco = bytes(bloco)
        partes.append(comp.compress(bloco))
        del faixas, bloco
    partes.append(comp.flush())
    return b"".join(partes)


def montar_pdf_cinza(tif, saida, larg_mm, alt_mm, linhas_bloco=256,
                     alvo=None):
    """
    Chapa unica em /DeviceGray, a partir do TIFF do tiffgray.

    Para arte de uma cor so. Aqui NAO ha /Decode invertido: o tiffgray ja
    entrega 0 = preto, 255 = branco, que e como o DeviceGray le.

    Devolve ["GRAY"], para quem chamou registrar o que saiu.
    """
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None

    im = Image.open(tif)
    if im.mode != "L":
        im = im.convert("L")
    w, h = im.size
    dados = _comprimir([im], w, h, linhas_bloco, alvo)
    if alvo:
        w, h = alvo
    im.close()

    lw = larg_mm / 25.4 * 72
    lh = alt_mm / 25.4 * 72
    conteudo = ("q %.4f 0 0 %.4f 0 0 cm /Im0 Do Q" % (lw, lh)).encode()

    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.4f %.4f] "
         "/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>"
         % (lw, lh)).encode(),
        ("<< /Type /XObject /Subtype /Image /Width %d /Height %d "
         "/ColorSpace /DeviceGray /BitsPerComponent 8 "
         "/Filter /FlateDecode /Length %d >>" % (w, h, len(dados))).encode(),
        b"<< /Length %d >>" % len(conteudo),
    ]
    _gravar(saida, objs, {4: dados, 5: conteudo})
    return ["GRAY"]


def montar_pdf(tifs, saida, larg_mm, alt_mm, linhas_bloco=256, alvo=None):
    """
    tifs: {"M": "caminho.tif", "K": "caminho.tif"} vindos do tiffsep
          (0 = tinta cheia, 255 = sem tinta -> invertido pelo /Decode)

    Devolve a lista de letras que entraram no PDF, na ordem.
    """
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None

    letras = [c for c in "CMYK" if c in tifs]
    letras += [k for k in tifs if k not in NOMES_TINTA.values()]
    n = len(letras)

    imgs = [Image.open(tifs[letra]) for letra in letras]
    w, h = imgs[0].size
    dados = _comprimir(imgs, w, h, linhas_bloco, alvo)
    if alvo:
        w, h = alvo
    for im in imgs:
        im.close()

    lw = larg_mm / 25.4 * 72
    lh = alt_mm / 25.4 * 72
    nomes = " ".join(CMYK_PDF.get(letra, "/" + letra) for letra in letras)
    decode = " ".join(["1 0"] * n)
    dominio = " ".join(["0 1"] * n)
    func = _tint_transform(letras).encode("latin-1")
    conteudo = ("q %.4f 0 0 %.4f 0 0 cm /Im0 Do Q" % (lw, lh)).encode()

    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.4f %.4f] "
         "/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>"
         % (lw, lh)).encode(),
        ("<< /Type /XObject /Subtype /Image /Width %d /Height %d "
         "/ColorSpace 6 0 R /BitsPerComponent 8 /Decode [%s] "
         "/Filter /FlateDecode /Length %d >>"
         % (w, h, decode, len(dados))).encode(),
        b"<< /Length %d >>" % len(conteudo),
        ("[/DeviceN [%s] /DeviceCMYK 7 0 R]" % nomes).encode(),
        ("<< /FunctionType 4 /Domain [%s] /Range [0 1 0 1 0 1 0 1] "
         "/Length %d >>" % (dominio, len(func))).encode(),
    ]
    _gravar(saida, objs, {4: dados, 5: conteudo, 7: func})
    return letras
