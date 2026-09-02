# -*- coding: utf-8 -*-
"""Apoio: log, pasta do mes/dia, registro do que ja foi feito, pendencias."""

import json
import os
import time
import unicodedata
from datetime import datetime, timedelta

from .config import HORA_VIRADA, MESES, PASTA_CONTROLE, REGISTRO


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


def anotar_pendencia(pasta, arquivo, motivo):
    """Escreve o problema no _PENDENCIAS.txt da pasta de saida do dia."""
    try:
        os.makedirs(pasta, exist_ok=True)
        with open(os.path.join(pasta, "_PENDENCIAS.txt"), "a",
                  encoding="utf-8") as f:
            f.write("%s | %s | %s\n"
                    % (datetime.now().strftime("%d/%m %H:%M"), arquivo, motivo))
    except Exception:
        pass


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
