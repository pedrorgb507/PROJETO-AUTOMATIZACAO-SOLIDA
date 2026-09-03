# -*- coding: utf-8 -*-
"""Laco principal: vigia a pasta do dia e manda cada PDF para o processador."""

import os
import sys
import time
from datetime import datetime

from .config import (BASE_CTP, BASE_ENTRADA, ESPERA_IMPRESSORA,
                     IMPRESSORA, INTERVALO, PASTA_CONTROLE,
                     PASTA_DOWNLOADS, SUBPASTA_SAIDA)
from .downloads import pendentes, recolher
from .ghostscript import GS
from .processador import processar
from .utils import (arquivo_estavel, carregar_registro, chave_arquivo,
                    localizar_pasta_mes, log, pasta_do_dia, salvar_registro)


def pastas_do_dia(criar_entrada=False):
    r"""
    (entrada, saida) de hoje, ou (None, None) se a pasta de entrada ainda
    nao existe. A saida e <BASE_CTP>\<MES>\<DIA>\FIA.

    criar_entrada=True cria a pasta do dia do lado do cliente. So use
    quando ha arquivo esperando em Downloads para ser entregue: fora
    disso o programa nao cria nada na pasta compartilhada.
    """
    mes = localizar_pasta_mes(BASE_ENTRADA, criar=criar_entrada)
    if not mes:
        return None, None
    dia = pasta_do_dia()
    entrada = os.path.join(BASE_ENTRADA, mes, dia)
    if not os.path.isdir(entrada):
        if not criar_entrada:
            return None, None
        os.makedirs(entrada, exist_ok=True)
        log("Criei a pasta do dia na entrada: %s" % entrada, alerta=True)
    # o CTP tem a propria arvore de meses, escrita do jeito dele
    mes_ctp = localizar_pasta_mes(BASE_CTP, criar=True)
    saida = os.path.join(BASE_CTP, mes_ctp, dia, SUBPASTA_SAIDA)
    return entrada, saida


def varrer(entrada, saida, registro, espera=None):
    """
    Processa o que ainda nao foi feito. Devolve quantos rodaram.

    Se a impressora estiver fora, nada e gerado: a varredura para e so
    volta a tentar depois de ESPERA_IMPRESSORA segundos.
    """
    espera = {"ate": 0, "avisado": False} if espera is None else espera
    if time.time() < espera["ate"]:
        return 0

    # PASSO 0: o que o operador baixou do Teams entra na pasta do dia
    recolher(entrada)

    feitos = 0
    for nome in sorted(os.listdir(entrada)):
        if not nome.lower().endswith(".pdf") or nome.startswith("~"):
            continue
        caminho = os.path.join(entrada, nome)
        if not os.path.isfile(caminho):
            continue
        try:
            chave = chave_arquivo(caminho)
        except OSError:
            continue
        if chave in registro:
            continue
        if not arquivo_estavel(caminho):
            continue

        resultado = processar(caminho, saida)

        if resultado["status"] == "espera":
            # Nada foi gerado. Nao entra no registro, para ser refeito
            # inteiro quando a impressora voltar.
            espera["ate"] = time.time() + ESPERA_IMPRESSORA
            if not espera["avisado"]:
                espera["avisado"] = True
                log("PARADO: %s esta fora do ar." % IMPRESSORA, alerta=True)
                log("        '%s' e os proximos ficam segurados, nenhuma "
                    "chapa sai." % nome, alerta=True)
                quanto = ("%d min" % (ESPERA_IMPRESSORA // 60)
                          if ESPERA_IMPRESSORA >= 60
                          else "%d s" % ESPERA_IMPRESSORA)
                log("        Arrume a impressora; tento de novo a cada %s, "
                    "sozinho." % quanto, alerta=True)
            return feitos

        if espera["avisado"]:
            espera["avisado"] = False
            log("Impressora voltou. Retomando a fila.", alerta=True)

        resultado["quando"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        resultado["arquivo"] = nome
        registro[chave] = resultado
        salvar_registro(registro)
        feitos += 1
    return feitos


def main():
    if not GS:
        print("Ghostscript nao encontrado. Instale em ghostscript.com")
        sys.exit(1)
    try:
        import pypdf, PIL          # noqa: F401,E401
    except ImportError as e:
        print("Falta biblioteca (%s).\nRode:  pip install pypdf pillow" % e)
        sys.exit(1)
    if not os.path.isdir(BASE_ENTRADA):
        print("Nao achei a pasta de entrada:\n    %s\n"
              "Confira o BASE_ENTRADA em src/finart_ctp/config.py" % BASE_ENTRADA)
        sys.exit(1)

    log("Ghostscript: %s" % GS)
    log("Entrada: %s" % BASE_ENTRADA)
    log("Saida:   %s" % BASE_CTP)
    log("Os originais NAO sao movidos. Controle em %s" % PASTA_CONTROLE)
    log("Downloads vigiado: %s" % PASTA_DOWNLOADS)
    log("Deixe esta janela aberta. Ctrl+C para parar.")

    registro = carregar_registro()
    log("Registro: %d arquivo(s) ja processados antes." % len(registro))
    espera = {"ate": 0, "avisado": False}

    ultima = None
    while True:
        try:
            # se ha download esperando, vale criar a pasta do dia
            entrada, saida = pastas_do_dia(criar_entrada=bool(pendentes()))
            if not entrada:
                if ultima != "sem_pasta":
                    ultima = "sem_pasta"
                    log("Esperando a pasta do dia aparecer em %s" % BASE_ENTRADA)
                time.sleep(INTERVALO)
                continue
            if entrada != ultima:
                ultima = entrada
                log("--- Vigiando: %s ---" % entrada)
                log("--- Gravando em: %s ---" % saida)

            varrer(entrada, saida, registro, espera)
            time.sleep(INTERVALO)
        except KeyboardInterrupt:
            log("Encerrado.")
            break
        except Exception as e:
            log("Erro no laco principal: %s" % e, alerta=True)
            time.sleep(INTERVALO)
