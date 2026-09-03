# -*- coding: utf-8 -*-
"""
A prova impressa: uma folha A4 em pe por pagina, um trabalho por folha.

Nao depende do Ghostscript: a rasterizacao e substituida por imagens
feitas na hora.
"""

import os

import pytest
from PIL import Image
from pypdf import PdfReader

import finart_ctp.prova as prova


def _imagens(pasta, tamanhos):
    caminhos = []
    for i, (w, h) in enumerate(tamanhos):
        c = os.path.join(str(pasta), "p%03d.jpg" % i)
        Image.new("RGB", (w, h), "white").save(c)
        caminhos.append(c)
    return caminhos


@pytest.fixture
def espiao(monkeypatch):
    """Intercepta o envio para a impressora e guarda o que seria impresso."""
    enviados = []

    def falso_envio(pdf, impressora=None):
        r = PdfReader(pdf)
        pg = r.pages[0]
        enviados.append({
            "paginas": len(r.pages),
            "larg_mm": round(float(pg.mediabox.width) / 72 * 25.4),
            "alt_mm": round(float(pg.mediabox.height) / 72 * 25.4),
        })

    monkeypatch.setattr(prova, "enviar_para_impressora", falso_envio)
    return enviados


def test_duas_paginas_viram_dois_trabalhos(monkeypatch, tmp_path, espiao):
    # duas paginas deitadas, como o "miolo CAD2"
    monkeypatch.setattr(prova, "_rasterizar",
                        lambda pdf, pasta, dpi=None: _imagens(tmp_path,
                                                              [(800, 600)] * 2))
    _, folhas = prova.imprimir("qualquer.pdf", "IMPRESSORA FALSA")

    assert folhas == 2
    assert len(espiao) == 2, "duplex juntaria as duas num trabalho so"
    for folha in espiao:
        assert folha["paginas"] == 1, "cada trabalho tem que ter 1 pagina"


def test_uma_pagina_vira_um_trabalho(monkeypatch, tmp_path, espiao):
    monkeypatch.setattr(prova, "_rasterizar",
                        lambda pdf, pasta, dpi=None: _imagens(tmp_path,
                                                              [(800, 600)]))
    _, folhas = prova.imprimir("qualquer.pdf", "IMPRESSORA FALSA")
    assert (folhas, len(espiao)) == (1, 1)


def test_folha_sai_sempre_a4_em_pe(monkeypatch, tmp_path, espiao):
    # arte deitada E arte em pe: as duas tem que virar A4 retrato
    monkeypatch.setattr(prova, "_rasterizar",
                        lambda pdf, pasta, dpi=None: _imagens(tmp_path,
                                                              [(800, 600),
                                                               (600, 800)]))
    prova.imprimir("qualquer.pdf", "IMPRESSORA FALSA")
    for folha in espiao:
        assert (folha["larg_mm"], folha["alt_mm"]) == (210, 297)


def test_arte_deitada_e_girada_para_caber(tmp_path):
    # a arte deitada tem que ocupar a folha girada, nao encolhida no meio
    imagem = _imagens(tmp_path, [(2000, 1000)])
    destino = os.path.join(str(tmp_path), "prova.pdf")
    prova._montar_a4(imagem, destino, dpi=150)

    pg = PdfReader(destino).pages[0]
    assert float(pg.mediabox.width) < float(pg.mediabox.height)   # retrato


# ----------------------------------------------------------------------
# Etiqueta do formato no canto da folha
# ----------------------------------------------------------------------

def _faixa_do_alto(folha, dpi=150):
    """Recorte do alto da folha, onde a etiqueta e escrita."""
    alto = int(round(prova.FAIXA_ROTULO_MM / 25.4 * dpi))
    return folha.crop((0, 0, folha.width, alto))


def _extremos(imagem):
    """(pixel mais escuro, pixel mais claro) do recorte, em cinza."""
    return imagem.convert("L").getextrema()


def _tem_tinta(imagem):
    """True se houver algum pixel escuro (texto ou arte)."""
    return _extremos(imagem)[0] < 128


def test_etiqueta_aparece_no_alto_da_folha():
    arte = Image.new("RGB", (2000, 1000), "white")      # deitada, em branco
    folha = prova.montar_folha(arte, dpi=150, etiqueta="SOLIDA F4")
    assert _tem_tinta(_faixa_do_alto(folha)), "a etiqueta nao foi escrita"


def test_sem_etiqueta_o_alto_fica_limpo():
    arte = Image.new("RGB", (2000, 1000), "white")
    folha = prova.montar_folha(arte, dpi=150, etiqueta="")
    assert not _tem_tinta(_faixa_do_alto(folha))


def test_etiqueta_nao_cai_por_cima_da_arte():
    # arte toda preta: se a faixa do alto tem branco, a arte foi empurrada
    arte = Image.new("RGB", (2000, 1000), "black")
    folha = prova.montar_folha(arte, dpi=150, etiqueta="SOLIDA F4")
    assert _extremos(_faixa_do_alto(folha))[1] > 200,         "a arte invadiu a faixa da etiqueta"


def test_folha_continua_a4_em_pe_com_etiqueta():
    arte = Image.new("RGB", (2000, 1000), "white")
    folha = prova.montar_folha(arte, dpi=150, etiqueta="SOLIDA F2")
    assert folha.width < folha.height
    assert abs(folha.width / 150 * 25.4 - 210) < 1
