# -*- coding: utf-8 -*-
"""Laco principal: vigia a pasta do dia e manda cada PDF para o processador."""

import os
import sys
import time
from datetime import datetime

from .config import (BASE_CTP, BASE_ENTRADA, BASE_ENTRADA_VOPRIX,
                     ESPERA_IMPRESSORA, INTERVALO, PASTA_CONTROLE,
                     SUBPASTA_SAIDA)
from .ghostscript import GS
from .processador import processar, processar_voprix
from .utils import (arquivo_estavel, carregar_registro, chave_arquivo,
                    localizar_pasta_mes, log, pasta_do_dia, salvar_registro)


def _pastas_do_dia(base_entrada):
    r"""
    (entrada, saida) de hoje para uma raiz de entrada, ou (None, None) se a
    pasta do dia ainda nao existe. A saida e sempre <BASE_CTP>\<MES>\<DIA>\FIA.
    """
    if not base_entrada:
        return None, None
    mes = localizar_pasta_mes(base_entrada)
    if not mes:
        return None, None
    dia = pasta_do_dia()
    entrada = os.path.join(base_entrada, mes, dia)
    if not os.path.isdir(entrada):
        return None, None
    # o CTP tem a propria arvore de meses, escrita do jeito dele
    mes_ctp = localizar_pasta_mes(BASE_CTP, criar=True)
    saida = os.path.join(BASE_CTP, mes_ctp, dia, SUBPASTA_SAIDA)
    return entrada, saida


def pastas_do_dia():
    """(entrada, saida) do fluxo SOLIDA."""
    return _pastas_do_dia(BASE_ENTRADA)


def varrer(entrada, saida, registro, espera=None, exts=(".pdf",),
           processa=processar):
    """
    Processa o que ainda nao foi feito. Devolve quantos rodaram.

    Se a impressora (ou o CorelDRAW, no fluxo VOPRIX) estiver fora, nada e
    gerado: a varredura para e so volta a tentar depois de ESPERA_IMPRESSORA
    segundos. Arquivo aberto na sessao do operador e apenas pulado, sem
    travar a fila.
    """
    espera = {"ate": 0, "avisado": False} if espera is None else espera
    if time.time() < espera["ate"]:
        return 0

    feitos = 0
    for nome in sorted(os.listdir(entrada)):
        if nome.startswith("~") or not nome.lower().endswith(tuple(exts)):
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

        resultado = processa(caminho, saida)

        if resultado["status"] == "pular":
            # Aberto no CorelDRAW do operador: nao mexemos. Nao entra no
            # registro; sai na proxima passada, quando a pessoa fechar.
            pulados = espera.setdefault("pulados", set())
            if chave not in pulados:
                pulados.add(chave)
                log("%s: %s - fica para depois" % (nome, resultado["motivo"]))
            continue

        if resultado["status"] == "espera":
            # Nada foi gerado. Nao entra no registro, para ser refeito
            # inteiro quando a impressora / o CorelDRAW voltar.
            espera["ate"] = time.time() + ESPERA_IMPRESSORA
            if not espera["avisado"]:
                espera["avisado"] = True
                log("PARADO: %s" % resultado["motivo"], alerta=True)
                log("        '%s' e os proximos ficam segurados, nenhuma "
                    "chapa sai." % nome, alerta=True)
                quanto = ("%d min" % (ESPERA_IMPRESSORA // 60)
                          if ESPERA_IMPRESSORA >= 60
                          else "%d s" % ESPERA_IMPRESSORA)
                log("        Resolva; tento de novo a cada %s, sozinho."
                    % quanto, alerta=True)
            return feitos

        if espera["avisado"]:
            espera["avisado"] = False
            log("Voltou. Retomando a fila.", alerta=True)

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
    if BASE_ENTRADA_VOPRIX:
        log("Entrada VOPRIX (.cdr): %s" % BASE_ENTRADA_VOPRIX)
        if not os.path.isdir(BASE_ENTRADA_VOPRIX):
            log("   ainda nao existe - o fluxo VOPRIX so liga quando ela "
                "aparecer.", alerta=True)
        try:
            import win32com.client          # noqa: F401
        except ImportError:
            log("   SEM pywin32 nesta maquina: os .cdr da VOPRIX vao ficar "
                "segurados. Rode 'pip install pywin32' ou ponha "
                "BASE_ENTRADA_VOPRIX = None.", alerta=True)
    log("Saida:   %s" % BASE_CTP)
    log("Os originais NAO sao movidos. Controle em %s" % PASTA_CONTROLE)
    log("Deixe esta janela aberta. Ctrl+C para parar.")

    registro = carregar_registro()
    log("Registro: %d arquivo(s) ja processados antes." % len(registro))
    espera = {"ate": 0, "avisado": False}
    espera_voprix = {"ate": 0, "avisado": False}

    visto = {}

    def ciclo(rotulo, entrada, saida, esp, **kw):
        if not entrada:
            if visto.get(rotulo) != "sem_pasta":
                visto[rotulo] = "sem_pasta"
                log("Esperando a pasta do dia (%s)." % rotulo)
            return
        if entrada != visto.get(rotulo):
            visto[rotulo] = entrada
            log("--- Vigiando %s: %s ---" % (rotulo, entrada))
            log("--- Gravando em: %s ---" % saida)
        varrer(entrada, saida, registro, esp, **kw)

    while True:
        try:
            ent, sai = pastas_do_dia()
            ciclo("SOLIDA", ent, sai, espera)

            if BASE_ENTRADA_VOPRIX:
                ent_v, sai_v = _pastas_do_dia(BASE_ENTRADA_VOPRIX)
                ciclo("VOPRIX", ent_v, sai_v, espera_voprix,
                      exts=(".cdr",), processa=processar_voprix)

            time.sleep(INTERVALO)
        except KeyboardInterrupt:
            log("Encerrado.")
            break
        except Exception as e:
            log("Erro no laco principal: %s" % e, alerta=True)
            time.sleep(INTERVALO)
