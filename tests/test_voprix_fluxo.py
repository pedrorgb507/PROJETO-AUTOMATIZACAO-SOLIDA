# -*- coding: utf-8 -*-
"""
O caminho da VOPRIX de ponta a ponta, sem CorelDRAW nem Ghostscript.

O que importa aqui: o .cdr passa pela Corel antes de tudo, o nome sai
pela regra da VOPRIX, o arquivo aberto na sessao do operador nao e
tocado, e o PDF temporario da conversao some no fim.
"""

import os

import pytest

import finart_ctp.monitor as M
import finart_ctp.processador as P
import finart_ctp.utils as U
from finart_ctp.corel import ArquivoEmUso

CDR = "Envelope_Saco_23x31,5_Colegio_Unus.cdr"


@pytest.fixture(autouse=True)
def sem_log(monkeypatch, tmp_path):
    monkeypatch.setattr(P, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    # teste nenhum pode escrever na pasta de pendencias da maquina de
    # verdade, nem no log: tudo vai para o tmp do pytest.
    monkeypatch.setattr(U, "PASTA_PENDENCIAS", str(tmp_path / "_pend_teste"))
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path / "_ctrl_teste"))


# ----------------------------------------------------------------------
# Formato e etiqueta
# ----------------------------------------------------------------------

def test_formato_no_nome():
    assert P.formato_no_nome(510, 400) == "510x400"
    assert P.formato_no_nome(400, 510) == "510x400"      # deitado
    assert P.formato_no_nome(775, 635) == "775x635"
    assert P.formato_no_nome(300, 200) == ""


def test_etiqueta_da_prova_diz_o_cliente():
    assert P.rotulo_prova(510, 400) == "SOLIDA F4"
    assert P.rotulo_prova(510, 400, P.VOPRIX) == "VOPRIX F4"
    assert P.rotulo_prova(775, 635, P.VOPRIX) == "VOPRIX F2"
    assert P.rotulo_prova(300, 200, P.VOPRIX) == ""


# ----------------------------------------------------------------------
# Nome de saida: cada cliente com a sua regra
# ----------------------------------------------------------------------

def test_nome_da_chapa_por_cliente():
    assert P.nome_da_chapa(P.SOLIDA, "49576 - Cliente - x.pdf", "R1",
                           775, 635, {"C", "M"}, 0, 1) == "49576R1"
    assert P.nome_da_chapa(P.VOPRIX, CDR, "", 510, 400,
                           {"C", "M"}, 0, 1) == "510x400_CM_VOPRIX_Envelope_Saco"


def test_nome_da_chapa_voprix_com_duas_paginas():
    n = "Pasta_Bopp_Orelha_44x31_Colegio_Unus.cdr"
    assert (P.nome_da_chapa(P.VOPRIX, n, "", 510, 400, {"C"}, 1, 2)
            == "510x400_C_VOPRIX_Pasta_Bopp_Orelha 02")


# ----------------------------------------------------------------------
# Conversao
# ----------------------------------------------------------------------

def test_cdr_aberto_no_corel_fica_para_depois(monkeypatch, tmp_path):
    """A regra que nasceu de erro: arquivo do operador nao se toca."""
    cdr = tmp_path / CDR
    cdr.write_bytes(b"cdr")

    def em_uso(_):
        raise ArquivoEmUso("'%s' esta aberto no CorelDRAW" % CDR)

    monkeypatch.setattr(P, "converter_cdr", em_uso)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda *a: pytest.fail("nao e pendencia, e so esperar"))

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.VOPRIX)
    assert r["status"] == "adiado"
    assert "CorelDRAW" in r["motivo"]


def test_corel_que_falha_vira_pendencia(monkeypatch, tmp_path):
    cdr = tmp_path / CDR
    cdr.write_bytes(b"cdr")

    def estourou(_):
        raise RuntimeError("CorelDRAW nao gerou o PDF")

    avisos = []
    monkeypatch.setattr(P, "converter_cdr", estourou)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda arq, motivo: avisos.append(motivo))

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.VOPRIX)
    assert r["status"] == "erro"
    assert len(avisos) == 1 and "CorelDRAW" in avisos[0]


def test_temporario_da_conversao_e_apagado(monkeypatch, tmp_path):
    """Mesmo quando o PDF convertido nao presta, a pasta local nao fica."""
    cdr = tmp_path / CDR
    cdr.write_bytes(b"cdr")
    tmp = tmp_path / "temporaria"
    tmp.mkdir()
    pdf = tmp / "convertido.pdf"
    pdf.write_bytes(b"%PDF-1.4 nem precisa ser valido")

    monkeypatch.setattr(P, "converter_cdr", lambda _: (str(pdf), str(tmp)))
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.VOPRIX)
    assert r["status"] == "erro"          # PDF ilegivel, o que interessa
    assert not os.path.exists(str(tmp))   # e a pasta local sumiu


def test_pdf_gigante_saido_da_corel_e_barrado(monkeypatch, tmp_path):
    """O caso real: .cdr de 375 MB que a Corel exportou como 2,2 GB."""
    cdr = tmp_path / CDR
    cdr.write_bytes(b"cdr")
    tmp = tmp_path / "temporaria"
    tmp.mkdir()
    pdf = tmp / "convertido.pdf"
    pdf.write_bytes(b"%PDF-1.4 fingindo ser enorme")

    # o .cdr cabe; quem estoura o limite e o PDF que a Corel devolveu
    monkeypatch.setattr(P, "converter_cdr", lambda _: (str(pdf), str(tmp)))
    monkeypatch.setattr(P, "acima_do_limite",
                        lambda c: "" if c.lower().endswith(".cdr")
                        else "arquivo gigante: 2200 MB, acima do limite")
    monkeypatch.setattr(P, "medir_paginas",
                        lambda *a: pytest.fail("nem deveria abrir o PDF"))
    avisos = []
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda arq, motivo: avisos.append((arq, motivo)))

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.VOPRIX)
    assert r["status"] == "erro"
    assert r["motivo"].startswith("depois de converter, ")
    assert avisos[0][0] == CDR            # a pendencia cita o .cdr original
    assert not os.path.exists(str(tmp))


def test_pdf_grande_demais_fica_guardado_para_a_mao(monkeypatch, tmp_path):
    """
    O que a Corel converteu nao se joga fora: vai para a pasta de
    pendencias, com o nome do original, para o operador seguir dali.
    """
    import finart_ctp.utils as U

    cdr = tmp_path / CDR
    cdr.write_bytes(b"cdr")
    tmp = tmp_path / "temporaria"
    tmp.mkdir()
    pdf = tmp / "convertido.pdf"
    pdf.write_bytes(b"%PDF-1.4 os 547 MB da Corel")
    pendencias = tmp_path / "_PENDENCIAS"

    monkeypatch.setattr(P, "converter_cdr", lambda _: (str(pdf), str(tmp)))
    monkeypatch.setattr(P, "acima_do_limite",
                        lambda c: "" if c.lower().endswith(".cdr")
                        else "arquivo gigante: 547 MB, acima do limite")
    monkeypatch.setattr(U, "PASTA_PENDENCIAS", str(pendencias))
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path / "_controle"))
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.VOPRIX)

    guardado = pendencias / "Envelope_Saco_23x31,5_Colegio_Unus.pdf"
    assert guardado.exists(), "o PDF convertido se perdeu"
    assert r["pendencia"] == str(guardado)
    assert not os.path.exists(str(tmp))        # e a temporaria sumiu


def test_pdf_ilegivel_tambem_fica_guardado(monkeypatch, tmp_path):
    import finart_ctp.utils as U

    cdr = tmp_path / CDR
    cdr.write_bytes(b"cdr")
    tmp = tmp_path / "temporaria"
    tmp.mkdir()
    pdf = tmp / "convertido.pdf"
    pdf.write_bytes(b"%PDF-1.4 quebrado")
    pendencias = tmp_path / "_PENDENCIAS"

    monkeypatch.setattr(P, "converter_cdr", lambda _: (str(pdf), str(tmp)))
    monkeypatch.setattr(U, "PASTA_PENDENCIAS", str(pendencias))
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path / "_controle"))
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.VOPRIX)
    assert r["status"] == "erro"
    assert (pendencias / "Envelope_Saco_23x31,5_Colegio_Unus.pdf").exists()


def test_quando_da_certo_nao_sobra_nada_guardado(monkeypatch, tmp_path):
    """Chapa gerada, PDF convertido descartado: a pasta nao vira deposito."""
    import finart_ctp.utils as U

    cdr = tmp_path / CDR
    cdr.write_bytes(b"cdr")
    tmp = tmp_path / "temporaria"
    tmp.mkdir()
    pdf = tmp / "convertido.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    pendencias = tmp_path / "_PENDENCIAS"

    monkeypatch.setattr(P, "converter_cdr", lambda _: (str(pdf), str(tmp)))
    monkeypatch.setattr(U, "PASTA_PENDENCIAS", str(pendencias))
    monkeypatch.setattr(P, "_processar_pdf",
                        lambda *a: {"status": "ok", "saidas": ["x.pdf"],
                                    "motivo": "", "impresso": 1})

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.VOPRIX)
    assert r["status"] == "ok"
    assert not pendencias.exists()
    assert not os.path.exists(str(tmp))


def test_voprix_nao_precisa_de_os(monkeypatch, tmp_path):
    """O nome da VOPRIX nao tem OS - e isso nao pode barrar o arquivo."""
    cdr = tmp_path / CDR
    cdr.write_bytes(b"cdr")
    chamou = []

    def converteu(caminho):
        chamou.append(caminho)
        raise RuntimeError("parei aqui de proposito")

    monkeypatch.setattr(P, "converter_cdr", converteu)
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.VOPRIX)
    assert chamou, "barrou por falta de OS antes de tentar converter"
    assert "nao achei numero de OS" not in r["motivo"]


def test_solida_sem_os_continua_barrada(monkeypatch, tmp_path):
    """A regra da OS vale so para a SOLIDA, e continua valendo."""
    pdf = tmp_path / "sem numero nenhum.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)

    r = P.processar(str(pdf), str(tmp_path / "saida"))
    assert r["status"] == "erro" and "nao achei numero de OS" in r["motivo"]


# ----------------------------------------------------------------------
# Monitor: duas pastas, uma saida
# ----------------------------------------------------------------------

def test_clientes_traz_as_duas_pastas(monkeypatch):
    monkeypatch.setattr(M, "BASE_ENTRADA_VOPRIX", r"V:\VOPRIX")
    monkeypatch.setattr(M, "BASE_ENTRADA_FIALHO", None)
    lista = M.clientes()
    assert [c[0] for c in lista] == [M.SOLIDA, M.VOPRIX]
    assert [c[2] for c in lista] == [(".pdf",), (".cdr",)]


def test_sem_pasta_da_voprix_fica_so_a_solida(monkeypatch):
    monkeypatch.setattr(M, "BASE_ENTRADA_VOPRIX", None)
    monkeypatch.setattr(M, "BASE_ENTRADA_FIALHO", None)
    assert [c[0] for c in M.clientes()] == [M.SOLIDA]


def test_varrer_so_pega_a_extensao_do_cliente(monkeypatch, tmp_path):
    (tmp_path / CDR).write_bytes(b"cdr")
    (tmp_path / "49572 - Cliente - flyer.pdf").write_bytes(b"pdf")

    vistos = []
    monkeypatch.setattr(M, "arquivo_estavel", lambda c: True)
    monkeypatch.setattr(M, "salvar_registro", lambda r: None)
    monkeypatch.setattr(M, "processar", lambda caminho, saida, cliente: (
        vistos.append((os.path.basename(caminho), cliente))
        or {"status": "ok", "saidas": [], "motivo": "", "impresso": None}))

    registro = {}
    M.varrer(str(tmp_path), "Z:/saida", registro, None, M.VOPRIX, ".cdr")

    assert vistos == [(CDR, M.VOPRIX)]
    assert len(registro) == 1
    assert list(registro.values())[0]["cliente"] == M.VOPRIX


def test_adiado_nao_entra_no_registro(monkeypatch, tmp_path):
    (tmp_path / CDR).write_bytes(b"cdr")
    monkeypatch.setattr(M, "arquivo_estavel", lambda c: True)
    monkeypatch.setattr(M, "salvar_registro", lambda r: None)
    monkeypatch.setattr(M, "processar", lambda *a: {
        "status": "adiado", "saidas": [], "motivo": "aberto no CorelDRAW"})

    registro = {}
    feitos = M.varrer(str(tmp_path), "Z:/saida", registro, None,
                      M.VOPRIX, ".cdr")

    assert feitos == 0 and registro == {}


# ----------------------------------------------------------------------
# Arte de uma cor so: chapa em escala de cinza
# ----------------------------------------------------------------------

def test_nome_diz_gray_quando_a_arte_e_de_uma_cor():
    assert (P.nome_da_chapa(P.VOPRIX, CDR, "", 510, 400, {"GRAY"}, 0, 1)
            == "510x400_GRAY_VOPRIX_Envelope_Saco")


def test_gray_no_lugar_das_quatro_tintas(monkeypatch, tmp_path):
    """Arte neutra: uma chapa em cinza, e o nome fala GRAY, nao CMYK."""
    feito = {}
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina", lambda pdf: [
        {"C": 0.0608, "M": 0.0608, "Y": 0.0608, "K": 0.0544}])
    monkeypatch.setattr(P, "sem_cor_gritante", lambda pdf, pagina: True)
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas, cinza=False, alvo=None):
        feito.update(base=base, cinza=cinza, dpi=dpi)
        return os.path.join(saida, base + ".pdf"), ["GRAY"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(os.path, "getsize", lambda c: 1000)

    P._processar_pdf("qualquer.pdf", CDR, str(tmp_path), P.VOPRIX,
                     {"status": "ok", "saidas": [], "motivo": "",
                      "impresso": None}, lambda m: None, True)

    assert feito["cinza"] is True
    assert feito["dpi"] == 1000
    assert feito["base"] == "510x400_GRAY_VOPRIX_Envelope_Saco"


def test_arte_colorida_continua_em_quadricromia(monkeypatch, tmp_path):
    feito = {}
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina", lambda pdf: [
        {"C": 0.31, "M": 0.08, "Y": 0.05, "K": 0.02}])
    monkeypatch.setattr(P, "sem_cor_gritante", lambda pdf, pagina: False)
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas, cinza=False, alvo=None):
        feito.update(base=base, cinza=cinza)
        return os.path.join(saida, base + ".pdf"), ["C", "M"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(os.path, "getsize", lambda c: 1000)

    P._processar_pdf("qualquer.pdf", CDR, str(tmp_path), P.VOPRIX,
                     {"status": "ok", "saidas": [], "motivo": "",
                      "impresso": None}, lambda m: None)

    assert feito["cinza"] is False
    assert feito["base"] == "510x400_CMYK_VOPRIX_Envelope_Saco"


def test_solida_nao_muda(monkeypatch, tmp_path):
    """A regra do cinza e da VOPRIX: a SOLIDA segue como sempre foi."""
    feito = {}
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina", lambda pdf: [
        {"C": 0.0608, "M": 0.0608, "Y": 0.0608, "K": 0.0544}])
    monkeypatch.setattr(P, "sem_cor_gritante",
                        lambda *a: pytest.fail("nem devia perguntar"))
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas, cinza=False, alvo=None):
        feito.update(base=base, cinza=cinza)
        return os.path.join(saida, base + ".pdf"), ["C", "M", "Y", "K"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(os.path, "getsize", lambda c: 1000)

    P._processar_pdf("x.pdf", "49700 - Cliente - flyer.pdf", str(tmp_path),
                     P.SOLIDA, {"status": "ok", "saidas": [], "motivo": "",
                                "impresso": None}, lambda m: None)

    assert feito["cinza"] is False
    assert feito["base"] == "49700"


def test_cobertura_igual_nos_tres_canais_e_preto_composto():
    """Os numeros reais do Blocos_Rio_Quente, que motivaram a regra."""
    assert P.pagina_de_uma_cor({"C": 0.06081, "M": 0.06079,
                                "Y": 0.06080, "K": 0.05444})


def test_preto_puro_tambem_e_uma_cor():
    assert P.pagina_de_uma_cor({"C": 0.0, "M": 0.0, "Y": 0.0, "K": 0.4212})


def test_arte_colorida_nao_passa_por_cinza():
    assert not P.pagina_de_uma_cor({"C": 0.31, "M": 0.08,
                                    "Y": 0.00, "K": 0.02})
    assert not P.pagina_de_uma_cor({"C": 0.20, "M": 0.20,
                                    "Y": 0.26, "K": 0.05})


def test_pagina_vazia_nao_vira_cinza():
    assert not P.pagina_de_uma_cor({"C": 0.0, "M": 0.0, "Y": 0.0, "K": 0.0})


# ----------------------------------------------------------------------
# Fora da quadricromia, quem manda fechar e gente
# ----------------------------------------------------------------------

def _monta_pagina(monkeypatch, cobertura, cinza=False):
    """Prepara uma pagina 510x400 com a cobertura pedida."""
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina", lambda pdf: [cobertura])
    monkeypatch.setattr(P, "sem_cor_gritante", lambda pdf, pagina: cinza)
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)
    monkeypatch.setattr(os.path, "getsize", lambda c: 1000)


def _roda(tmp_path, aprovado=False, nome=CDR, cliente=None):
    return P._processar_pdf("x.pdf", nome, str(tmp_path),
                            cliente or P.VOPRIX,
                            {"status": "ok", "saidas": [], "motivo": "",
                             "impresso": None}, lambda m: None, aprovado)


def test_uma_cor_nao_fecha_sozinha(monkeypatch, tmp_path):
    """Cinza para antes de gerar: o operador decide."""
    _monta_pagina(monkeypatch, {"C": .0608, "M": .0608, "Y": .0608, "K": .0544},
                  cinza=True)
    monkeypatch.setattr(P, "_gerar_chapa",
                        lambda *a, **k: pytest.fail("nao podia ter fechado"))
    avisos = []
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda arq, motivo: avisos.append(motivo))

    r = _roda(tmp_path)

    assert r["status"] == "erro" and r["saidas"] == []
    assert "NAO veio em quadricromia" in avisos[0]
    assert "GRAY" in avisos[0]
    assert "510x400_GRAY_VOPRIX_Envelope_Saco" in avisos[0]   # o que sairia
    assert "C 0.0608" in avisos[0]                            # os numeros


def test_duas_cores_tambem_espera(monkeypatch, tmp_path):
    _monta_pagina(monkeypatch, {"C": .21, "M": .00, "Y": .00, "K": .08})
    monkeypatch.setattr(P, "_gerar_chapa",
                        lambda *a, **k: pytest.fail("nao podia ter fechado"))
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)

    assert _roda(tmp_path)["status"] == "erro"


def test_quadricromia_fecha_sozinha(monkeypatch, tmp_path):
    """O caminho de sempre continua sem pedir licenca a ninguem."""
    _monta_pagina(monkeypatch, {"C": .31, "M": .22, "Y": .18, "K": .09})
    feito = {}

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas, cinza=False, alvo=None):
        feito["base"] = base
        return os.path.join(saida, base + ".pdf"), ["C", "M", "Y", "K"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda *a: pytest.fail("quadricromia nao e pendencia"))

    r = _roda(tmp_path)
    assert r["status"] == "ok"
    assert feito["base"] == "510x400_CMYK_VOPRIX_Envelope_Saco"


def test_aprovado_fecha_fora_da_quadricromia(monkeypatch, tmp_path):
    """Depois do 'pode fechar', a mesma pagina passa."""
    _monta_pagina(monkeypatch, {"C": .0608, "M": .0608, "Y": .0608, "K": .0544},
                  cinza=True)
    feito = {}

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas, cinza=False, alvo=None):
        feito.update(base=base, cinza=cinza)
        return os.path.join(saida, base + ".pdf"), ["GRAY"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)

    r = _roda(tmp_path, aprovado=True)
    assert r["status"] == "ok"
    assert feito["cinza"] is True
    assert feito["base"] == "510x400_GRAY_VOPRIX_Envelope_Saco"


def test_solida_de_uma_cor_continua_fechando(monkeypatch, tmp_path):
    """A trava e da VOPRIX: a SOLIDA nao para por causa de cor."""
    _monta_pagina(monkeypatch, {"C": .00, "M": .00, "Y": .00, "K": .42})
    feito = {}

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas, cinza=False, alvo=None):
        feito["base"] = base
        return os.path.join(saida, base + ".pdf"), ["K"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda *a: pytest.fail("SOLIDA nao pode parar"))

    r = _roda(tmp_path, nome="49700 - Cliente - timbrado.pdf",
              cliente=P.SOLIDA)
    assert r["status"] == "ok" and feito["base"] == "49700"
