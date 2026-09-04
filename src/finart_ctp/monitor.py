# -*- coding: utf-8 -*-
"""Laco principal: vigia a pasta do dia de cada cliente e manda o que aparecer."""

import os
import sys
import time
from datetime import datetime

from .config import (BASE_CTP, BASE_ENTRADA, BASE_ENTRADA_EMPORIO,
                     BASE_ENTRADA_FIALHO, BASE_ENTRADA_VOPRIX,
                     ESPERA_IMPRESSORA, IMPRESSORA, INTERVALO,
                     PASTA_CONTROLE, SUBPASTA_SAIDA)
from .ghostscript import GS
from .processador import EMPORIO, FIALHO, SOLIDA, VOPRIX, processar
from .utils import (arquivo_estavel, carregar_registro, chave_arquivo,
                    localizar_pasta_mes, log, pasta_do_dia, salvar_registro)


def clientes():
    r"""
    (nome, base_de_entrada, extensoes) de cada pasta vigiada, na ordem.

    Cada cliente tem a sua base - dentro dela, sempre MES\DIA -, e traz um
    tipo de arquivo. A SAIDA e a mesma para todos: a FIA do dia.

    O Fialho olha .pdf E .cdr de proposito: so o PDF vira chapa, mas o
    .cdr precisa ser VISTO para virar pendencia. Arquivo que o programa
    ignora em silencio e servico que ninguem lembra de fazer.
    """
    lista = [(SOLIDA, BASE_ENTRADA, (".pdf",))]
    if BASE_ENTRADA_VOPRIX:
        lista.append((VOPRIX, BASE_ENTRADA_VOPRIX, (".cdr",)))
    if BASE_ENTRADA_FIALHO:
        lista.append((FIALHO, BASE_ENTRADA_FIALHO, (".pdf", ".cdr")))
    if BASE_ENTRADA_EMPORIO:
        lista.append((EMPORIO, BASE_ENTRADA_EMPORIO, (".pdf",)))
    return lista


def pasta_entrada_do_dia(base):
    r"""<base>\<MES>\<DIA> de hoje, ou None se a pasta ainda nao existe."""
    mes = localizar_pasta_mes(base)
    if not mes:
        return None
    entrada = os.path.join(base, mes, pasta_do_dia())
    return entrada if os.path.isdir(entrada) else None


def pasta_saida_do_dia():
    r"""
    <BASE_CTP>\<MES>\<DIA>\FIA - a mesma para todos os clientes.

    O CTP tem a propria arvore de meses, escrita do jeito dele.
    """
    mes = localizar_pasta_mes(BASE_CTP, criar=True)
    return os.path.join(BASE_CTP, mes, pasta_do_dia(), SUBPASTA_SAIDA)


def pastas_do_dia(base=None):
    """(entrada, saida) de hoje, ou (None, None) sem pasta de entrada."""
    entrada = pasta_entrada_do_dia(base or BASE_ENTRADA)
    if not entrada:
        return None, None
    return entrada, pasta_saida_do_dia()


def varrer(entrada, saida, registro, espera=None, cliente=SOLIDA,
           extensoes=(".pdf",), adiados=None):
    """
    Processa o que ainda nao foi feito. Devolve quantos rodaram.

    Se a impressora estiver fora, nada e gerado: a varredura para e so
    volta a tentar depois de ESPERA_IMPRESSORA segundos.

    'adiados' guarda os arquivos que estao abertos no CorelDRAW do
    operador, so para o aviso nao se repetir a cada varredura.
    """
    espera = {"ate": 0, "avisado": False} if espera is None else espera
    if time.time() < espera["ate"]:
        return 0
    adiados = set() if adiados is None else adiados

    feitos = 0
    for nome in sorted(os.listdir(entrada)):
        if not nome.lower().endswith(tuple(extensoes)) or nome.startswith("~"):
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

        resultado = processar(caminho, saida, cliente)

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

        if resultado["status"] == "adiado":
            # Arte aberta no CorelDRAW de alguem. Nao entra no registro:
            # fica para a proxima passada, quando a pessoa fechar.
            if chave not in adiados:
                adiados.add(chave)
                log("'%s' esta aberto no CorelDRAW. Nao encosto nele; "
                    "converto quando fecharem." % nome, alerta=True)
            continue
        adiados.discard(chave)

        if espera["avisado"]:
            espera["avisado"] = False
            log("Impressora voltou. Retomando a fila.", alerta=True)

        resultado["quando"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        resultado["arquivo"] = nome
        resultado["cliente"] = cliente
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

    vigiadas = clientes()

    # A VOPRIX so anda com o pywin32: e por ele que se fala com o
    # CorelDRAW. Sem a biblioteca, seguimos so com a SOLIDA.
    if any(nome == VOPRIX for nome, _, _ in vigiadas):
        try:
            import win32com.client       # noqa: F401
        except ImportError:
            print("Sem pywin32 nesta maquina: nao da para converter os .cdr\n"
                  "da VOPRIX. Rode  pip install pywin32  e reabra.\n"
                  "Por enquanto, sigo so com a SOLIDA.")
            vigiadas = [c for c in vigiadas if c[0] != VOPRIX]

    if not any(os.path.isdir(base) for _, base, _ in vigiadas):
        print("Nao achei nenhuma pasta de entrada:")
        for nome, base, _ in vigiadas:
            print("    %-7s %s" % (nome, base))
        print("Confira o config_local.py (ou o config.py).")
        sys.exit(1)

    log("Ghostscript: %s" % GS)
    for nome, base, exts in vigiadas:
        log("Entrada %-7s %s  (%s)" % (nome, base, " ".join(exts)))
    log("Saida:   %s" % BASE_CTP)
    log("Os originais NAO sao movidos. Controle em %s" % PASTA_CONTROLE)
    log("Deixe esta janela aberta. Ctrl+C para parar.")

    registro = carregar_registro()
    log("Registro: %d arquivo(s) ja processados antes." % len(registro))
    espera = {"ate": 0, "avisado": False}
    adiados = set()

    ultima = {}
    while True:
        try:
            for nome, base, exts in vigiadas:
                entrada = pasta_entrada_do_dia(base)
                if not entrada:
                    if ultima.get(nome) != "sem_pasta":
                        ultima[nome] = "sem_pasta"
                        log("%s: esperando a pasta do dia aparecer em %s"
                            % (nome, base))
                    continue

                saida = pasta_saida_do_dia()
                if ultima.get(nome) != entrada:
                    ultima[nome] = entrada
                    log("--- Vigiando %s: %s ---" % (nome, entrada))
                    log("--- Gravando em: %s ---" % saida)

                varrer(entrada, saida, registro, espera, nome, exts, adiados)
            time.sleep(INTERVALO)
        except KeyboardInterrupt:
            log("Encerrado.")
            break
        except Exception as e:
            log("Erro no laco principal: %s" % e, alerta=True)
            time.sleep(INTERVALO)
