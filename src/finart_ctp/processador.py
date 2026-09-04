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
                     ROTULOS_PROVA_VOPRIX, TAMANHO_MAXIMO_MB, TOLERANCIA_MM)
from .ghostscript import separar_tintas, tintas_por_pagina
from .prova import imprimir
from .nomes import extrair_oss, nome_saida, nome_saida_voprix
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


def rotulo_prova(larg, alt, rotulos=ROTULOS_PROVA):
    """Texto que vai no canto da folha de prova. Vazio se nao reconhecer."""
    return rotulos.get(casar_formato(larg, alt), "")


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


def _falhar(nome, motivo):
    """Marca pendencia e devolve um resultado 'erro'. Nunca levanta."""
    log("%s: %s" % (nome, motivo), alerta=True)
    anotar_pendencia(nome, motivo)
    return {"status": "erro", "saidas": [], "motivo": motivo, "impresso": None}


def _nucleo(origem_pdf, nome_ref, pasta_saida, rotulos, nomear,
            colisao="outra arte com o mesmo nome"):
    """
    Miolo comum aos dois fluxos: mede, imprime a prova e gera as chapas.

    - origem_pdf : PDF a rasterizar/separar (na VOPRIX e um temporario)
    - nome_ref   : nome que aparece no log e nas pendencias
    - rotulos    : formato -> etiqueta da prova
    - nomear     : (indice, total, chave_formato, sufixo, tintas) -> nome de saida
    - colisao    : texto do aviso quando ja existe um arquivo com o mesmo nome

    Devolve {"status": "ok"|"erro"|"espera", "saidas": [...], "motivo": "..."}.
    Nunca levanta excecao para cima.
    """
    resultado = {"status": "ok", "saidas": [], "motivo": "", "impresso": None}

    try:
        medidas = medir_paginas(origem_pdf)
        tintas = tintas_por_pagina(origem_pdf)
    except Exception as e:
        return _falhar(nome_ref, "PDF ilegivel: %s" % e)

    total = len(medidas)
    if not total:
        return _falhar(nome_ref, "PDF sem paginas")

    log("'%s': %d pagina(s)" % (nome_ref, total))
    os.makedirs(pasta_saida, exist_ok=True)
    problemas = []

    # PASSO 1: prova impressa, com o arquivo original. So vale a pena
    # gastar papel se alguma pagina tiver formato conhecido.
    if IMPRIMIR_ORIGINAL and any(identificar_formato(l, a)[0] for l, a in medidas):
        try:
            etiquetas = [rotulo_prova(l, a, rotulos) for l, a in medidas]
            _, folhas = imprimir(origem_pdf, etiquetas=etiquetas)
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
        chave = casar_formato(larg, alt)
        if not chave:
            motivo = ("pagina %d: %.0f x %.0f mm nao bate com nenhum formato"
                      % (i + 1, larg, alt))
            log("   " + motivo, alerta=True)
            anotar_pendencia(nome_ref, motivo)
            problemas.append(motivo)
            continue

        dpi, sufixo = FORMATOS[chave]
        usadas = tintas[i] if i < len(tintas) else set("CMYK")
        base = nomear(i, total, chave, sufixo, usadas)
        log("   p%d -> %s | %.0fx%.0f mm | %d dpi | tintas: %s"
            % (i + 1, base, larg, alt, dpi, "".join(sorted(usadas)) or "?"))

        if os.path.exists(os.path.join(pasta_saida, base + ".pdf")):
            aviso = ("ja existe %s.pdf (%s); este saiu como _v2"
                     % (base, colisao))
            log("   ATENCAO: " + aviso, alerta=True)
            anotar_pendencia(nome_ref, aviso)

        inicio = time.time()
        try:
            saida, letras = _gerar_chapa(origem_pdf, pasta_saida, base, i + 1,
                                         dpi, larg, alt, usadas)
        except Exception as e:
            motivo = "pagina %d: %s" % (i + 1, e)
            log("   FALHOU: %s" % motivo, alerta=True)
            anotar_pendencia(nome_ref, motivo)
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


def processar(caminho, pasta_saida):
    """
    Fluxo de um PDF do cliente (SOLIDA), pagina a pagina.

    Devolve {"status": "ok"|"erro"|"espera", "saidas": [...], "motivo": "..."}.
    Nunca levanta excecao para cima.
    """
    nome = os.path.basename(caminho)

    mb = os.path.getsize(caminho) / 1048576
    if mb > TAMANHO_MAXIMO_MB:
        return _falhar(nome, "arquivo gigante: %.0f MB, acima do limite de "
                       "%d MB. Nao processei - precisa ser tratado a mao"
                       % (mb, TAMANHO_MAXIMO_MB))

    if not extrair_oss(nome):
        return _falhar(nome, "nao achei numero de OS no nome")

    # Sem a descricao no nome, duas artes da mesma OS batem de frente.
    def nomear(indice, total, chave, sufixo, tintas):
        return nome_saida(nome, sufixo or "", indice, total)

    return _nucleo(caminho, nome, pasta_saida, ROTULOS_PROVA, nomear,
                   colisao="outra arte com a mesma OS")


def processar_voprix(caminho, pasta_saida):
    """
    Fluxo de um .cdr da VOPRIX: converte pelo CorelDRAW e gera a chapa.

    O .cdr ja vem montado no tamanho da chapa. O nome de saida sai do
    proprio nome do arquivo (produto antes da medida), com o formato e as
    tintas na frente: 510x400_CM_VOPRIX_Envelope_Saco.

    Se o arquivo estiver aberto na sessao do operador, devolve status
    'pular' - nao mexemos nele e tentamos de novo na proxima passada. Se o
    CorelDRAW nao responder, devolve 'espera'.
    """
    from .corel import ArquivoEmUso, publicar_pdf

    nome = os.path.basename(caminho)

    mb = os.path.getsize(caminho) / 1048576
    if mb > TAMANHO_MAXIMO_MB:
        return _falhar(nome, "arquivo gigante: %.0f MB, acima do limite de "
                       "%d MB. Nao processei - precisa ser tratado a mao"
                       % (mb, TAMANHO_MAXIMO_MB))

    os.makedirs(PASTA_CONTROLE, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="voprix_", dir=PASTA_CONTROLE)
    pdf = os.path.join(tmp, os.path.splitext(nome)[0] + ".pdf")
    try:
        try:
            publicar_pdf(caminho, pdf)
        except ArquivoEmUso as e:
            return {"status": "pular", "saidas": [], "motivo": str(e),
                    "impresso": None}
        except Exception as e:
            log("   %s: CorelDRAW nao converteu (%s)" % (nome, e), alerta=True)
            return {"status": "espera", "saidas": [], "impresso": None,
                    "motivo": "CorelDRAW indisponivel: %s" % e}

        def nomear(indice, total, chave, sufixo, tintas):
            return nome_saida_voprix(nome, "%dx%d" % chave, tintas,
                                     indice, total)

        return _nucleo(pdf, nome, pasta_saida, ROTULOS_PROVA_VOPRIX, nomear,
                       colisao="outro arquivo com o mesmo nome de saida")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
