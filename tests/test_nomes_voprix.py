# -*- coding: utf-8 -*-
"""
Nome de saida da VOPRIX, com os arquivos reais da pasta do cliente.

Padrao de entrada:  Produto_medida_cores_Cliente.cdr
Padrao de saida:    510x400_CORES_VOPRIX_Produto
"""

import pytest

from finart_ctp.nomes import cores_no_nome, nome_saida_voprix, resumo_voprix


REAIS = [
    ("Envelope_Saco_23x31,5_Colegio_Unus.cdr", "Envelope_Saco"),
    ("Pasta_Bopp_Orelha_44x31_Colegio_Unus.cdr", "Pasta_Bopp_Orelha"),
    ("Cartaz_29,7x42_4_0_Campeao_Lubrificantes_e_Filtro.cdr", "Cartaz"),
    ("Panfleto_11,6x14,5_4_0_Otica_AZ_Melo.cdr", "Panfleto"),
    ("Forro_Bandeja_35x27,5_4_0_Rangara_Restaurante.cdr", "Forro_Bandeja"),
    ("Caixa_Basculante_Bopp_25x20x7_4_0_Feliz_Aniversario.cdr",
     "Caixa_Basculante_Bopp"),
]


@pytest.mark.parametrize("arquivo,esperado", REAIS)
def test_resumo_pega_o_produto_antes_da_medida(arquivo, esperado):
    assert resumo_voprix(arquivo) == esperado


def test_resumo_sem_medida_no_nome():
    # nada quebra: devolve o nome inteiro
    assert resumo_voprix("Arte_Sem_Medida.cdr") == "Arte_Sem_Medida"


def test_cores_saem_na_ordem_cmyk():
    assert cores_no_nome({"M", "C"}) == "CM"
    assert cores_no_nome({"K"}) == "K"
    assert cores_no_nome({"Y", "K", "C", "M"}) == "CMYK"


def test_cor_especial_entra_depois_da_escala():
    assert cores_no_nome({"K", "PANTONE485"}) == "KPANTONE485"


def test_nome_de_saida_com_as_cores_certas():
    n = "Envelope_Saco_23x31,5_Colegio_Unus.cdr"
    assert (nome_saida_voprix(n, "510x400", {"C", "M"})
            == "510x400_CM_VOPRIX_Envelope_Saco")
    assert (nome_saida_voprix(n, "510x400", set("CMYK"))
            == "510x400_CMYK_VOPRIX_Envelope_Saco")
    assert (nome_saida_voprix(n, "510x400", {"K"})
            == "510x400_K_VOPRIX_Envelope_Saco")


def test_numero_da_pagina_vai_no_fim_com_dois_digitos():
    n = "Pasta_Bopp_Orelha_44x31_Colegio_Unus.cdr"
    assert (nome_saida_voprix(n, "510x400", {"C"}, 0, 2)
            == "510x400_C_VOPRIX_Pasta_Bopp_Orelha 01")
    assert (nome_saida_voprix(n, "510x400", {"C"}, 1, 2)
            == "510x400_C_VOPRIX_Pasta_Bopp_Orelha 02")


def test_uma_pagina_nao_leva_numero():
    n = "Cartaz_29,7x42_4_0_Campeao.cdr"
    assert nome_saida_voprix(n, "510x400", set("CMYK")) \
        == "510x400_CMYK_VOPRIX_Cartaz"


def test_outro_formato_de_chapa():
    n = "Cartaz_29,7x42_4_0_Campeao.cdr"
    assert nome_saida_voprix(n, "775x635", {"K"}) \
        == "775x635_K_VOPRIX_Cartaz"
