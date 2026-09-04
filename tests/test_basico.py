# -*- coding: utf-8 -*-
"""Testes rapidos: rode com  pytest  na raiz do projeto."""

import pytest

import finart_ctp.utils as U
from finart_ctp.pdf_builder import _tint_transform
from finart_ctp.processador import identificar_formato
from finart_ctp.utils import normalizar


@pytest.fixture(autouse=True)
def fora_da_maquina(monkeypatch, tmp_path):
    """Nada de teste encosta nas pastas de verdade desta maquina."""
    monkeypatch.setattr(U, "PASTA_PENDENCIAS", str(tmp_path / "_pend_teste"))
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path / "_ctrl_teste"))


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


def test_arquivo_gigante_vira_pendencia(monkeypatch, tmp_path):
    """Nao processa, nao imprime, e avisa: e o caso do PDF de 2,2 GB."""
    import finart_ctp.processador as P

    grande = tmp_path / "49999 - Cliente - cartaz.pdf"
    grande.write_bytes(b"%PDF-1.4 nem precisa ser valido")

    monkeypatch.setattr(P, "TAMANHO_MAXIMO_MB", 0)          # tudo e gigante
    avisos = []
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda arq, motivo: avisos.append((arq, motivo)))
    monkeypatch.setattr(P, "log", lambda *a, **k: None)
    monkeypatch.setattr(P, "imprimir",
                        lambda *a, **k: pytest.fail("nao pode imprimir"))

    r = P.processar(str(grande), str(tmp_path / "saida"))

    assert r["status"] == "erro"
    assert "gigante" in r["motivo"]
    assert len(avisos) == 1 and "gigante" in avisos[0][1]


def test_arquivo_dentro_do_limite_nao_e_barrado(monkeypatch, tmp_path):
    import finart_ctp.processador as P

    pequeno = tmp_path / "49999 - Cliente - cartaz.pdf"
    pequeno.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(P, "TAMANHO_MAXIMO_MB", 500)
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)
    monkeypatch.setattr(P, "log", lambda *a, **k: None)

    r = P.processar(str(pequeno), str(tmp_path / "saida"))
    # passa do limite e falha adiante, na leitura do PDF - nao por tamanho
    assert "gigante" not in r["motivo"]
