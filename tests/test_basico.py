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


def test_etiqueta_por_formato():
    from finart_ctp.processador import rotulo_prova
    assert rotulo_prova(510, 400) == "SOLIDA F4"
    assert rotulo_prova(400, 510) == "SOLIDA F4"      # deitado, mesmo formato
    assert rotulo_prova(775, 635) == "SOLIDA F2"
    assert rotulo_prova(635, 775) == "SOLIDA F2"


def test_etiqueta_vazia_para_formato_desconhecido():
    from finart_ctp.processador import rotulo_prova
    assert rotulo_prova(300, 200) == ""
