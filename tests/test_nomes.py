# -*- coding: utf-8 -*-
"""Nomes de saida, com os arquivos reais da pasta de entrada."""

from finart_ctp.nomes import extrair_os, extrair_oss, nome_saida, sufixo_pagina


def test_extrair_os_nome_de_entrada():
    assert extrair_os("49513 - Cliente - capa.pdf") == "49513"
    assert extrair_os("49596 - Cliente - rotulos adesivos.pdf") == "49596"


def test_extrair_os_com_prefixo():
    assert extrair_os("OS 49513 cliente.pdf") == "49513"
    assert extrair_os("os_49513.pdf") == "49513"


def test_extrair_varias_os():
    nome = "49581 49582 49583 - Cliente - bottons 7cm.pdf"
    assert extrair_oss(nome) == ["49581", "49582", "49583"]


def test_extrair_os_sem_numero():
    assert extrair_os("arte final.pdf") is None
    assert extrair_oss("arte final.pdf") == []


def test_numero_na_descricao_nao_vira_os():
    # "bola 30cm" nao pode virar OS
    assert extrair_oss("49584 - Cliente - bola 30cm.pdf") == ["49584"]


def test_sufixo_pagina():
    assert sufixo_pagina(0, 1) == ""
    assert (sufixo_pagina(0, 2), sufixo_pagina(1, 2)) == ("F", "V")
    assert [sufixo_pagina(i, 3) for i in range(3)] == ["1", "2", "3"]


def test_nome_saida_so_a_os():
    # a descricao do arquivo de origem NAO entra no nome
    assert nome_saida("49513 - Cliente - capa.pdf", "") == "49513"
    assert nome_saida("49513 - Cliente - miolo CAD1.pdf", "") == "49513"
    assert nome_saida("49572 - Cliente - flyer.pdf", "") == "49572"


def test_nome_saida_formato_grande():
    n = nome_saida("49576 - Cliente - informativo correios.pdf", "R1")
    assert n == "49576R1"


def test_nome_saida_frente_e_verso():
    orig = "49513 - Cliente - miolo CAD2.pdf"
    assert nome_saida(orig, "R1", 0, 2) == "49513R1 F"
    assert nome_saida(orig, "R1", 1, 2) == "49513R1 V"


def test_nome_saida_tres_paginas():
    orig = "49584 - Cliente - bola 30cm.pdf"
    assert [nome_saida(orig, "", i, 3) for i in range(3)] ==         ["49584 1", "49584 2", "49584 3"]


def test_nome_saida_varias_os():
    orig = "49581 49582 49583 - Cliente - bottons 7cm.pdf"
    assert nome_saida(orig, "") == "49581 49582 49583"


def test_nome_saida_sem_caractere_proibido():
    assert "/" not in nome_saida("49513 - X - capa 1/2.pdf", "")
