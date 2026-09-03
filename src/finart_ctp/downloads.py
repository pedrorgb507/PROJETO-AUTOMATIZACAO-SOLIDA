# -*- coding: utf-8 -*-
"""
Ponte entre o Teams e a pasta do dia.

Enquanto o download direto do Teams nao existe, o caminho e:
o operador baixa o anexo no Teams (cai em Downloads) e o programa move
o arquivo para a pasta do dia do cliente, com o mesmo nome. Dai em
diante e o processo de sempre.

So mexe em arquivo que PARECE ordem de servico: PDF cujo nome comeca
com o numero da OS e tem " - " logo depois, como

    49635 - Cliente - santinhos.pdf
    49581 49582 49583 - Cliente - bottons 7cm.pdf

Boleto, planilha, instalador e o resto do lixo que vive em Downloads
ficam onde estao.
"""

import os
import re
import shutil

from .config import MOVER_DO_DOWNLOADS, PADRAO_SERVICO, PASTA_DOWNLOADS
from .utils import arquivo_estavel, log

# extensoes de download pela metade
PARCIAIS = (".crdownload", ".part", ".partial", ".tmp", ".!ut")

# "49635 - Cliente - santinhos (1).pdf" -> tira o "(1)" que o navegador poe
COPIA = re.compile(r"\s*\(\d+\)$")

_servico = re.compile(PADRAO_SERVICO, re.IGNORECASE)
_avisados = set()          # para nao repetir o mesmo aviso a cada varredura


def e_servico(nome):
    """True se o nome tem cara de ordem de servico."""
    if not nome.lower().endswith(".pdf"):
        return False
    if nome.lower().endswith(PARCIAIS) or nome.startswith("~"):
        return False
    return bool(_servico.match(nome))


def nome_limpo(nome):
    """'49635 - Cliente - santinhos (1).pdf' -> '49635 - Cliente - santinhos.pdf'"""
    raiz, ext = os.path.splitext(nome)
    return COPIA.sub("", raiz).strip() + ext


def pendentes():
    """Nomes dos arquivos de servico esperando em Downloads."""
    try:
        return [n for n in sorted(os.listdir(PASTA_DOWNLOADS)) if e_servico(n)]
    except OSError:
        return []


def recolher(destino):
    """
    Leva os arquivos de servico de Downloads para a pasta do dia.

    Devolve a lista de nomes entregues. Nao sobrescreve nada: se ja
    existir arquivo com o mesmo nome e tamanho diferente, entrega como
    _v2; se for igual, entende que ja foi entregue e deixa quieto.
    """
    entregues = []
    for nome in pendentes():
        origem = os.path.join(PASTA_DOWNLOADS, nome)
        if not os.path.isfile(origem) or not arquivo_estavel(origem):
            continue

        alvo = os.path.join(destino, nome_limpo(nome))
        if os.path.exists(alvo):
            if os.path.getsize(alvo) == os.path.getsize(origem):
                if nome not in _avisados:
                    _avisados.add(nome)
                    log("'%s' ja esta na pasta do dia; deixei em Downloads."
                        % nome)
                continue
            raiz, ext = os.path.splitext(alvo)
            n = 2
            while os.path.exists("%s_v%d%s" % (raiz, n, ext)):
                n += 1
            alvo = "%s_v%d%s" % (raiz, n, ext)
            log("ja existia um '%s' diferente; entregando como '%s'"
                % (os.path.basename(nome_limpo(nome)), os.path.basename(alvo)),
                alerta=True)

        try:
            os.makedirs(destino, exist_ok=True)
            if MOVER_DO_DOWNLOADS:
                shutil.move(origem, alvo)
                verbo = "movido"
            else:
                shutil.copy2(origem, alvo)
                verbo = "copiado"
        except OSError as e:
            log("Nao consegui levar '%s' para a pasta do dia: %s" % (nome, e),
                alerta=True)
            continue

        log("Downloads -> pasta do dia: %s (%s)"
            % (os.path.basename(alvo), verbo))
        entregues.append(os.path.basename(alvo))
    return entregues
