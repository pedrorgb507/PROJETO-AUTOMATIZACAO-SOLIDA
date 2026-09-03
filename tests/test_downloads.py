# -*- coding: utf-8 -*-
"""
A ponte Downloads -> pasta do dia.

O filtro e a parte critica: Downloads e uma pasta pessoal, cheia de
coisa que nao tem nada a ver com o servico. Se ele errar para mais, o
programa comeca a mover arquivo dos outros.
"""

import os

import pytest

from finart_ctp.downloads import e_servico, nome_limpo, recolher


SERVICO = [
    "49635 - Cliente - santinhos.pdf",
    "49581 49582 49583 - Cliente - bottons 7cm.pdf",
    "49513 - Cliente - miolo CAD2.pdf",
    "49635 - Cliente - santinhos (1).pdf",
]

NAO_SERVICO = [
    "VSCodeUserSetup-x64-1.135.0.exe",
    "Controle_Estoque_Chapas_Solida_Grafica_3.xlsx",
    "orcamento_acabamento_grafico_4.html",
    "README.md",
    "boleto 2026 - vencimento.pdf",       # comeca com palavra, nao com OS
    "nota fiscal 12345.pdf",
    "2026 - relatorio.pdf",               # ano de 4 digitos nao e OS
    "49607-Cliente-adesivos.pdf",         # sem " - ": fica em Downloads
    "49635 - Cliente - santinhos.pdf.crdownload",   # download pela metade
    "~$rascunho.pdf",
]


@pytest.mark.parametrize("nome", SERVICO)
def test_reconhece_ordem_de_servico(nome):
    assert e_servico(nome), nome


@pytest.mark.parametrize("nome", NAO_SERVICO)
def test_ignora_o_resto_do_downloads(nome):
    assert not e_servico(nome), nome


def test_tira_o_sufixo_de_copia_do_navegador():
    assert (nome_limpo("49635 - Cliente - santinhos (1).pdf")
            == "49635 - Cliente - santinhos.pdf")
    assert (nome_limpo("49635 - Cliente - santinhos.pdf")
            == "49635 - Cliente - santinhos.pdf")


def test_entrega_e_nao_encosta_no_resto(monkeypatch, tmp_path):
    origem = tmp_path / "downloads"
    destino = tmp_path / "dia"
    origem.mkdir()
    (origem / "49635 - Cliente - santinhos.pdf").write_bytes(b"%PDF-1.4 servico")
    (origem / "boleto.pdf").write_bytes(b"%PDF-1.4 particular")
    (origem / "planilha.xlsx").write_bytes(b"nao e pdf")

    import finart_ctp.downloads as d
    monkeypatch.setattr(d, "PASTA_DOWNLOADS", str(origem))
    monkeypatch.setattr(d, "arquivo_estavel", lambda c: True)
    monkeypatch.setattr(d, "log", lambda *a, **k: None)   # nao sujar o log real

    entregues = d.recolher(str(destino))

    assert entregues == ["49635 - Cliente - santinhos.pdf"]
    assert os.listdir(str(destino)) == ["49635 - Cliente - santinhos.pdf"]
    # o que nao era servico continua intocado em Downloads
    assert sorted(os.listdir(str(origem))) == ["boleto.pdf", "planilha.xlsx"]


def test_nao_sobrescreve_arquivo_diferente(monkeypatch, tmp_path):
    origem = tmp_path / "downloads"
    destino = tmp_path / "dia"
    origem.mkdir()
    destino.mkdir()
    (origem / "49635 - Cliente - santinhos.pdf").write_bytes(b"versao nova, maior")
    (destino / "49635 - Cliente - santinhos.pdf").write_bytes(b"antiga")

    import finart_ctp.downloads as d
    monkeypatch.setattr(d, "PASTA_DOWNLOADS", str(origem))
    monkeypatch.setattr(d, "arquivo_estavel", lambda c: True)
    monkeypatch.setattr(d, "log", lambda *a, **k: None)   # nao sujar o log real

    d.recolher(str(destino))

    ficaram = sorted(os.listdir(str(destino)))
    assert ficaram == ["49635 - Cliente - santinhos.pdf",
                       "49635 - Cliente - santinhos_v2.pdf"]
    assert (destino / "49635 - Cliente - santinhos.pdf").read_bytes() == b"antiga"
