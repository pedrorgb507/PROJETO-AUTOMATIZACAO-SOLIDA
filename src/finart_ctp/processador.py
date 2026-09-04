# -*- coding: utf-8 -*-
"""
Processa um arquivo do cliente.

Dois clientes passam por aqui, e a diferenca entre eles esta so nas pontas:

  SOLIDA  PDF pronto  -> nome pela OS       49576R1
  VOPRIX  .cdr        -> nome pelo formato  510x400_CM_VOPRIX_Envelope_Saco

O .cdr da VOPRIX vira PDF pelo CorelDRAW da propria maquina (corel.py) e
desse ponto em diante o caminho e o mesmo: prova impressa, separacao de
tintas e uma chapa por pagina.

O arquivo de origem NUNCA e movido nem apagado: a pasta e compartilhada.
Quem controla o que ja foi feito e o registro, em utils.py.
"""

import glob
import os
import re
import shutil
import tempfile
import time

from .config import (AVISAR_QUANDO_NAO_FOR_CMYK, FORMATOS, FORMATOS_FIALHO,
                     IMPRESSORA, IMPRIMIR_ORIGINAL, NOMES_TINTA,
                     PASTA_CONTROLE, ROTULOS_PROVA, ROTULOS_PROVA_FIALHO,
                     ROTULOS_PROVA_VOPRIX, TAMANHO_MAXIMO_MB, TOLERANCIA_MM)
from .corel import ArquivoEmUso, publicar_pdf
from .ghostscript import (LIMIAR_TINTA, cobertura_por_pagina, sem_cor_gritante,
                          separar_cinza, separar_tintas, tintas_da_cobertura)
from .prova import imprimir
from .nomes import (extrair_oss, nome_saida, nome_saida_fialho,
                    nome_saida_voprix, resumo_fialho)
from .pdf_builder import montar_pdf, montar_pdf_cinza
from .utils import anotar_pendencia, guardar_para_a_mao, log, nome_livre

SOLIDA = "SOLIDA"
VOPRIX = "VOPRIX"
FIALHO = "FIALHO"


def medir_paginas(pdf):
    """[(largura_mm, altura_mm), ...] - uma por pagina, ja com /Rotate."""
    from pypdf import PdfReader
    r = PdfReader(pdf)
    medidas = []
    for p in r.pages:
        b = p.mediabox
        larg, alt = float(b.width) / 72 * 25.4, float(b.height) / 72 * 25.4
        if ((p.get("/Rotate") or 0) % 360) in (90, 270):
            larg, alt = alt, larg
        medidas.append((larg, alt))
    return medidas


def formatos_do_cliente(cliente=SOLIDA):
    """
    A tabela de chapas desse cliente.

    O Fialho tem a propria: a chapa grande dele e 730x600, que nao existe
    na Solida - e a 775x635 da Solida nao existe nele.
    """
    return FORMATOS_FIALHO if cliente == FIALHO else FORMATOS


def casar_formato(larg, alt, cliente=SOLIDA):
    """Chave do formato cadastrado que bate com a medida, ou None."""
    medido = sorted([larg, alt])
    for chave in formatos_do_cliente(cliente):
        alvo = sorted(chave)
        if (abs(medido[0] - alvo[0]) <= TOLERANCIA_MM and
                abs(medido[1] - alvo[1]) <= TOLERANCIA_MM):
            return chave
    return None


def identificar_formato(larg, alt, cliente=SOLIDA):
    """(dpi, sufixo) do formato que bate, ou (None, None)."""
    chave = casar_formato(larg, alt, cliente)
    return formatos_do_cliente(cliente)[chave] if chave else (None, None)


def formato_no_nome(larg, alt, cliente=SOLIDA):
    """'510x400' - como o formato entra no nome de saida."""
    chave = casar_formato(larg, alt, cliente)
    return "%dx%d" % chave if chave else ""


def chapas_aceitas(cliente=SOLIDA):
    """'510x400 ou 730x600' - para dizer no aviso o que era esperado."""
    return " ou ".join("%dx%d" % c for c in formatos_do_cliente(cliente))


def rotulo_prova(larg, alt, cliente=SOLIDA):
    """Texto que vai no canto da folha de prova. Vazio se nao reconhecer."""
    tabela = ROTULOS_PROVA
    if cliente == VOPRIX:
        tabela = ROTULOS_PROVA_VOPRIX
    elif cliente == FIALHO:
        tabela = ROTULOS_PROVA_FIALHO
    return tabela.get(casar_formato(larg, alt, cliente), "")


def pagina_de_uma_cor(cob, folga=0.02):
    """
    True quando a pagina e preto sozinho - puro ou composto.

    Arte de uma cor nao chega aqui como preto puro: a Corel exporta o
    preto composto, com C, M, Y e K juntos. O que denuncia isso e a
    cobertura das tres cores dar o MESMO numero (num arquivo real:
    C 0.06081, M 0.06079, Y 0.06080, K 0.05444). Arte colorida nunca faz
    isso - cada canal tem o seu total.

    Rodar esse arquivo como quadricromia daria QUATRO chapas onde o
    trabalho pede uma; e pegar so o canal K daria chapa lavada, porque o
    preto esta espalhado pelos quatro canais.
    """
    cmy = [cob["C"], cob["M"], cob["Y"]]
    if max(cmy) <= LIMIAR_TINTA:
        return cob["K"] > LIMIAR_TINTA               # preto puro
    return (max(cmy) - min(cmy)) <= folga * max(cmy)  # preto composto


def proxima_sequencia(pasta_saida, prefixo):
    """
    O proximo numero livre da sequencia do dia para esse trabalho.

    As chapas do Fialho sao numeradas por TRABALHO e por DIA, e nao por
    arquivo: as 11 chapas de UNICIDADES de um dia sairam 01 a 11 mesmo
    vindo de tres PDFs diferentes (forro, introducao e divisoria). Por
    isso a conta se faz olhando a pasta de saida, nao o arquivo de origem.
    """
    padrao = re.compile(r"^%s (\d+)\.pdf$" % re.escape(prefixo), re.IGNORECASE)
    maior = 0
    try:
        nomes = os.listdir(pasta_saida)
    except OSError:
        return 1
    for nome in nomes:
        achou = padrao.match(nome)
        if achou:
            maior = max(maior, int(achou.group(1)))
    return maior + 1


def nome_da_chapa(cliente, nome, sufixo, larg, alt, tintas, indice, total,
                  pasta_saida=None):
    """Nome de saida (sem .pdf), pela regra do cliente."""
    if cliente == VOPRIX:
        return nome_saida_voprix(nome, formato_no_nome(larg, alt, cliente),
                                 tintas, indice, total)
    if cliente == FIALHO:
        formato = formato_no_nome(larg, alt, cliente)
        prefixo = "%s_FIALHO_%s" % (formato, resumo_fialho(nome))
        seq = (proxima_sequencia(pasta_saida, prefixo) if pasta_saida
               else indice + 1)
        return nome_saida_fialho(nome, formato, seq)
    return nome_saida(nome, sufixo or "", indice, total)


def acima_do_limite(caminho):
    """Motivo da recusa por tamanho, ou '' se o arquivo couber."""
    mb = os.path.getsize(caminho) / 1048576
    if mb <= TAMANHO_MAXIMO_MB:
        return ""
    return ("arquivo gigante: %.0f MB, acima do limite de %d MB. "
            "Nao processei - precisa ser tratado a mao"
            % (mb, TAMANHO_MAXIMO_MB))


def converter_cdr(caminho):
    """
    (pdf, pasta_temporaria) do .cdr publicado pelo CorelDRAW.

    O PDF sai no disco local: a Corel exporta arquivos enormes e isso nao
    pode passar pela rede. Quem chamou apaga a pasta no fim.
    """
    os.makedirs(PASTA_CONTROLE, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="ctp_cdr_", dir=PASTA_CONTROLE)
    base = os.path.splitext(os.path.basename(caminho))[0]
    try:
        return publicar_pdf(caminho, os.path.join(tmp, base + ".pdf")), tmp
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


def _gerar_chapa(origem, pasta_saida, base, pagina, dpi, larg, alt, usadas,
                 cinza=False):
    """
    Separa uma pagina e monta o PDF final. Devolve o caminho gerado.

    Com cinza=True sai UMA chapa em escala de cinza, no lugar das quatro
    da quadricromia: e o caso da arte de uma cor so.

    Os TIFFs da separacao ficam SEMPRE no disco local: sao varios GB e
    passar isso pela rede tornaria tudo lento.
    """
    os.makedirs(PASTA_CONTROLE, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="ctp_p%d_" % pagina, dir=PASTA_CONTROLE)
    try:
        if cinza:
            tif = separar_cinza(origem, dpi, tmp, pagina)
            saida = nome_livre(pasta_saida, base)
            return saida, montar_pdf_cinza(tif, saida, larg, alt)

        separar_tintas(origem, dpi, tmp, pagina)

        tifs = {}
        for tif in sorted(glob.glob(os.path.join(tmp, "s(*).tif"))):
            tinta = re.search(r"\(([^)]+)\)", os.path.basename(tif)).group(1)
            if tinta in NOMES_TINTA:
                letra = NOMES_TINTA[tinta]
                if letra not in usadas:
                    continue                      # separacao vazia, descarta
            else:
                letra = re.sub(r"[^A-Za-z0-9]+", "", tinta)[:16]
                log("   cor especial: %s" % tinta, alerta=True)
            tifs[letra] = tif

        if not tifs:
            raise RuntimeError("nenhuma tinta encontrada na pagina %d" % pagina)

        saida = nome_livre(pasta_saida, base)
        letras = montar_pdf(tifs, saida, larg, alt)
        return saida, letras
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def processar(caminho, pasta_saida, cliente=SOLIDA, aprovado=False):
    """
    Fluxo completo de um arquivo.

    Devolve {"status": "ok"|"erro"|"espera"|"adiado", "saidas": [...],
    "motivo": "..."}. Nunca levanta excecao para cima.

    "adiado" e so da VOPRIX: o .cdr esta aberto no CorelDRAW do operador
    e nao encostamos nele. Nao entra no registro - fica para a proxima
    passada, quando a pessoa tiver fechado o arquivo.

    Quando a VOPRIX da errado depois de converter, o PDF nao e jogado
    fora: vai para a PASTA_PENDENCIAS, para o trabalho da Corel nao se
    perder e voce continuar dali.

    aprovado=True e a pessoa dizendo "pode fechar": pula o aviso do
    AVISAR_QUANDO_NAO_FOR_CMYK e gera a chapa mesmo fora da quadricromia.
    """
    nome = os.path.basename(caminho)
    resultado = {"status": "ok", "saidas": [], "motivo": "",
                 "impresso": None}

    def falhar(motivo):
        log("%s: %s" % (nome, motivo), alerta=True)
        anotar_pendencia(nome, motivo)
        resultado["status"] = "erro"
        resultado["motivo"] = motivo
        return resultado

    motivo = acima_do_limite(caminho)
    if motivo:
        return falhar(motivo)

    # PASSO 0, so da VOPRIX: o .cdr vira PDF pelo CorelDRAW da maquina.
    temporaria = None
    trabalho = caminho
    if cliente == VOPRIX:
        try:
            log("'%s': convertendo no CorelDRAW..." % nome)
            trabalho, temporaria = converter_cdr(caminho)
        except ArquivoEmUso as e:
            resultado["status"] = "adiado"
            resultado["motivo"] = str(e)
            return resultado
        except Exception as e:
            return falhar("CorelDRAW nao converteu: %s" % e)
    elif cliente == FIALHO:
        # Padrao temporario: so anda o que ja vem em PDF, no tamanho da
        # chapa. Corel e arte por montar param aqui e esperam gente.
        if not nome.lower().endswith(".pdf"):
            ext = os.path.splitext(nome)[1] or "sem extensao"
            return falhar("veio em %s, nao em PDF - montagem ainda e na "
                          "mao. Nao dei andamento no servico" % ext)
    elif not extrair_oss(nome):
        return falhar("nao achei numero de OS no nome")

    try:
        # O PDF que a Corel devolve pode ser muito maior que o .cdr: um
        # arquivo de 375 MB ja virou um PDF de 2,2 GB.
        motivo = acima_do_limite(trabalho)
        if motivo:
            return falhar("depois de converter, " + motivo)

        return _processar_pdf(trabalho, nome, pasta_saida, cliente,
                              resultado, falhar, aprovado)
    finally:
        # O que a Corel converteu nao se joga fora so porque nao deu para
        # seguir: fica guardado para a mao, e a conversao nao se repete.
        if temporaria:
            if resultado["status"] == "erro" and os.path.isfile(trabalho):
                guardado = guardar_para_a_mao(trabalho, nome)
                if guardado:
                    resultado["pendencia"] = guardado
                    log("   o PDF convertido ficou em %s - abra ele no "
                        "Photoshop/InDesign, nao precisa converter de novo"
                        % guardado, alerta=True)
            shutil.rmtree(temporaria, ignore_errors=True)


def _processar_pdf(pdf, nome, pasta_saida, cliente, resultado, falhar,
                   aprovado=False):
    """
    O caminho comum aos dois clientes, pagina a pagina.

    'pdf' e o arquivo que vai ser lido e impresso - na VOPRIX, o que a
    Corel acabou de gerar. 'nome' e sempre o do arquivo original, que e
    quem manda no nome de saida.
    """
    try:
        medidas = medir_paginas(pdf)
        cobertura = cobertura_por_pagina(pdf)
    except Exception as e:
        return falhar("PDF ilegivel: %s" % e)

    total = len(medidas)
    if not total:
        return falhar("PDF sem paginas")

    log("'%s': %d pagina(s)" % (nome, total))
    os.makedirs(pasta_saida, exist_ok=True)
    problemas = []

    # PASSO 1: prova impressa, com a arte inteira. So vale a pena gastar
    # papel se alguma pagina tiver formato conhecido.
    if IMPRIMIR_ORIGINAL and any(identificar_formato(l, a, cliente)[0]
                                 for l, a in medidas):
        try:
            etiquetas = [rotulo_prova(l, a, cliente) for l, a in medidas]
            _, folhas = imprimir(pdf, etiquetas=etiquetas)
            log("   impresso em %s (%d folha%s, so frente)"
                % (IMPRESSORA, folhas, "s" if folhas > 1 else ""))
            resultado["impresso"] = folhas
        except Exception as e:
            # Sem prova, sem chapa: segura o arquivo e tenta de novo depois.
            log("   NAO IMPRIMIU (%s): %s" % (IMPRESSORA, e), alerta=True)
            resultado["status"] = "espera"
            resultado["motivo"] = "impressora fora: %s" % e
            resultado["impresso"] = False
            return resultado

    for i, (larg, alt) in enumerate(medidas):
        dpi, sufixo = identificar_formato(larg, alt, cliente)

        if not dpi:
            motivo = ("pagina %d: %.0f x %.0f mm nao e chapa (%s)"
                      % (i + 1, larg, alt, chapas_aceitas(cliente)))
            if cliente == FIALHO:
                motivo += " - nao dei andamento no servico"
            log("   " + motivo, alerta=True)
            anotar_pendencia(nome, motivo)
            problemas.append(motivo)
            continue

        cob = cobertura[i] if i < len(cobertura) else None
        usadas = tintas_da_cobertura(cob) if cob else set("CMYK")

        # Arte de uma cor so chega como preto composto (C, M, Y e K em
        # partes iguais). Vale uma chapa em cinza, nao quatro. Duas
        # perguntas: os totais batem, e nao ha cor gritante em pixel nenhum.
        cinza = (cliente == VOPRIX and cob is not None
                 and pagina_de_uma_cor(cob) and sem_cor_gritante(pdf, i + 1))
        if cinza:
            usadas = {"GRAY"}
            log("   p%d: cobertura C %.4f M %.4f Y %.4f K %.4f - arte de "
                "uma cor, a chapa sai em escala de cinza"
                % (i + 1, cob["C"], cob["M"], cob["Y"], cob["K"]), alerta=True)

        base = nome_da_chapa(cliente, nome, sufixo, larg, alt, usadas, i,
                             total, pasta_saida)
        log("   p%d -> %s | %.0fx%.0f mm | %d dpi | tintas: %s"
            % (i + 1, base, larg, alt, dpi, "".join(sorted(usadas)) or "?"))

        # Quadricromia fecha sozinha. Fora dela, quem manda fechar e gente:
        # o programa para aqui, com os numeros na tela, e guarda o PDF.
        if (AVISAR_QUANDO_NAO_FOR_CMYK and cliente == VOPRIX
                and not aprovado and usadas != set("CMYK")):
            numeros = ("C %.4f M %.4f Y %.4f K %.4f"
                       % (cob["C"], cob["M"], cob["Y"], cob["K"])
                       if cob else "cobertura desconhecida")
            motivo = ("pagina %d: NAO veio em quadricromia - %s (%s). "
                      "Sairia como %s. Nao fechei: confira antes"
                      % (i + 1, "".join(sorted(usadas)) or "?", numeros, base))
            anotar_pendencia(nome, motivo)
            problemas.append(motivo)
            continue

        # Sem a descricao no nome, duas artes da mesma OS batem de frente.
        if os.path.exists(os.path.join(pasta_saida, base + ".pdf")):
            aviso = ("ja existe %s.pdf (outra arte com o mesmo nome de "
                     "saida); este saiu como _v2" % base)
            log("   ATENCAO: " + aviso, alerta=True)
            anotar_pendencia(nome, aviso)

        inicio = time.time()
        try:
            saida, letras = _gerar_chapa(pdf, pasta_saida, base, i + 1,
                                         dpi, larg, alt, usadas, cinza)
        except Exception as e:
            motivo = "pagina %d: %s" % (i + 1, e)
            log("   FALHOU: %s" % motivo, alerta=True)
            anotar_pendencia(nome, motivo)
            problemas.append(motivo)
            continue

        mb = os.path.getsize(saida) / 1048576
        log("   OK em %.0fs: %s (%s, %.1f MB)"
            % (time.time() - inicio, os.path.basename(saida),
               "+".join(letras), mb))
        resultado["saidas"].append(os.path.basename(saida))

    if problemas:
        resultado["status"] = "erro"
        resultado["motivo"] = " ; ".join(problemas)
    return resultado
