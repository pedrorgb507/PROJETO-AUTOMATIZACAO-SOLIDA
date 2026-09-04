# -*- coding: utf-8 -*-
"""
O padrao temporario do FIALHO BRINDES.

So anda o que chega em PDF ja no tamanho da chapa (510x400 ou 730x600).
O resto - Corel, arte fora de medida - para e vira pendencia.

Os nomes usados aqui sao os arquivos de verdade da pasta do cliente.
"""

import os

import pytest

import finart_ctp.monitor as M
import finart_ctp.processador as P
import finart_ctp.utils as U
from finart_ctp.nomes import nome_saida_fialho, resumo_fialho


@pytest.fixture(autouse=True)
def sem_log(monkeypatch, tmp_path):
    monkeypatch.setattr(P, "log", lambda *a, **k: None)
    monkeypatch.setattr(M, "log", lambda *a, **k: None)
    monkeypatch.setattr(U, "PASTA_PENDENCIAS", str(tmp_path / "_pend_teste"))
    monkeypatch.setattr(U, "PASTA_CONTROLE", str(tmp_path / "_ctrl_teste"))


# ----------------------------------------------------------------------
# O nome principal do servico
# ----------------------------------------------------------------------

def test_nome_principal_e_o_cliente_e_nao_o_material():
    """'forro', 'capa' e 'miolo' sao material; o servico e o cliente."""
    assert resumo_fialho("FORRO AGENDA unicidades  2027.pdf") == "UNICIDADES"
    assert resumo_fialho("capa AGENDA UNICIDADES.pdf") == "UNICIDADES"
    assert resumo_fialho("INTRODUÇÃO  unicidades.pdf") == "UNICIDADES"
    assert resumo_fialho("CAPA Agenda PAULISTA  2027.pdf") == "PAULISTA"


def test_medida_e_contagem_saem_do_nome():
    n = "MIOLO caderno sicoob montagen formato 48x66 9 imagem 2 chapas.pdf"
    assert resumo_fialho(n) == "SICOOB"


def test_acento_e_caractere_especial_somem():
    assert resumo_fialho("INTRODUÇÃO  unicidades.pdf") == "UNICIDADES"
    n = "biocromo novo modelo  envelope  15,5x22 sem janela com nº.pdf"
    assert resumo_fialho(n) == "BIOCROMO"


def test_sem_nome_principal_repete_o_arquivo_limpo():
    """Combinado: melhor um nome comprido do que uma chapa sem nome."""
    n = "divisoria colorida  montagem para agenda de dobra.pdf"
    assert (resumo_fialho(n)
            == "DIVISORIA COLORIDA MONTAGEM PARA AGENDA DE DOBRA")


def test_nome_de_saida_completo():
    assert (nome_saida_fialho("FORRO AGENDA unicidades  2027.pdf",
                              "510x400", 1)
            == "510x400_FIALHO_UNICIDADES 01")
    assert (nome_saida_fialho("MIOLO caderno sicoob 48x66.pdf", "730x600", 12)
            == "730x600_FIALHO_SICOOB 12")


# ----------------------------------------------------------------------
# A sequencia e do dia, nao do arquivo
# ----------------------------------------------------------------------

def test_sequencia_continua_de_onde_o_dia_parou(tmp_path):
    """
    As 11 chapas de UNICIDADES sairam 01 a 11 vindo de tres PDFs. Entao a
    contagem olha a pasta do dia, e nao a pagina do arquivo.
    """
    for n in ("510x400_FIALHO_UNICIDADES 01.pdf",
              "510x400_FIALHO_UNICIDADES 02.pdf",
              "510x400_FIALHO_UNICIDADES 03.pdf"):
        (tmp_path / n).write_bytes(b"chapa")

    assert P.proxima_sequencia(str(tmp_path),
                               "510x400_FIALHO_UNICIDADES") == 4


def test_sequencia_nao_confunde_trabalhos_diferentes(tmp_path):
    (tmp_path / "510x400_FIALHO_UNICIDADES 07.pdf").write_bytes(b"x")
    (tmp_path / "730x600_FIALHO_SICOOB 02.pdf").write_bytes(b"x")

    assert P.proxima_sequencia(str(tmp_path), "730x600_FIALHO_SICOOB") == 3
    assert P.proxima_sequencia(str(tmp_path), "510x400_FIALHO_PAULISTA") == 1


def test_sequencia_em_pasta_que_nem_existe(tmp_path):
    assert P.proxima_sequencia(str(tmp_path / "nao_existe"), "x") == 1


def test_nome_da_chapa_usa_a_pasta_para_numerar(tmp_path):
    (tmp_path / "510x400_FIALHO_UNICIDADES 01.pdf").write_bytes(b"x")
    nome = P.nome_da_chapa(P.FIALHO, "INTRODUÇÃO  unicidades.pdf", "",
                           510, 400, set("CMYK"), 0, 2, str(tmp_path))
    assert nome == "510x400_FIALHO_UNICIDADES 02"


# ----------------------------------------------------------------------
# Formatos: a tabela do Fialho e outra
# ----------------------------------------------------------------------

def test_chapa_grande_do_fialho_e_730x600():
    assert P.identificar_formato(730, 600, P.FIALHO) == (800, "")
    assert P.identificar_formato(600, 730, P.FIALHO) == (800, "")   # deitado
    assert P.identificar_formato(510, 400, P.FIALHO) == (1000, "")


def test_formato_da_solida_nao_vale_no_fialho():
    """775x635 e chapa da Solida; no Fialho nao existe."""
    assert P.identificar_formato(775, 635, P.FIALHO) == (None, None)
    assert P.identificar_formato(730, 600) == (None, None)


def test_520x400_nao_bate_exato_mas_encaixa():
    """O CAPA Agenda PAULISTA mede 520x400: 10 mm fora, e chapa 510x400."""
    assert P.identificar_formato(520, 400, P.FIALHO) == (None, None)
    assert P.encaixar_formato(520, 400, P.FIALHO) == (510, 400)

    chapa, dpi, _, encaixou = P.chapa_da_pagina(520, 400, P.FIALHO)
    assert (chapa, dpi, encaixou) == ((510, 400), 1000, True)


def test_encaixe_respeita_o_sentido_da_arte():
    """Arte em pe encaixa na chapa em pe: nada e girado nem esticado."""
    chapa, _, _, encaixou = P.chapa_da_pagina(400, 520, P.FIALHO)
    assert chapa == (400, 510) and encaixou


def test_arte_longe_da_chapa_nao_encaixa():
    """Acima do limite ninguem sabe o que pode ser cortado."""
    assert P.encaixar_formato(600, 400, P.FIALHO) is None
    assert P.chapa_da_pagina(600, 400, P.FIALHO)[1] is None


def test_encaixe_nao_vale_para_os_outros_clientes():
    """Corte as cegas so foi combinado com o Fialho."""
    assert P.encaixar_formato(520, 400, P.SOLIDA) is None
    assert P.encaixar_formato(520, 400, P.VOPRIX) is None
    assert P.chapa_da_pagina(520, 400, P.SOLIDA)[1] is None


def test_medida_exata_nao_mexe_no_tamanho_da_arte():
    """Batendo na tolerancia, a chapa sai do tamanho que a arte tem."""
    chapa, dpi, _, encaixou = P.chapa_da_pagina(512, 398, P.FIALHO)
    assert chapa == (512, 398) and dpi == 1000 and not encaixou


def test_etiqueta_sai_mesmo_quando_a_arte_so_encaixa():
    assert P.rotulo_prova(520, 400, P.FIALHO) == "FIALHO F4"


def test_etiqueta_da_prova_do_fialho():
    assert P.rotulo_prova(510, 400, P.FIALHO) == "FIALHO F4"
    assert P.rotulo_prova(730, 600, P.FIALHO) == "FIALHO F2"


# ----------------------------------------------------------------------
# O que nao esta no padrao para aqui
# ----------------------------------------------------------------------

def test_corel_do_fialho_nao_anda(monkeypatch, tmp_path):
    """Sem montagem automatica ainda: o .cdr so avisa."""
    cdr = tmp_path / "CALENDARIO SICRED MONTAGEM.cdr"
    cdr.write_bytes(b"cdr")
    avisos = []
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda arq, motivo: avisos.append(motivo))
    monkeypatch.setattr(P, "converter_cdr",
                        lambda *a: pytest.fail("Fialho nao converte ainda"))

    r = P.processar(str(cdr), str(tmp_path / "saida"), P.FIALHO)

    assert r["status"] == "erro"
    assert "nao em PDF" in r["motivo"]
    assert "Nao dei andamento" in avisos[0]


def test_fialho_nao_exige_numero_de_os(monkeypatch, tmp_path):
    """A regra da OS e da Solida: os nomes do Fialho nao tem numero."""
    pdf = tmp_path / "FORRO AGENDA unicidades  2027.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(P, "anotar_pendencia", lambda *a: None)

    r = P.processar(str(pdf), str(tmp_path / "saida"), P.FIALHO)
    assert "nao achei numero de OS" not in r["motivo"]


def test_520x400_fecha_centralizado_na_510x400(monkeypatch, tmp_path):
    """O CAPA Agenda PAULISTA: entra centralizado, 5 mm cortados por lado."""
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(520, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina",
                        lambda pdf: [{"C": .1, "M": .1, "Y": .1, "K": .1}])
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)
    feito = {}

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas,
              cinza=False, alvo=None):
        feito.update(base=base, chapa=(larg, alt), alvo=alvo, dpi=dpi)
        return os.path.join(saida, base + ".pdf"), ["C", "M", "Y", "K"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(os.path, "getsize", lambda c: 1000)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda *a: pytest.fail("nao e mais pendencia"))

    r = P._processar_pdf("x.pdf", "CAPA Agenda PAULISTA  2027.pdf",
                         str(tmp_path), P.FIALHO,
                         {"status": "ok", "saidas": [], "motivo": "",
                          "impresso": None}, lambda m: None)

    assert r["status"] == "ok"
    assert feito["base"] == "510x400_FIALHO_PAULISTA 01"   # nome pela CHAPA
    assert feito["chapa"] == (510, 400)                    # pagina do PDF
    assert feito["alvo"] == (20079, 15748)                 # 510x400 a 1000 dpi


def test_pagina_longe_da_medida_ainda_vira_pendencia(monkeypatch, tmp_path):
    """600x400 esta longe demais: continua parando, como antes."""
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(600, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina",
                        lambda pdf: [{"C": .1, "M": .1, "Y": .1, "K": .1}])
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)
    monkeypatch.setattr(P, "_gerar_chapa",
                        lambda *a, **k: pytest.fail("nao podia ter fechado"))
    avisos = []
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda arq, motivo: avisos.append(motivo))

    r = P._processar_pdf("x.pdf", "arte torta.pdf", str(tmp_path), P.FIALHO,
                         {"status": "ok", "saidas": [], "motivo": "",
                          "impresso": None}, lambda m: None)

    assert r["status"] == "erro" and r["saidas"] == []
    assert "600 x 400 mm nao e chapa" in avisos[0]
    assert "510x400" in avisos[0] and "730x600" in avisos[0]
    assert "nao dei andamento" in avisos[0]


def test_pdf_no_tamanho_certo_fecha(monkeypatch, tmp_path):
    """730x600, o miolo do SICOOB: caminho normal, chapa gerada."""
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(730, 600), (730, 600)])
    monkeypatch.setattr(P, "cobertura_por_pagina",
                        lambda pdf: [{"C": .2, "M": .2, "Y": .2, "K": .1}] * 2)
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)
    feitos = []

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas, cinza=False, alvo=None):
        feitos.append((base, dpi))
        alvo = os.path.join(saida, base + ".pdf")
        open(alvo, "wb").write(b"chapa")
        return alvo, ["C", "M", "Y", "K"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda *a: pytest.fail("nao e pendencia"))

    r = P._processar_pdf("x.pdf", "MIOLO caderno sicoob 48x66.pdf",
                         str(tmp_path), P.FIALHO,
                         {"status": "ok", "saidas": [], "motivo": "",
                          "impresso": None}, lambda m: None)

    assert r["status"] == "ok"
    assert feitos == [("730x600_FIALHO_SICOOB 01", 800),
                      ("730x600_FIALHO_SICOOB 02", 800)]


def test_a_trava_de_cor_da_voprix_nao_pega_o_fialho(monkeypatch, tmp_path):
    """Fialho de uma cor fecha normal: a trava do CMYK e so da VOPRIX."""
    monkeypatch.setattr(P, "medir_paginas", lambda pdf: [(510, 400)])
    monkeypatch.setattr(P, "cobertura_por_pagina",
                        lambda pdf: [{"C": 0, "M": 0, "Y": 0, "K": .42}])
    monkeypatch.setattr(P, "IMPRIMIR_ORIGINAL", False)
    monkeypatch.setattr(P, "sem_cor_gritante",
                        lambda *a: pytest.fail("regra de cinza e da VOPRIX"))
    feitos = []

    def gerar(origem, saida, base, pagina, dpi, larg, alt, usadas, cinza=False, alvo=None):
        feitos.append(base)
        return os.path.join(saida, base + ".pdf"), ["K"]

    monkeypatch.setattr(P, "_gerar_chapa", gerar)
    monkeypatch.setattr(os.path, "getsize", lambda c: 1000)
    monkeypatch.setattr(P, "anotar_pendencia",
                        lambda *a: pytest.fail("nao e pendencia"))

    r = P._processar_pdf("x.pdf", "FORRO AGENDA unicidades  2027.pdf",
                         str(tmp_path), P.FIALHO,
                         {"status": "ok", "saidas": [], "motivo": "",
                          "impresso": None}, lambda m: None)

    assert r["status"] == "ok" and feitos == ["510x400_FIALHO_UNICIDADES 01"]


# ----------------------------------------------------------------------
# Monitor
# ----------------------------------------------------------------------

def test_monitor_vigia_as_tres_pastas(monkeypatch):
    monkeypatch.setattr(M, "BASE_ENTRADA_VOPRIX", r"V:\VOPRIX")
    monkeypatch.setattr(M, "BASE_ENTRADA_FIALHO", r"V:\Fialho Brindes")
    lista = M.clientes()
    assert [c[0] for c in lista] == [M.SOLIDA, M.VOPRIX, M.FIALHO]
    assert lista[2][2] == (".pdf", ".cdr")     # o .cdr entra so para avisar


def test_varrer_do_fialho_ve_pdf_e_cdr(monkeypatch, tmp_path):
    (tmp_path / "FORRO AGENDA unicidades  2027.pdf").write_bytes(b"x")
    (tmp_path / "CALENDARIO SICRED MONTAGEM.cdr").write_bytes(b"x")
    (tmp_path / "planilha.xlsx").write_bytes(b"x")

    vistos = []
    monkeypatch.setattr(M, "arquivo_estavel", lambda c: True)
    monkeypatch.setattr(M, "salvar_registro", lambda r: None)
    monkeypatch.setattr(M, "processar", lambda caminho, saida, cliente: (
        vistos.append(os.path.basename(caminho))
        or {"status": "ok", "saidas": [], "motivo": "", "impresso": None}))

    M.varrer(str(tmp_path), "Z:/saida", {}, None, M.FIALHO, (".pdf", ".cdr"))

    assert sorted(vistos) == ["CALENDARIO SICRED MONTAGEM.cdr",
                              "FORRO AGENDA unicidades  2027.pdf"]


# ----------------------------------------------------------------------
# O corte, em pixel
# ----------------------------------------------------------------------

def _imagem_da_chapa(pdf):
    """(largura, altura, bytes) da imagem que ficou dentro do PDF."""
    import re
    import zlib
    dados = open(pdf, "rb").read()
    cab = re.search(rb"/Width (\d+) /Height (\d+)", dados)
    w, h = int(cab.group(1)), int(cab.group(2))
    inicio = dados.index(b"stream\n", cab.end()) + 7
    fim = dados.index(b"\nendstream", inicio)
    return w, h, zlib.decompress(dados[inicio:fim])


def test_arte_maior_e_cortada_igual_dos_dois_lados(tmp_path):
    """Arte 100 de largura na chapa de 80: some 10 de cada lado."""
    from PIL import Image
    from finart_ctp.pdf_builder import montar_pdf_cinza

    arte = Image.new("L", (100, 40), 128)
    for x in range(100):
        arte.putpixel((x, 0), x)            # regua para saber o que sobrou
    tif = str(tmp_path / "arte.tif")
    arte.save(tif)

    saida = str(tmp_path / "chapa.pdf")
    montar_pdf_cinza(tif, saida, 510, 400, alvo=(80, 40))

    w, h, px = _imagem_da_chapa(saida)
    assert (w, h) == (80, 40)
    primeira_linha = px[:80]
    assert primeira_linha[0] == 10          # os 10 primeiros foram cortados
    assert primeira_linha[-1] == 89         # e os 10 ultimos tambem


def test_arte_menor_ganha_branco_em_volta(tmp_path):
    """Arte 60 de largura na chapa de 80: 10 de branco de cada lado."""
    from PIL import Image
    from finart_ctp.pdf_builder import montar_pdf_cinza

    arte = Image.new("L", (60, 20), 0)      # tudo preto, para o branco saltar
    tif = str(tmp_path / "arte.tif")
    arte.save(tif)

    saida = str(tmp_path / "chapa.pdf")
    montar_pdf_cinza(tif, saida, 510, 400, alvo=(80, 30))

    w, h, px = _imagem_da_chapa(saida)
    assert (w, h) == (80, 30)
    assert px[:80] == b"\xff" * 80          # faixa de cima: branca inteira
    meio = px[15 * 80:16 * 80]              # linha no meio da arte
    assert meio[:10] == b"\xff" * 10        # borda esquerda branca
    assert meio[10:70] == b"\x00" * 60      # arte preta no centro
    assert meio[70:] == b"\xff" * 10        # borda direita branca


def test_sem_alvo_a_imagem_sai_do_tamanho_que_entrou(tmp_path):
    """Quem bate na medida exata nao passa por corte nenhum."""
    from PIL import Image
    from finart_ctp.pdf_builder import montar_pdf_cinza

    tif = str(tmp_path / "arte.tif")
    Image.new("L", (50, 30), 77).save(tif)
    saida = str(tmp_path / "chapa.pdf")
    montar_pdf_cinza(tif, saida, 510, 400)

    w, h, px = _imagem_da_chapa(saida)
    assert (w, h) == (50, 30)
    assert px == b"\x4d" * (50 * 30)
