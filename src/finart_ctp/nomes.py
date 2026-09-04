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
import unicodedata

from .config import (PALAVRAS_MATERIAL, PALAVRAS_QUE_PEDEM_OLHO,
                     PALAVRAS_SERVICO_EMPORIO)

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


# Palavra que nao identifica ninguem e nao conta como nome.
LIGACAO = {"E", "DE", "DA", "DO", "DAS", "DOS", "COM", "SEM", "PARA"}


def _posicoes_de_nome(partes):
    """Onde estao os pedacos que valem como nome de gente ou de empresa."""
    return [i for i, p in enumerate(partes)
            if p and not p.isdigit() and not MEDIDA.match(p)
            and p.upper() not in LIGACAO]


def partes_voprix(nome):
    """
    (CLIENTE, produto) a partir do nome do arquivo.

    >>> partes_voprix("Panfleto_15,0x21,0_4_0_M3RIN.cdr")
    ('M3RIN', 'panfleto')
    >>> partes_voprix("Envelope_Saco_23x31,5_Colegio_Unus.cdr")
    ('COLEGIO_UNUS', 'envelope_saco')

    O cliente sao os DOIS ULTIMOS nomes do arquivo - ou so o ultimo,
    quando so ha um. Numero solto nao conta (a especificacao de cores
    '4_0', a data no fim) nem palavra de ligacao.

    O produto e o que vem antes da medida. Sem medida no nome, e tudo o
    que sobra na frente do cliente.
    """
    base = os.path.splitext(os.path.basename(nome))[0]
    partes = base.split("_")

    medida = next((i for i, p in enumerate(partes) if MEDIDA.match(p)), None)
    inicio = medida + 1 if medida is not None else 0
    cauda = partes[inicio:]

    posicoes = _posicoes_de_nome(cauda)
    escolhidas = posicoes[-2:] if len(posicoes) >= 2 else posicoes[-1:]
    cliente = "_".join(cauda[i] for i in escolhidas).upper()

    if medida is not None:
        produto = "_".join(partes[:medida])
    elif escolhidas:
        produto = "_".join(partes[:inicio + escolhidas[0]])
    else:
        produto = base
    return cliente, (produto or base).lower()


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
    '510x400_CM_VOPRIX_COLEGIO_UNUS_envelope_saco'

    CLIENTE em maiuscula na frente, produto em minuscula atras. O cliente
    vem primeiro porque e ele que identifica o trabalho: dois 'Panfleto'
    no mesmo dia ja bateram de frente na pasta do CTP e sairam como
    'Panfleto' e 'Panfleto_v2', sem ninguem saber qual era qual.

    Com mais de uma pagina, o numero vai no fim: '... 01', '... 02'.
    """
    cliente, produto = partes_voprix(nome_original)
    miolo = "%s_%s" % (cliente, produto) if cliente else produto
    nome = "%s_%s_VOPRIX_%s" % (formato, cores_no_nome(tintas) or "K", miolo)
    if total > 1:
        nome += " %02d" % (indice + 1)
    nome = PROIBIDOS.sub("", nome)
    return re.sub(r"\s+", " ", nome).strip()


# ======================================================================
# FIALHO BRINDES
# ======================================================================
# O nome de entrada nao segue padrao nenhum - e o titulo que a pessoa deu
# ao arquivo:
#
#     FORRO AGENDA unicidades  2027.pdf
#     MIOLO caderno sicoob montagen formato 48x66 9 imagem 2 chapas.pdf
#     divisoria colorida  montagem para agenda de dobra.pdf
#
# A chapa se chama pelo NOME PRINCIPAL do servico, que quase sempre e o
# cliente final - 'forro', 'miolo', 'caderno' sao tipo de material e nao
# identificam trabalho nenhum:
#
#     510x400_FIALHO_UNICIDADES 01
#     730x600_FIALHO_SICOOB 01
#
# Nao sobrando nome principal, o nome do arquivo inteiro serve, limpo:
#
#     510x400_FIALHO_DIVISORIA COLORIDA MONTAGEM PARA AGENDA DE DOBRA 01

MEDIDA_SOLTA = re.compile(r"^\d+X\d+$")


def limpo(texto):
    """'INTRODUÇÃO  unicidades' -> 'INTRODUCAO UNICIDADES'."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    so_util = re.sub(r"[^A-Za-z0-9 ]+", " ", sem_acento)
    return re.sub(r"\s+", " ", so_util).strip().upper()


def _e_descartavel(palavra):
    """Palavra que nao identifica o servico: material, medida, numero."""
    return (palavra in PALAVRAS_MATERIAL
            or palavra.isdigit()
            or len(palavra) == 1
            or bool(MEDIDA_SOLTA.match(palavra)))


def resumo_fialho(nome):
    """
    'FORRO AGENDA unicidades  2027.pdf' -> 'UNICIDADES'

    O que sobra depois de tirar tipo de material, medida e numero. Se nao
    sobrar nada, devolve o nome do arquivo inteiro, limpo - e melhor um
    nome comprido do que uma chapa sem nome.
    """
    base = limpo(os.path.splitext(os.path.basename(nome))[0])
    principais = [p for p in base.split(" ") if p and not _e_descartavel(p)]
    return " ".join(principais) if principais else base


def nome_saida_fialho(nome_original, formato, sequencia):
    """
    Nome (sem .pdf) da chapa que vai para o CTP.

    >>> nome_saida_fialho("FORRO AGENDA unicidades  2027.pdf", "510x400", 1)
    '510x400_FIALHO_UNICIDADES 01'

    A sequencia e do DIA e do trabalho, nao do arquivo: as 11 chapas de
    UNICIDADES de um dia saem 01 a 11 mesmo vindo de tres PDFs diferentes.
    Quem conta e o processador, olhando a pasta de saida.
    """
    nome = "%s_FIALHO_%s %02d" % (formato, resumo_fialho(nome_original),
                                  sequencia)
    nome = PROIBIDOS.sub("", nome)
    return re.sub(r"\s+", " ", nome).strip()


# ======================================================================
# EMPORIO PRINT
# ======================================================================
# Entra como a SOLIDA - PDF pronto, com a OS na frente - e sai como a
# VOPRIX, com formato, cores e cliente no nome:
#
#     01995 - CHAPA CAIXA 4796.pdf
#       ->  510x400_CMYK_EMPORIO_01995_CAIXA 4796_1
#           510x400_GRAY_EMPORIO_01995_CAIXA 4796_2
#
# Quem identifica o servico e a OS. A descricao vem junto, limpa das
# palavras que so dizem que aquilo e um trabalho de chapa.


def resumo_emporio(nome):
    """
    '01995 - CHAPA CAIXA 4796.pdf' -> 'CAIXA 4796'

    Tudo depois da OS, sem as palavras de servico e sem os tracos. Se
    nao sobrar nada, devolve vazio - ai o nome fica so com a OS, que ja
    identifica o trabalho.
    """
    base = os.path.splitext(os.path.basename(nome))[0]
    oss = extrair_oss(nome)
    if oss:
        # tira a OS e o que vier antes dela
        corte = base.find(oss[-1])
        if corte >= 0:
            base = base[corte + len(oss[-1]):]

    base = re.sub(r"[_\-]+", " ", base)
    palavras = [p for p in base.split(" ") if p]
    ficam = [p for p in palavras
             if limpo(p) not in PALAVRAS_SERVICO_EMPORIO]
    return re.sub(r"\s+", " ", " ".join(ficam)).strip()


def pede_olho(nome):
    """True quando o nome do arquivo pede conferencia humana (verniz)."""
    palavras = set(limpo(nome).split(" "))
    return bool(palavras & PALAVRAS_QUE_PEDEM_OLHO)


def nome_saida_emporio(nome_original, formato, tintas, indice=0, total=1):
    """
    Nome (sem .pdf) da chapa que vai para o CTP.

    >>> nome_saida_emporio("01995 - CHAPA CAIXA 4796.pdf", "510x400",
    ...                    set("CMYK"), 0, 2)
    '510x400_CMYK_EMPORIO_01995_CAIXA 4796_1'

    Com mais de uma pagina, o numero vai no fim depois de um _, que e
    como os operadores ja escrevem.
    """
    oss = extrair_oss(nome_original)
    partes = [formato, cores_no_nome(tintas) or "K", "EMPORIO",
              " ".join(oss) if oss else "SEM_OS"]
    descricao = resumo_emporio(nome_original)
    if descricao:
        partes.append(descricao)

    nome = "_".join(partes)
    if total > 1:
        nome += "_%d" % (indice + 1)
    nome = PROIBIDOS.sub("", nome)
    return re.sub(r"\s+", " ", nome).strip()
