# -*- coding: utf-8 -*-
"""
Como o arquivo de saida se chama.

Nome de entrada:  "49513 - Cliente - miolo CAD2.pdf"
                   ^^^^^   ^^^^^   ^^^^^^^^^^^
                    OS    cliente   descricao

Regra: SO o numero da OS, mais nada. A descricao do arquivo de origem
("capa", "miolo CAD1") NAO entra no nome.

  510x400 mm  -> so a OS                   49572
  775x635 mm  -> OS + R1                   49576R1

  1 pagina    -> sem sufixo de pagina      49572
  2 paginas   -> F (frente) e V (verso)    49513R1 F / 49513R1 V
  3 ou mais   -> 1, 2, 3 ...               49513 1 / 49513 2 / 49513 3
"""

import os
import re

PROIBIDOS = re.compile(r'[\/:*?"<>|]')


def partes_do_nome(nome):
    """('49513', 'miolo CAD2') a partir de '49513 - Cliente - miolo CAD2.pdf'."""
    base = os.path.splitext(os.path.basename(nome))[0]
    seg = [p.strip() for p in base.split(" - ")]
    prefixo = seg[0]
    descricao = seg[-1] if len(seg) > 1 else ""
    return prefixo, descricao


def extrair_os(nome):
    """Primeiro numero de OS do nome, ou None. (usado nos avisos e no log)"""
    oss = extrair_oss(nome)
    return oss[0] if oss else None


def extrair_oss(nome):
    """
    Todos os numeros de OS do inicio do nome, na ordem.

    '49581 49582 49583 - Cliente - bottons.pdf' -> ['49581','49582','49583']
    """
    prefixo, _ = partes_do_nome(nome)
    limpo = re.sub(r"OS[\s_\-]*", " ", prefixo, flags=re.IGNORECASE)
    oss = re.findall(r"\d{4,8}", limpo)
    if oss:
        return oss
    base = os.path.splitext(os.path.basename(nome))[0]
    m = re.search(r"OS[\s_\-]*(\d{3,8})", base, re.IGNORECASE)
    return [m.group(1)] if m else []


def sufixo_pagina(indice, total):
    """'' para 1 pagina, F/V para 2, 1..n para 3 ou mais."""
    if total <= 1:
        return ""
    if total == 2:
        return "F" if indice == 0 else "V"
    return str(indice + 1)


def nome_saida(nome_original, sufixo_formato, indice=0, total=1):
    """
    Nome (sem .pdf) do PDF que vai para o CTP.

    >>> nome_saida("49513 - Cliente - capa.pdf", "")
    '49513'
    >>> nome_saida("49513 - Cliente - miolo CAD2.pdf", "R1", 1, 2)
    '49513R1 V'
    """
    oss = extrair_oss(nome_original)

    nome = (" ".join(oss) if oss else "SEM_OS") + sufixo_formato
    pag = sufixo_pagina(indice, total)
    if pag:
        nome += " " + pag

    nome = PROIBIDOS.sub("", nome)
    return re.sub(r"\s+", " ", nome).strip()


# ======================================================================
# VOPRIX
# ======================================================================
# Os arquivos vem em .cdr, ja montados no tamanho da chapa, e o nome
# segue outro padrao:
#
#     Envelope_Saco_23x31,5_Colegio_Unus.cdr
#     ^^^^^^^^^^^^^ ^^^^^^^ ^^^^^^^^^^^^
#       produto      medida     cliente
#
# O que vai para o CTP e o produto - o pedaco ANTES da medida - porque e
# por ele que se identifica a chapa na hora de gravar.
#
#     510x400_CM_VOPRIX_Envelope_Saco

MEDIDA = re.compile(r"^\d+(?:[.,]\d+)?(?:x\d+(?:[.,]\d+)?)+$", re.IGNORECASE)


def resumo_voprix(nome):
    """
    'Envelope_Saco_23x31,5_Colegio_Unus.cdr' -> 'Envelope_Saco'

    Tudo que vem antes da primeira medida do nome. Sem medida nenhuma,
    devolve o nome inteiro sem extensao.
    """
    base = os.path.splitext(os.path.basename(nome))[0]
    partes = base.split("_")
    for i, parte in enumerate(partes):
        if MEDIDA.match(parte):
            return "_".join(partes[:i]) or base
    return base


def cores_no_nome(tintas):
    """{'M','C'} -> 'CM'. Cor especial entra depois das quatro de escala."""
    escala = [c for c in "CMYK" if c in tintas]
    especiais = [t for t in sorted(tintas) if t not in "CMYK"]
    return "".join(escala + especiais)


def nome_saida_voprix(nome_original, formato, tintas, indice=0, total=1):
    """
    Nome (sem .pdf) do PDF que vai para o CTP.

    >>> nome_saida_voprix("Envelope_Saco_23x31,5_Colegio_Unus.cdr",
    ...                   "510x400", {"C", "M"})
    '510x400_CM_VOPRIX_Envelope_Saco'

    Com mais de uma pagina, o numero vai no fim: '... 01', '... 02'.
    """
    nome = "%s_%s_VOPRIX_%s" % (formato, cores_no_nome(tintas) or "K",
                                resumo_voprix(nome_original))
    if total > 1:
        nome += " %02d" % (indice + 1)
    nome = PROIBIDOS.sub("", nome)
    return re.sub(r"\s+", " ", nome).strip()
