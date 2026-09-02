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


def montar_pdf(tifs, saida, larg_mm, alt_mm, linhas_bloco=256):
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

    imgs = [Image.open(tifs[l]) for l in letras]
    w, h = imgs[0].size

    comp = zlib.compressobj(6)
    partes = []
    for y0 in range(0, h, linhas_bloco):
        y1 = min(y0 + linhas_bloco, h)
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
    dados = b"".join(partes)
    for im in imgs:
        im.close()

    lw = larg_mm / 25.4 * 72
    lh = alt_mm / 25.4 * 72
    nomes = " ".join(CMYK_PDF.get(l, "/" + l) for l in letras)
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
    fluxos = {4: dados, 5: conteudo, 7: func}

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
    return letras
