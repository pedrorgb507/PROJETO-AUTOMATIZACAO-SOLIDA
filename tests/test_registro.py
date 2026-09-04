# -*- coding: utf-8 -*-
"""
O registro e compartilhado: mais de um programa pode estar rodando.

Nasceu de caso real - uma chapa fechada as 09:20 sumiu do registro as
09:49, quando o outro programa salvou o dicionario dele por cima.
"""

import json

import pytest

import finart_ctp.utils as U


@pytest.fixture(autouse=True)
def controle_no_tmp(monkeypatch, tmp_path):
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path))
    monkeypatch.setattr(U, "log", lambda *a, **k: None)


def _no_disco(tmp_path):
    with open(str(tmp_path / U.REGISTRO), encoding="utf-8") as f:
        return json.load(f)


def test_salvar_nao_apaga_o_que_o_outro_gravou(tmp_path):
    """Os dois programas comecam iguais e cada um faz um arquivo."""
    U.salvar_registro({"comum": {"arquivo": "ja existia"}})

    programa_a = U.carregar_registro()
    programa_b = U.carregar_registro()

    programa_a["chapa_do_a"] = {"arquivo": "fechada as 09:20"}
    U.salvar_registro(programa_a)

    programa_b["chapa_do_b"] = {"arquivo": "fechada as 09:49"}
    U.salvar_registro(programa_b)

    disco = _no_disco(tmp_path)
    assert "chapa_do_a" in disco, "o segundo apagou o trabalho do primeiro"
    assert "chapa_do_b" in disco
    assert "comum" in disco


def test_quem_salva_recebe_o_conjunto_de_volta(tmp_path):
    """Senao o laco segue com uma lista velha e refaz arquivo dos outros."""
    U.salvar_registro({"do_outro": {"arquivo": "x"}})

    meu = {"meu": {"arquivo": "y"}}
    U.salvar_registro(meu)

    assert "do_outro" in meu and "meu" in meu


def test_o_mais_novo_vence_na_mesma_chave(tmp_path):
    U.salvar_registro({"k": {"status": "erro"}})
    U.salvar_registro({"k": {"status": "ok"}})
    assert _no_disco(tmp_path)["k"]["status"] == "ok"


def test_registro_ilegivel_nao_derruba_a_gravacao(tmp_path):
    """Arquivo pela metade (queda de energia) nao pode travar o programa."""
    (tmp_path / U.REGISTRO).write_text("{isso nao e json", encoding="utf-8")
    U.salvar_registro({"novo": {"arquivo": "z"}})
    assert "novo" in _no_disco(tmp_path)


def test_salvar_nao_remove_nada(tmp_path):
    """
    Consequencia de juntar: apagar uma entrada exige gravar o JSON
    direto. Se um dia alguem 'sumir' uma chave e ela voltar, e por aqui.
    """
    U.salvar_registro({"a": {"x": 1}, "b": {"x": 2}})

    reg = U.carregar_registro()
    del reg["b"]
    U.salvar_registro(reg)

    assert "b" in _no_disco(tmp_path)
