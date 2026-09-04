# -*- coding: utf-8 -*-
"""
EMPORIO PRINT: entra como a SOLIDA, sai como a VOPRIX.

So chega PDF, com a OS na frente do nome. O nome de saida foi lido das
chapas que os operadores fecharam a mao:

    510x400_CMYK_EMPORIO_01995_CAIXA 4796_1
    510x400_GRAY_EMPORIO_01995_CAIXA 4796_2
    660x605_GRAY_EMPORIO_01965_Maria Flor

Os arquivos usados aqui sao os de verdade da pasta do cliente.
"""

import os

import pytest

import finart_ctp.monitor as M
import finart_ctp.processador as P
import finart_ctp.utils as U
from finart_ctp.nomes import nome_saida_emporio, pede_olho, resumo_emporio


@pytest.fixture(autouse=True)
def sem_log(monkeypatch, tmp_path):
    monkeypatch.setattr(P, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    monkeypatch.setattr(U, "PASTA_PENDENCIAS", str(tmp_path / "_pend_teste"))
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path / "_ctrl_teste"))


# ----------------------------------------------------------------------
# Formatos: a chapa grande do Emporio e 660x605
# ----------------------------------------------------------------------

def test_chapas_do_emporio():
    assert P.identificar_formato(510, 400, P.EMPORIO) == (1000, "")
    assert P.identificar_formato(660, 605, P.EMPORIO) == (800, "")
    assert P.identificar_formato(605, 660, P.EMPORIO) == (800, "")   # deitado


def test_chapa_dos_outros_nao_vale_aqui():
    assert P.identificar_formato(775, 635, P.EMPORIO) == (None, None)
    assert P.identificar_formato(730, 600, P.EMPORIO) == (None, None)
    assert P.identificar_formato(660, 605) == (None, None)
    assert P.identificar_formato(660, 605, P.FIALHO) == (None, None)


def test_encaixe_e_so_do_fialho():
    """Cortar arte no escuro nao foi combinado com o Emporio."""
    assert P.encaixar_formato(670, 605, P.EMPORIO) is None


def test_etiqueta_da_prova():
    assert P.rotulo_prova(510, 400, P.EMPORIO) == "EMPORIO F4"
    assert P.rotulo_prova(660, 605, P.EMPORIO) == "EMPORIO F2"


# ----------------------------------------------------------------------
# O nome de saida
# ----------------------------------------------------------------------

def test_descricao_sai_do_nome_sem_as_palavras_de_servico():
    assert resumo_emporio("01995 - CHAPA CAIXA 4796.pdf") == "CAIXA 4796"
    assert (resumo_emporio("01929 - Regravar - 12 Modelos Caixas Cordial.pdf")
            == "12 Caixas Cordial")


def test_descricao_comprida_e_cortada_sem_partir_palavra():
    """
    Teto de 25. Os operadores abreviam a mao ('Guia', 'CXBLANT') e isso
    ninguem adivinha; o corte respeita a palavra.
    """
    d = resumo_emporio("01970 - CHAPA - Pasta C Orelha Lab Clinico Central.pdf")
    assert d == "Pasta C Orelha Lab"
    assert len(d) <= 25

    d = resumo_emporio("01987 - CHAPA - ARTE Guia do Comprador com canhoto.pdf")
    assert d == "Guia do Comprador com"


def test_nome_de_chapa_nao_leva_acento():
    """
    Acento em nome de chapa e pedido de encrenca: o arquivo atravessa a
    rede, o RIP e o InDesign, e nem todos leem UTF-8 igual.
    """
    assert (nome_saida_emporio("02040 - CHAPA - Cartão Mãe.pdf", "510x400",
                               set("CMYK"))
            == "510x400_CMYK_EMPORIO_02040_Cartao Mae")
    assert (nome_saida_emporio("01987 - CHAPA - entrega descartável.pdf",
                               "510x400", set("CMYK"))
            == "510x400_CMYK_EMPORIO_01987_entrega descartavel")


def test_verniz_fica_no_nome():
    """VERNIZ nao e palavra de servico: tem que aparecer na chapa."""
    assert "VERNIZ" in resumo_emporio("01928 - VERNIZ - Tag Balada.pdf")


def test_nome_igual_ao_que_o_operador_escreveu():
    """O 01995 do dia 03, chapa por chapa."""
    n = "01995 - CHAPA CAIXA 4796.pdf"
    assert (nome_saida_emporio(n, "510x400", set("CMYK"), 0, 2)
            == "510x400_CMYK_EMPORIO_01995_CAIXA 4796_1")
    assert (nome_saida_emporio(n, "510x400", {"GRAY"}, 1, 2)
            == "510x400_GRAY_EMPORIO_01995_CAIXA 4796_2")


def test_uma_pagina_nao_leva_numero():
    n = "01965 - CHAPA - Maria Flor - Papel de Seda.pdf"
    assert (nome_saida_emporio(n, "660x605", {"GRAY"})
            == "660x605_GRAY_EMPORIO_01965_Maria Flor Papel de Seda")


def test_sem_descricao_fica_so_a_os():
    assert (nome_saida_emporio("02040 - CHAPA.pdf", "510x400", set("CMYK"))
            == "510x400_CMYK_EMPORIO_02040")


def test_nome_da_chapa_escolhe_a_regra_do_emporio():
    assert (P.nome_da_chapa(P.EMPORIO, "01995 - CHAPA CAIXA 4796.pdf", "",
                            510, 400, set("CMYK"), 0, 1)
            == "510x400_CMYK_EMPORIO_01995_CAIXA 4796")


# ----------------------------------------------------------------------
# Verniz nao fecha sozinho
# ----------------------------------------------------------------------

def test_pede_olho_reconhece_verniz():
    assert pede_olho("01929 - CHAPA VERNIZ - 12 Modelos Caixas.pdf")
    assert pede_olho("01928 - VERNIZ - Tag Balada - 5x12cm.pdf")
    assert not pede_olho("01995 - CHAPA CAIXA 4796.pdf")


def _pagina(monkeypatch, cobertura, cinza=False):
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina", lambda pdf: [cobertura])
    monkeypatch.setattr(P, "sem_cor_gritante", lambda pdf, pagina: cinza)
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)
    monkeypatch.setattr(os.path, "getsize", lambda c: 1000)


def _roda(tmp_path, nome, aprovado=False):
    return P._processar_pdf("x.pdf", nome, str(tmp_path), P.EMPORIO,
                            {"status": "ok", "saidas": [], "motivo": "",
                             "impresso": None}, lambda m: None, aprovado)


def test_verniz_para_mesmo_em_quadricromia(monkeypatch, tmp_path):
    """Pedido do operador: verniz se confere antes, sempre."""
    _pagina(monkeypatch, {"C": .3, "M": .2, "Y": .2, "K": .1})
    monkeypatch.setattr(P, "_gerar_chapa",
                        lambda *a, **k: pytest.fail("verniz nao fecha sozinho"))
    avisos = []
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda arq, motivo: avisos.append(motivo))

    r = _roda(tmp_path, "01929 - CHAPA VERNIZ - 12 Modelos Caixas.pdf")

    assert r["status"] == "erro" and r["saidas"] == []
    assert "VERNIZ" in avisos[0] and "confere antes" in avisos[0]


def test_verniz_aprovado_fecha(monkeypatch, tmp_path):
    _pagina(monkeypatch, {"C": .3, "M": .2, "Y": .2, "K": .1})
    feito = {}

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas,
              cinza=False, alvo=None):
        feito["base"] = base
        return os.path.join(saida, base + ".pdf"), ["C", "M", "Y", "K"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)

    r = _roda(tmp_path, "01928 - VERNIZ - Tag Balada.pdf", aprovado=True)
    assert r["status"] == "ok" and "VERNIZ" in feito["base"]


# ----------------------------------------------------------------------
# Cor: cinza sai GRAY, e fora da quadricromia espera gente
# ----------------------------------------------------------------------

def test_pagina_de_uma_cor_sai_gray(monkeypatch, tmp_path):
    """A pagina 2 do 01995: o operador escreveu GRAY, o programa tambem."""
    _pagina(monkeypatch, {"C": 0, "M": 0, "Y": 0, "K": .42}, cinza=True)
    feito = {}

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas,
              cinza=False, alvo=None):
        feito.update(base=base, cinza=cinza)
        return os.path.join(saida, base + ".pdf"), ["GRAY"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)

    r = _roda(tmp_path, "01995 - CHAPA CAIXA 4796.pdf", aprovado=True)
    assert r["status"] == "ok"
    assert feito["cinza"] is True
    assert feito["base"] == "510x400_GRAY_EMPORIO_01995_CAIXA 4796"


def test_fora_da_quadricromia_espera(monkeypatch, tmp_path):
    """Como na VOPRIX: uma, duas ou tres cores param e avisam."""
    _pagina(monkeypatch, {"C": .21, "M": 0, "Y": 0, "K": .08})
    monkeypatch.setattr(P, "_gerar_chapa",
                        lambda *a, **k: pytest.fail("nao podia ter fechado"))
    avisos = []
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda arq, motivo: avisos.append(motivo))

    r = _roda(tmp_path, "01995 - CHAPA CAIXA 4796.pdf")
    assert r["status"] == "erro"
    assert "NAO veio em quadricromia" in avisos[0]


def test_quadricromia_fecha_sozinha(monkeypatch, tmp_path):
    _pagina(monkeypatch, {"C": .31, "M": .22, "Y": .18, "K": .09})
    feito = {}

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas,
              cinza=False, alvo=None):
        feito.update(base=base, dpi=dpi)
        return os.path.join(saida, base + ".pdf"), ["C", "M", "Y", "K"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda *a: pytest.fail("quadricromia nao e pendencia"))

    r = _roda(tmp_path, "02031 - AORTA-SEM-FRONTEIRAS_FOLHA-A4 (EP).pdf")
    assert r["status"] == "ok" and feito["dpi"] == 1000
    assert feito["base"].startswith("510x400_CMYK_EMPORIO_02031_AORTA")


def test_a_solida_nao_para_por_cor_nem_por_verniz(monkeypatch, tmp_path):
    """As travas sao da VOPRIX e do Emporio; a SOLIDA segue como sempre."""
    _pagina(monkeypatch, {"C": 0, "M": 0, "Y": 0, "K": .42})
    feito = {}

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas,
              cinza=False, alvo=None):
        feito["base"] = base
        return os.path.join(saida, base + ".pdf"), ["K"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda *a: pytest.fail("SOLIDA nao para"))

    r = P._processar_pdf("x.pdf", "49700 - Cliente - verniz.pdf",
                         str(tmp_path), P.SOLIDA,
                         {"status": "ok", "saidas": [], "motivo": "",
                          "impresso": None}, lambda m: None)
    assert r["status"] == "ok" and feito["base"] == "49700"
