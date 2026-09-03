# -*- coding: utf-8 -*-
"""
Processa um PDF do cliente.

O arquivo de origem NUNCA e movido nem apagado: a pasta e compartilhada.
Quem controla o que ja foi feito e o registro, em utils.py.
"""

import glob
import os
import re
import shutil
import tempfile
import time

from .config import (FORMATOS, IMPRESSORA, IMPRIMIR_ORIGINAL,
                     NOMES_TINTA, PASTA_CONTROLE, ROTULOS_PROVA,
                     TOLERANCIA_MM)
from .ghostscript import separar_tintas, tintas_por_pagina
from .prova import imprimir
from .nomes import extrair_oss, nome_saida
from .pdf_builder import montar_pdf
from .utils import anotar_pendencia, log, nome_livre


def medir_paginas(pdf):
    """[(largura_mm, altura_mm), ...] - uma por pagina, ja com /Rotate."""
    from pypdf import PdfReader
    r = PdfReader(pdf)
    medidas = []
    for p in r.pages:
        b = p.mediabox
        larg, alt = float(b.width) / 72 * 25.4, float(b.height) / 72 * 25.4
        if ((p.get("/Rotate") or 0) % 360) in (90, 270):
            larg, alt = alt, larg
        medidas.append((larg, alt))
    return medidas


def casar_formato(larg, alt):
    """Chave do formato cadastrado que bate com a medida, ou None."""
    medido = sorted([larg, alt])
    for chave in FORMATOS:
        alvo = sorted(chave)
        if (abs(medido[0] - alvo[0]) <= TOLERANCIA_MM and
                abs(medido[1] - alvo[1]) <= TOLERANCIA_MM):
            return chave
    return None


def identificar_formato(larg, alt):
    """(dpi, sufixo) do formato que bate, ou (None, None)."""
    chave = casar_formato(larg, alt)
    return FORMATOS[chave] if chave else (None, None)


def rotulo_prova(larg, alt):
    """Texto que vai no canto da folha de prova. Vazio se nao reconhecer."""
    return ROTULOS_PROVA.get(casar_formato(larg, alt), "")


def _gerar_chapa(origem, pasta_saida, base, pagina, dpi, larg, alt, usadas):
    """
    Separa uma pagina e monta o PDF final. Devolve o caminho gerado.

    Os TIFFs da separacao ficam SEMPRE no disco local: sao varios GB e
    passar isso pela rede tornaria tudo lento.
    """
    os.makedirs(PASTA_CONTROLE, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="ctp_p%d_" % pagina, dir=PASTA_CONTROLE)
    try:
        separar_tintas(origem, dpi, tmp, pagina)

        tifs = {}
        for tif in sorted(glob.glob(os.path.join(tmp, "s(*).tif"))):
            tinta = re.search(r"\(([^)]+)\)", os.path.basename(tif)).group(1)
            if tinta in NOMES_TINTA:
                letra = NOMES_TINTA[tinta]
                if letra not in usadas:
                    continue                      # separacao vazia, descarta
            else:
                letra = re.sub(r"[^A-Za-z0-9]+", "", tinta)[:16]
                log("   cor especial: %s" % tinta, alerta=True)
            tifs[letra] = tif

        if not tifs:
            raise RuntimeError("nenhuma tinta encontrada na pagina %d" % pagina)

        saida = nome_livre(pasta_saida, base)
        letras = montar_pdf(tifs, saida, larg, alt)
        return saida, letras
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def processar(caminho, pasta_saida):
    """
    Fluxo completo de um arquivo, pagina a pagina.

    Devolve {"status": "ok"|"erro", "saidas": [...], "motivo": "..."}.
    Nunca levanta excecao para cima.
    """
    nome = os.path.basename(caminho)
    resultado = {"status": "ok", "saidas": [], "motivo": "",
                 "impresso": None}

    def falhar(motivo):
        log("%s: %s" % (nome, motivo), alerta=True)
        anotar_pendencia(nome, motivo)
        resultado["status"] = "erro"
        resultado["motivo"] = motivo
        return resultado

    if not extrair_oss(nome):
        return falhar("nao achei numero de OS no nome")

    try:
        medidas = medir_paginas(caminho)
        tintas = tintas_por_pagina(caminho)
    except Exception as e:
        return falhar("PDF ilegivel: %s" % e)

    total = len(medidas)
    if not total:
        return falhar("PDF sem paginas")

    log("'%s': %d pagina(s)" % (nome, total))
    os.makedirs(pasta_saida, exist_ok=True)
    problemas = []

    # PASSO 1: prova impressa, com o arquivo original. So vale a pena
    # gastar papel se alguma pagina tiver formato conhecido.
    if IMPRIMIR_ORIGINAL and any(identificar_formato(l, a)[0] for l, a in medidas):
        try:
            etiquetas = [rotulo_prova(l, a) for l, a in medidas]
            _, folhas = imprimir(caminho, etiquetas=etiquetas)
            log("   impresso em %s (%d folha%s, so frente)"
                % (IMPRESSORA, folhas, "s" if folhas > 1 else ""))
            resultado["impresso"] = folhas
        except Exception as e:
            # Sem prova, sem chapa: segura o arquivo e tenta de novo depois.
            log("   NAO IMPRIMIU (%s): %s" % (IMPRESSORA, e), alerta=True)
            resultado["status"] = "espera"
            resultado["motivo"] = "impressora fora: %s" % e
            resultado["impresso"] = False
            return resultado

    for i, (larg, alt) in enumerate(medidas):
        dpi, sufixo = identificar_formato(larg, alt)
        base = nome_saida(nome, sufixo or "", i, total)

        if not dpi:
            motivo = ("pagina %d: %.0f x %.0f mm nao bate com nenhum formato"
                      % (i + 1, larg, alt))
            log("   " + motivo, alerta=True)
            anotar_pendencia(nome, motivo)
            problemas.append(motivo)
            continue

        usadas = tintas[i] if i < len(tintas) else set("CMYK")
        log("   p%d -> %s | %.0fx%.0f mm | %d dpi | tintas: %s"
            % (i + 1, base, larg, alt, dpi, "".join(sorted(usadas)) or "?"))

        # Sem a descricao no nome, duas artes da mesma OS batem de frente.
        if os.path.exists(os.path.join(pasta_saida, base + ".pdf")):
            aviso = ("ja existe %s.pdf (outra arte com a mesma OS); "
                     "este saiu como _v2" % base)
            log("   ATENCAO: " + aviso, alerta=True)
            anotar_pendencia(nome, aviso)

        inicio = time.time()
        try:
            saida, letras = _gerar_chapa(caminho, pasta_saida, base, i + 1,
                                         dpi, larg, alt, usadas)
        except Exception as e:
            motivo = "pagina %d: %s" % (i + 1, e)
            log("   FALHOU: %s" % motivo, alerta=True)
            anotar_pendencia(nome, motivo)
            problemas.append(motivo)
            continue

        mb = os.path.getsize(saida) / 1048576
        log("   OK em %.0fs: %s (%s, %.1f MB)"
            % (time.time() - inicio, os.path.basename(saida),
               "+".join(letras), mb))
        resultado["saidas"].append(os.path.basename(saida))

    if problemas:
        resultado["status"] = "erro"
        resultado["motivo"] = " ; ".join(problemas)
    return resultado
