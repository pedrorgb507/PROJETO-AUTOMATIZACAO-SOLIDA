# -*- coding: utf-8 -*-
"""Apoio: log, pasta do mes/dia, registro do que ja foi feito, pendencias."""

import json
import os
import shutil
import time
import unicodedata
from datetime import datetime, timedelta

from .config import (HORA_VIRADA, MESES, PASTA_CONTROLE, PASTA_PENDENCIAS,
                     REGISTRO)


# ----------------------------------------------------------------------
# Texto
# ----------------------------------------------------------------------

def normalizar(texto):
    """'MARÇO', 'Marco', 'marco ' -> 'MARCO'. Para comparar nome de pasta."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.strip().upper()


# ----------------------------------------------------------------------
# Pasta do dia:  BASE\SETEMBRO\02
# ----------------------------------------------------------------------

def agora_util():
    """Data de trabalho: antes da HORA_VIRADA ainda conta como o dia anterior."""
    agora = datetime.now()
    if agora.hour < HORA_VIRADA:
        agora -= timedelta(days=1)
    return agora


def pasta_do_dia():
    """Nome da subpasta do dia, ex: '02'."""
    return "%02d" % agora_util().day


def nome_do_mes():
    """Nome canonico do mes de hoje, ex: 'SETEMBRO'."""
    return MESES[agora_util().month - 1]


def localizar_pasta_mes(base, criar=False):
    """
    Nome REAL da pasta do mes dentro de base, do jeito que esta escrita la
    (SETEMBRO, Maio, MARÇO...). Devolve None se nao existir e criar=False.
    """
    alvo = normalizar(nome_do_mes())
    try:
        for nome in os.listdir(base):
            if os.path.isdir(os.path.join(base, nome)) and normalizar(nome) == alvo:
                return nome
    except OSError:
        pass
    if criar:
        os.makedirs(os.path.join(base, nome_do_mes()), exist_ok=True)
        return nome_do_mes()
    return None


# ----------------------------------------------------------------------
# Log
# ----------------------------------------------------------------------

def log(msg, alerta=False):
    r"""Imprime na tela e grava em <PASTA_CONTROLE>\_log_ctp.txt."""
    linha = "[%s] %s%s" % (datetime.now().strftime("%d/%m %H:%M:%S"),
                           ">>> " if alerta else "", msg)
    print(linha, flush=True)
    try:
        os.makedirs(PASTA_CONTROLE, exist_ok=True)
        with open(os.path.join(PASTA_CONTROLE, "_log_ctp.txt"), "a",
                  encoding="utf-8") as f:
            f.write(linha + "\n")
    except Exception:
        pass


def anotar_pendencia(arquivo, motivo):
    """
    Registra um problema que precisa de gente.

    Fica no PC, junto do log, e NAO na pasta do CTP: la so entram as
    chapas. Alem de gravar, imprime um aviso grande na tela, para nao
    passar batido em quem esta olhando a janela do programa.
    """
    barra = "!" * 66
    print("")
    print(barra, flush=True)
    print("!!!  PENDENCIA - PRECISA DE VOCE", flush=True)
    print("!!!  arquivo: %s" % arquivo, flush=True)
    print("!!!  motivo : %s" % motivo, flush=True)
    print(barra, flush=True)
    print("")
    log("PENDENCIA: %s | %s" % (arquivo, motivo), alerta=True)
    anotar_no_arquivo(arquivo, motivo)


def anotar_no_arquivo(arquivo, motivo):
    """Uma linha no _PENDENCIAS.txt, sem o alarde na tela."""
    try:
        os.makedirs(PASTA_CONTROLE, exist_ok=True)
        with open(os.path.join(PASTA_CONTROLE, "_PENDENCIAS.txt"), "a",
                  encoding="utf-8") as f:
            f.write("%s | %s | %s" % (datetime.now().strftime("%d/%m %H:%M"),
                                      arquivo, motivo) + chr(10))
    except Exception:
        pass


def guardar_para_a_mao(caminho, nome_original):
    """
    Move para a PASTA_PENDENCIAS o arquivo que o programa nao deu conta.

    E o PDF que a Corel gerou. Guardando ele, o trabalho da conversao nao
    se perde: o operador abre esse PDF no Photoshop/InDesign, como sempre
    fez, em vez de converter o .cdr outra vez - que e a parte demorada.

    Devolve o caminho final, ou None se nem isso deu certo.
    """
    try:
        os.makedirs(PASTA_PENDENCIAS, exist_ok=True)
        base = os.path.splitext(os.path.basename(nome_original))[0]
        destino = nome_livre(PASTA_PENDENCIAS, base)
        shutil.move(caminho, destino)
        anotar_no_arquivo(os.path.basename(nome_original),
                          "PDF convertido guardado em %s" % destino)
        return destino
    except Exception as e:
        log("Nao consegui guardar o PDF em %s: %s" % (PASTA_PENDENCIAS, e),
            alerta=True)
        return None


def pendencias_abertas(limite=20):
    """Ultimas pendencias anotadas, a mais recente por ultimo."""
    try:
        with open(os.path.join(PASTA_CONTROLE, "_PENDENCIAS.txt"),
                  encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip()][-limite:]
    except OSError:
        return []


# ----------------------------------------------------------------------
# Registro do que ja foi processado
# ----------------------------------------------------------------------
# A pasta de entrada e compartilhada, entao nada e movido de la. Em vez
# disso guardamos nome + tamanho + data de modificacao. Se a arte for
# corrigida e regravada, a chave muda e o arquivo e refeito sozinho.

def chave_arquivo(caminho):
    st = os.stat(caminho)
    return "%s|%d|%d" % (os.path.basename(caminho), st.st_size, int(st.st_mtime))


def caminho_registro():
    return os.path.join(PASTA_CONTROLE, REGISTRO)


def carregar_registro():
    try:
        with open(caminho_registro(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def salvar_registro(reg):
    try:
        os.makedirs(PASTA_CONTROLE, exist_ok=True)
        tmp = caminho_registro() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(reg, f, ensure_ascii=False, indent=1)
        os.replace(tmp, caminho_registro())
    except OSError as e:
        log("Nao consegui gravar o registro: %s" % e, alerta=True)


# ----------------------------------------------------------------------
# Arquivos
# ----------------------------------------------------------------------

def arquivo_estavel(caminho):
    """True se o arquivo parou de crescer (terminou de copiar pela rede)."""
    try:
        a = os.path.getsize(caminho)
        time.sleep(2)
        return a == os.path.getsize(caminho) and a > 0
    except OSError:
        return False


def nome_livre(pasta, base):
    """Caminho de saida que ainda nao existe: X.pdf, X_v2.pdf, X_v3.pdf..."""
    alvo = os.path.join(pasta, base + ".pdf")
    n = 2
    while os.path.exists(alvo):
        alvo = os.path.join(pasta, "%s_v%d.pdf" % (base, n))
        n += 1
    return alvo
