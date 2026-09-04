# -*- coding: utf-8 -*-
"""
O fluxo VOPRIX: .cdr convertido pelo CorelDRAW e transformado em chapa.

Nao depende do CorelDRAW nem do Ghostscript: a conversao e o miolo sao
substituidos na hora.
"""

import finart_ctp.processador as P
from finart_ctp.corel import ArquivoEmUso
from finart_ctp.monitor import _pastas_do_dia, varrer


def _cdr(tmp_path, nome="Envelope_Saco_23x31,5_Colegio_Unus.cdr"):
    arq = tmp_path / nome
    arq.write_bytes(b"CDR nem precisa ser valido")
    return arq


def test_pasta_voprix_desligada():
    # BASE_ENTRADA_VOPRIX = None -> fluxo desligado, nada quebra
    assert _pastas_do_dia(None) == (None, None)


def test_cdr_aberto_no_operador_e_apenas_pulado(monkeypatch, tmp_path):
    def recusa(cdr, destino):
        raise ArquivoEmUso("'x.cdr' esta aberto no CorelDRAW")

    monkeypatch.setattr("finart_ctp.corel.publicar_pdf", recusa)
    monkeypatch.setattr(P, "log", lambda *a, **k: None)

    r = P.processar_voprix(str(_cdr(tmp_path)), str(tmp_path / "saida"))
    assert r["status"] == "pular"


def test_corel_fora_do_ar_segura_a_fila(monkeypatch, tmp_path):
    def cai(cdr, destino):
        raise RuntimeError("COM nao respondeu")

    monkeypatch.setattr("finart_ctp.corel.publicar_pdf", cai)
    monkeypatch.setattr(P, "log", lambda *a, **k: None)

    r = P.processar_voprix(str(_cdr(tmp_path)), str(tmp_path / "saida"))
    assert r["status"] == "espera"
    assert "CorelDRAW" in r["motivo"]


def test_pular_nao_entra_no_registro_nem_trava(monkeypatch, tmp_path):
    _cdr(tmp_path)

    def recusa(cdr, destino):
        raise ArquivoEmUso("aberto")

    monkeypatch.setattr("finart_ctp.corel.publicar_pdf", recusa)
    monkeypatch.setattr("finart_ctp.monitor.log", lambda *a, **k: None)
    monkeypatch.setattr("finart_ctp.monitor.arquivo_estavel", lambda c: True)

    registro = {}
    espera = {"ate": 0, "avisado": False}
    varrer(str(tmp_path), str(tmp_path / "saida"), registro, espera,
           exts=(".cdr",), processa=P.processar_voprix)

    assert registro == {}                       # nao registra
    assert espera["ate"] == 0                   # nao entra em espera


def test_nome_de_saida_sai_pelo_padrao_voprix(monkeypatch, tmp_path):
    """O miolo recebe um 'nomear' que junta formato + cores + produto."""
    capturado = {}

    def _nucleo_falso(origem_pdf, nome_ref, pasta_saida, rotulos, nomear,
                      colisao=""):
        capturado["nome"] = nomear(0, 1, (510, 400), "", {"C", "M"})
        capturado["rotulos"] = rotulos
        return {"status": "ok", "saidas": [], "motivo": "", "impresso": None}

    monkeypatch.setattr("finart_ctp.corel.publicar_pdf",
                        lambda cdr, destino: destino)
    monkeypatch.setattr(P, "_nucleo", _nucleo_falso)

    P.processar_voprix(str(_cdr(tmp_path)), str(tmp_path / "saida"))

    assert capturado["nome"] == "510x400_CM_VOPRIX_Envelope_Saco"
    assert capturado["rotulos"][(510, 400)] == "VOPRIX F4"
