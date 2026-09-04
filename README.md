# PROJETO FECHAMENTO CHAPA

Fechamento de chapas para o CTP da Finart.

Vigia a pasta do dia do cliente no servidor. A cada PDF novo: mede cada página,
descobre quais tintas ela usa de verdade e gera **um PDF por página, só com essas
tintas**, no dpi certo e com o nome montado a partir da OS. Substitui o passo
manual no Photoshop/InDesign.

**O original nunca é movido nem apagado** — a pasta de entrada é compartilhada.
O controle do que já foi feito fica num `_processados.json` no próprio PC.

Há dois fluxos, cada um com sua pasta de entrada:

- **SOLIDA** — PDFs nomeados pela OS (`49513 - Cliente - capa.pdf`). É o padrão.
- **VOPRIX** — arquivos `.cdr` já montados no tamanho da chapa. O programa
  converte pelo próprio CorelDRAW da máquina e segue o mesmo caminho.
  Veja [VOPRIX (.cdr)](#voprix-cdr).

## Pastas

| | |
|---|---|
| Entrada SOLIDA | `X:\ENTRADA\<MÊS>\<DIA>` — ex.: `X:\ENTRADA\SETEMBRO\02` |
| Entrada VOPRIX | `Z:\VOPRIX\<MÊS>\<DIA>` — só `.cdr`; `BASE_ENTRADA_VOPRIX = None` desliga |
| Saída | `Y:\CTP\<MÊS>\<DIA>\FIA` — ex.: `Y:\CTP\SETEMBRO\03\FIA` (os dois fluxos gravam aqui) |
| Controle | `C:\CTP\_controle` — log e registro ficam no PC, fora da rede |

A pasta `FIA` fica ao lado das dos outros operadores (uma pasta por operador)
e é criada sozinha todo dia. O nome do mês é encontrado como está escrito no
servidor — `MARÇO`, `Marco`, `Fevereiro` e `FEVEREIRO` são a mesma pasta.

## Passo 1: prova impressa

Antes de gerar qualquer chapa, o **arquivo original do cliente** sai impresso na
a impressora configurada, em **A4 retrato, só na frente**.

A prova é montada aqui: a arte é rasterizada e centralizada numa folha A4 em pé
(arte deitada é girada).

A folha leva no canto superior esquerdo, **fora da arte**, a etiqueta do
formato — o alto da folha ganha uma faixa em branco e a arte desce para
caber embaixo dela:

| Formato da chapa | Etiqueta SOLIDA | Etiqueta VOPRIX |
|---|---|---|
| 510 × 400 mm | `SOLIDA F4` | `VOPRIX F4` |
| 775 × 635 mm | `SOLIDA F2` | `VOPRIX F2` |

Formato não reconhecido sai sem etiqueta. O texto fica em `ROTULOS_PROVA` e
`ROTULOS_PROVA_VOPRIX`, no `config.py`.
 Duas razões para não mandar o PDF do cliente direto:

- o `-dFitPage` do Ghostscript 10.03.1 quebra quando precisa girar a página, que
  é exatamente o caso de uma chapa deitada indo para folha em pé;
- **cada página vira um trabalho de impressão separado.** A impressora está em
  duplex, e um trabalho de 2 páginas sairia frente e verso na mesma folha.
  Mandando um por vez, um arquivo de 2 páginas sai em 2 folhas, cada uma só na
  frente — sem precisar mexer na configuração da impressora, que é de todos.

**Se a impressora falhar, nenhuma chapa é gerada.** O arquivo fica segurado, o
programa avisa no log e tenta de novo a cada 5 minutos, sozinho. Quando a
impressora voltar, ele retoma a fila do ponto onde parou — nada se perde e nada
precisa ser refeito à mão. Nada entra no registro enquanto a prova não sair.

Para desligar a impressão: `IMPRIMIR_ORIGINAL = False` no `config.py`.

## Formatos e dpi

| Tamanho da página | DPI  | Sufixo |
|-------------------|------|--------|
| 510 × 400 mm      | 1000 | —      |
| 775 × 635 mm      | 800  | `R1`   |
| qualquer outro    | —    | anotado em `_PENDENCIAS.txt`, sem processar |

## Nome do arquivo de saída

Só o número da OS. A descrição do arquivo de origem (`capa`, `miolo CAD1`)
não entra no nome.

| Original | Sai como |
|---|---|
| `49572 - Cliente - flyer.pdf` (510×400) | `49572.pdf` |
| `49576 - Cliente - informativo correios.pdf` (775×635) | `49576R1.pdf` |
| `49513 - Cliente - miolo CAD2.pdf` (775×635, 2 páginas) | `49513R1 F.pdf` e `49513R1 V.pdf` |
| 3 páginas ou mais | `49513 1.pdf`, `49513 2.pdf`, `49513 3.pdf` |
| `49581 49582 49583 - Cliente - bottons 7cm.pdf` | `49581 49582 49583.pdf` |

Se duas artes do mesmo dia tiverem a mesma OS e o mesmo formato — como a
`capa` e o `miolo CAD1` da OS 49513 —, a segunda sai como `49513_v2.pdf` e o
caso é anotado no `_PENDENCIAS.txt`, para você renomear como preferir.

## VOPRIX (.cdr)

A VOPRIX manda `.cdr` numa pasta só dela (`BASE_ENTRADA_VOPRIX`, mesma árvore
`MÊS\DIA`). Cada arquivo já vem montado no tamanho da chapa e o nome segue
outro padrão:

```
Envelope_Saco_23x31,5_Colegio_Unus.cdr
└─ produto ──┘ └ medida ┘ └── cliente ──┘
```

O que acontece com cada `.cdr`:

1. **conversão pelo próprio CorelDRAW** da máquina — o motor da Corel exporta o
   PDF, então cor especial, sobreimpressão, sangria e fonte saem como no
   arquivo. A automação se conecta à sessão aberta do operador; ele vê o
   arquivo piscar na tela durante a conversão.
2. daí para a frente é o mesmo caminho do fluxo SOLIDA: prova impressa
   (etiqueta `VOPRIX F4` / `VOPRIX F2`), separação de tintas e chapa.

O nome de saída sai do **produto** (o pedaço antes da medida), com o formato
da chapa e as tintas na frente:

| Original | Sai como |
|---|---|
| `Envelope_Saco_23x31,5_Colegio_Unus.cdr` (510×400, C+M) | `510x400_CM_VOPRIX_Envelope_Saco.pdf` |
| `Cartaz_29,7x42_4_0_Campeao.cdr` (775×635, CMYK) | `775x635_CMYK_VOPRIX_Cartaz.pdf` |
| 2 páginas ou mais | `... 01.pdf`, `... 02.pdf` |

**Arquivo aberto no CorelDRAW do operador não é tocado** — fica para a próxima
passada, quando a pessoa fechar. Se o CorelDRAW não responder, o fluxo VOPRIX
segura a fila e tenta de novo a cada 5 minutos, igual à impressora fora do ar.
O fluxo SOLIDA continua rodando normalmente enquanto isso.

Para desligar: `BASE_ENTRADA_VOPRIX = None` no `config.py`.

## Estrutura

```
finart-ctp/
├─ run_ctp.py             ← ponto de entrada (é este que você roda)
├─ iniciar_ctp.bat        ← atalho de clique duplo para o PC da produção
├─ requirements.txt  requirements-dev.txt  pyproject.toml
├─ .vscode/               ← configuração do VS Code (F5, testes, extensões)
├─ src/finart_ctp/
│  ├─ config.py           ← PASTAS, FORMATOS, HORA_VIRADA  (o que você edita)
│  ├─ monitor.py          ← laço que vigia as pastas do dia (SOLIDA + VOPRIX)
│  ├─ processador.py      ← mede, confere formato e conduz página a página
│  ├─ corel.py            ← converte .cdr da VOPRIX pelo CorelDRAW da máquina
│  ├─ nomes.py            ← como o arquivo de saída se chama (SOLIDA e VOPRIX)
│  ├─ ghostscript.py      ← inkcov (quais tintas) e tiffsep (separação)
│  ├─ pdf_builder.py      ← monta o PDF DeviceN com as tintas usadas
│  └─ utils.py            ← log, pasta do mês/dia, registro, pendências
├─ tests/                 ← pytest
```

## Instalação (uma vez por máquina)

1. **Ghostscript 64-bit** — <https://ghostscript.com>
2. **Python 3.9+** — <https://python.org>, marcando **“Add python.exe to PATH”**
3. No VS Code: `Ctrl+Shift+P` → **Tasks: Run Task** → **Criar ambiente virtual (.venv)**

   Ou no terminal, na pasta do projeto:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
   ```

4. **Crie o `src/finart_ctp/config_local.py`** com os caminhos desta máquina.
   Ele não vai para o controle de versão e sobrescreve o `config.py`:

   ```python
   BASE_ENTRADA = r"V:\PASTA DO CLIENTE"     # dentro dela: MES\DIA
   BASE_ENTRADA_VOPRIX = r"V:\VOPRIX"        # .cdr da VOPRIX; None desliga
   BASE_CTP = r"W:\CTP"                      # saída: MES\DIA\FIA
   PASTA_CONTROLE = r"C:\CTP\_controle"      # log, registro e temporários
   IMPRESSORA = "NOME EXATO NO WINDOWS"      # veja em Impressoras e scanners
   ```

   O fluxo VOPRIX ainda precisa do **CorelDRAW instalado e aberto** na
   máquina. Sem CorelDRAW, deixe `BASE_ENTRADA_VOPRIX = None`.

   Sem esse arquivo o programa sobe com os caminhos de exemplo do
   `config.py` e não vai achar nada.

## Como rodar

- **No VS Code:** `F5` → *CTP: vigiar a pasta do dia*
- **Na produção:** clique duplo em `iniciar_ctp.bat`
- **No terminal:** `python run_ctp.py`

Deixe a janela aberta. `Ctrl+C` encerra. Ao reabrir, ele lê o `_processados.json`
e continua de onde parou, sem refazer nada.

## Refazer um arquivo

Regrave a arte por cima, com o mesmo nome. O registro guarda nome + tamanho +
data de modificação, então o arquivo alterado é reconhecido como novo e refeito
sozinho. Para forçar tudo de novo, apague o `_processados.json`.

## Onde mexer

Quase tudo que muda no dia a dia está em [src/finart_ctp/config.py](src/finart_ctp/config.py):
caminhos, formatos aceitos, tolerância em mm, hora da virada e intervalo de varredura.

## Testes

```powershell
python -m pytest -q
```

## Registro

- `C:\CTP\_controle\_log_ctp.txt` — tudo que aconteceu, com hora
- `C:\CTP\_controle\_processados.json` — o que já foi feito
- `C:\CTP\_controle\_PENDENCIAS.txt` — o que precisa de gente

A pasta do CTP na rede recebe **só as chapas**, nada de arquivo de controle.

Quando algo precisa de atenção humana — tamanho fora do padrão, duas artes
com a mesma OS, PDF ilegível —, o programa para de ser discreto e imprime
na tela:

```
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!  PENDENCIA - PRECISA DE VOCE
!!!  arquivo: 49638 - Cliente - vouchers.pdf
!!!  motivo : ja existe 49638.pdf (outra arte com a mesma OS)
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```
