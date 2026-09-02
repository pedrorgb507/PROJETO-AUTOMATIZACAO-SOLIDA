# -*- coding: utf-8 -*-
"""Testes rapidos: rode com  pytest  na raiz do projeto."""

from finart_ctp.pdf_builder import _tint_transform
from finart_ctp.processador import identificar_formato
from finart_ctp.utils import normalizar


def test_formato_chapa_pequena():
    assert identificar_formato(510, 400) == (1000, "")
    assert identificar_formato(400, 510) == (1000, "")      # deitado


def test_formato_chapa_grande():
    assert identificar_formato(775, 635) == (800, "R1")


def test_formato_dentro_da_tolerancia():
    assert identificar_formato(512, 398) == (1000, "")


def test_formato_fora_do_padrao():
    assert identificar_formato(300, 200) == (None, None)


def test_normalizar_mes():
    assert normalizar("MARÇO") == "MARCO"
    assert normalizar(" Marco ") == "MARCO"
    assert normalizar("Fevereiro") == "FEVEREIRO"


def test_tint_transform_uma_tinta():
    assert _tint_transform(["K"]).startswith("{")
    assert _tint_transform(["K"]).endswith("}")


def test_tint_transform_duas_tintas():
    saida = _tint_transform(["M", "K"])
    assert "roll" in saida and saida.count("pop") == 2
