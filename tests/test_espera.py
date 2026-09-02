# -*- coding: utf-8 -*-
"""A trava que segura a fila enquanto a impressora esta fora."""

import time

from finart_ctp.monitor import varrer

INEXISTENTE = "Z:/pasta/que/nao/existe"


def test_espera_nem_olha_a_pasta():
    # dentro da janela de espera, varrer nem chega a listar a entrada:
    # o caminho abaixo nao existe e mesmo assim nao da erro
    espera = {"ate": time.time() + 60, "avisado": True}
    assert varrer(INEXISTENTE, "Z:/saida", {}, espera) == 0


def test_fora_da_espera_volta_a_olhar():
    espera = {"ate": time.time() - 1, "avisado": False}
    try:
        varrer(INEXISTENTE, "Z:/saida", {}, espera)
    except OSError:
        pass          # tentou listar a pasta, que e o esperado
    else:
        raise AssertionError("deveria ter tentado abrir a pasta")
