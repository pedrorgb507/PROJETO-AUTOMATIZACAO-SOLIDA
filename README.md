# PROJETO FECHAMENTO CHAPA

Fechamento de chapas para o CTP da Finart.

Vigia a pasta do dia de **cada cliente** no servidor. A cada arte nova: mede cada
página, descobre quais tintas ela usa de verdade e gera **um PDF por página, só
com essas tintas**, no dpi certo e com o nome que aquele cliente usa. Substitui
o passo manual no Photoshop/InDesign.

São três clientes, e a diferença entre eles está só nas pontas:

| | Chega como | Sai chamando |
|---|---|---|
| **SOLIDA** | PDF pronto | `49576R1` — o número da OS |
| **VOPRIX** | `.cdr`, convertido pelo CorelDRAW | `510x400_CM_VOPRIX_Envelope_Saco` |
| **FIALHO** | PDF pronto, no tamanho da chapa | `510x400_FIALHO_UNICIDADES 01` |

No meio — prova impressa, separação de tintas, uma chapa por página — os três
seguem o mesmo caminho, e as chapas caem na **mesma pasta FIA do dia**.

**O original nunca é movido nem apagado** — a pasta de entrada é compartilhada.
O controle do que já foi feito fica num `_processados.json` no próprio PC.

## Pastas

| | |
|---|---|
| Entrada SOLIDA | `V:\SOLIDA Grafica\<MÊS>\<DIA>` — só `.pdf` |
| Entrada VOPRIX | `V:\VOPRIX\<MÊS>\<DIA>` — só `.cdr` |
| Entrada FIALHO | `V:\Fialho Brindes\<MÊS>\<DIA>` — `.pdf` fecha, `.cdr` só avisa |
| Saída | `W:\CTP\<MÊS>\<DIA>\FIA` — a mesma para os três |
| Controle | `C:\CTP\_controle` — log e registro ficam no PC, fora da rede |

Os caminhos reais desta máquina ficam no `config_local.py`; os do `config.py`
são exemplos. Para desligar um cliente, deixe a base dele em `None`.

A pasta `FIA` fica ao lado das dos outros operadores (uma pasta por operador)
e é criada sozinha todo dia. O nome do mês é encontrado como está escrito no
servidor — `MARÇO`, `Marco`, `Fevereiro` e `FEVEREIRO` são a mesma pasta.

## Passo 0: o `.cdr` da VOPRIX

A VOPRIX entrega em `.cdr`, com a arte já montada no tamanho da chapa. Antes de
qualquer coisa, o **CorelDRAW desta máquina** publica o arquivo em PDF, e é esse
PDF que segue para a prova e para as chapas. O temporário fica no disco local e
é apagado no fim — nada disso passa pela rede.

Quem exporta é o motor da própria Corel, então cor especial, sobreimpressão,
sangria e fonte saem como no arquivo. Conversor de terceiros sai "parecido", e
parecido não serve para gravar chapa.

**A automação usa a sessão do CorelDRAW que estiver aberta — a do operador.**
Daí duas regras que nasceram de erro cometido:

1. nunca mexer na visibilidade da janela;
2. nunca fechar documento que não fomos nós que abrimos.

Por isso, **arquivo aberto no Corel do operador não é convertido**: o programa
avisa uma vez no log e deixa para a próxima passada, quando a pessoa fechar.
Não vira pendência e não entra no registro — nada se perde.

O operador vai ver o arquivo piscar na tela durante a conversão. É o preço
combinado de dividir a máquina.

### O programa exige os ajustes do PDF, não herda

O `PublishToPDF` usa o que estiver marcado na janela de *Publicar em PDF* da
máquina — e o que estava marcado era **compressão nenhuma**. Um `.cdr` de 13 MB
virava um PDF de **1007 MB**, dos quais 1006 MB eram bitmap gravado cru.

Não era defeito da automação: publicando pela janela dá o mesmo. Na mão o
arquivo passa pelo Photoshop depois, e ninguém vê o monstro do meio.

Agora o programa exige dois ajustes, e os dois são **sem perda**:

| | Medido no mesmo arquivo |
|---|---|
| como estava | 1007,5 MB |
| **`BitmapCompression = ZIP` + `CompressText`** | **39,6 MB — 25× menor** |

E o que sai é o mesmo arquivo: cobertura de tinta igual na quinta casa
(`+0.00000` nas quatro) e a página rasterizada com **7.114.344 de 7.114.344
pixels idênticos**, diferença máxima 0 de 255.

**Não reamostramos**, e isso foi decidido com número na mesa. As imagens do
cliente chegam em ~1064 dpi no tamanho final — mais do que a chapa grava (1000
dpi) e mais do que o offset usa (300–400). Mesmo assim:

- ZIP + 800 dpi dá **50,9 MB**, *maior* que sem reamostrar — a interpolação
  inventa valores que comprimem pior;
- ZIP + 600 dpi dá 42,2 MB;
- ZIP + 400 dpi dá 32,5 MB, e o **QR code do panfleto sai borrado**. Traço fino
  dentro do bitmap é o que quebra primeiro.

Reamostrar aqui custa qualidade e não paga nada. Os ajustes ficam em
`PDF_CORELDRAW`, no `config.py`.

Se ainda assim o PDF passar do limite de tamanho, o arquivo vira pendência sem
gerar chapa — foi o caso do `.cdr` de 375 MB que saiu como um PDF de 2,2 GB.

## Passo 1: prova impressa

Antes de gerar qualquer chapa, o **arquivo original do cliente** sai impresso na
a impressora configurada, em **A4 retrato, só na frente**.

A prova é montada aqui: a arte é rasterizada e centralizada numa folha A4 em pé
(arte deitada é girada).

A folha leva no canto superior esquerdo, **fora da arte**, a etiqueta do
formato — o alto da folha ganha uma faixa em branco e a arte desce para
caber embaixo dela:

| Formato da chapa | SOLIDA | VOPRIX | FIALHO |
|---|---|---|---|
| 510 × 400 mm | `SOLIDA F4` | `VOPRIX F4` | `FIALHO F4` |
| 775 × 635 mm | `SOLIDA F2` | `VOPRIX F2` | — |
| 730 × 600 mm | — | — | `FIALHO F2` |

A etiqueta diz também de quem é a chapa: todas saem na mesma bandeja.

Formato não reconhecido sai sem etiqueta. O texto fica em `ROTULOS_PROVA`,
`ROTULOS_PROVA_VOPRIX` e `ROTULOS_PROVA_FIALHO`, no `config.py`.
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

## FIALHO BRINDES: padrão temporário

O Fialho manda de tudo — PDF pronto, PDF fora de medida, arquivo em Corel, arte
que ainda precisa ser montada. Enquanto o programa não dá conta de tudo isso, o
combinado é estreito de propósito:

**Só anda o que chega em PDF já no tamanho final da chapa.** Todo o resto para,
vira pendência na tela e espera gente — nenhum serviço anda pela metade.

| Chapa | DPI | Etiqueta da prova |
|---|---|---|
| 510 × 400 mm | 1000 | `FIALHO F4` |
| 730 × 600 mm | 800 | `FIALHO F2` |

São só essas duas: a 775×635 da Solida não vale aqui, e a 730×600 do Fialho não
vale lá. Cada cliente tem a sua tabela.

O que **para e não anda**:

- arquivo em `.cdr` — montagem ainda é na mão. O programa enxerga o arquivo só
  para avisar; arquivo ignorado em silêncio é serviço que ninguém lembra de fazer;
- página longe de qualquer chapa — o aviso diz o que era esperado.

### Arte quase do tamanho da chapa entra centralizada

A arte do Fialho às vezes vem alguns milímetros fora: o `CAPA Agenda PAULISTA
2027.pdf` mede **520×400** e é chapa **510×400**. Até `ENCAIXE_MAXIMO_MM` (15 mm)
de diferença, ela entra **centralizada** na chapa mais próxima:

- o que **sobra é cortado**, igualmente dos dois lados — 5 mm de cada lado, no
  caso do Paulista;
- o que **falta vira branco**, também dividido igualmente.

É corte, não redução: **nada é redimensionado**, para a arte chegar na chapa do
tamanho em que foi desenhada. Por isso o limite é curto — acima dele ninguém
sabe o que pode ser cortado, e o arquivo vira pendência como antes.

A chapa sai com o tamanho e o nome da **chapa**, não da arte:
`510x400_FIALHO_PAULISTA 01`. E o log avisa toda vez que centralizou:

```
>>> p1: arte 520x400 mm entra centralizada na chapa 510x400
    - sobra cortada dos dois lados
```

O encaixe vale **só para o Fialho**. Cortar arte no escuro não foi combinado com
mais ninguém.

### O nome da chapa é o nome principal do serviço

`forro`, `miolo`, `capa`, `caderno` são tipo de material e não identificam
trabalho nenhum. O que nomeia a chapa é o **nome principal** — quase sempre o
cliente final:

| Arquivo | Chapa |
|---|---|
| `FORRO AGENDA unicidades 2027.pdf` | `510x400_FIALHO_UNICIDADES 01` |
| `MIOLO caderno sicoob montagen formato 48x66.pdf` | `730x600_FIALHO_SICOOB 01` |
| `biocromo novo modelo envelope 15,5x22.pdf` | `510x400_FIALHO_BIOCROMO 01` |

O programa joga fora as palavras de material, as medidas (`48x66`) e os números
soltos; o que sobra é o nome. **Não sobrando nada**, o nome do arquivo inteiro
vira o nome da chapa, em maiúscula, sem acento e sem caractere especial:

```
divisoria colorida  montagem para agenda de dobra.pdf
  -> 510x400_FIALHO_DIVISORIA COLORIDA MONTAGEM PARA AGENDA DE DOBRA 01
```

Melhor um nome comprido do que uma chapa sem nome.

A lista de palavras que não contam está em `PALAVRAS_MATERIAL`, no `config.py`,
e **é para crescer**: quando uma chapa sair com nome errado, quase sempre a
correção é acrescentar a palavra ali.

### A numeração é do dia, não do arquivo

`01`, `02`, `03`... contam por **trabalho e por dia**, não por arquivo. As 11
chapas de UNICIDADES de um dia saem `01` a `11` mesmo vindo de três PDFs
diferentes: antes de gravar, o programa olha a pasta de saída e continua de onde
o dia parou.

## Formatos e dpi — SOLIDA e VOPRIX

| Tamanho da página | DPI  | Sufixo |
|-------------------|------|--------|
| 510 × 400 mm      | 1000 | —      |
| 775 × 635 mm      | 800  | `R1`   |
| qualquer outro    | —    | anotado em `_PENDENCIAS.txt`, sem processar |

O Fialho tem a própria tabela (510×400 e 730×600), na seção dele.

## Nome do arquivo de saída — SOLIDA

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

## Nome do arquivo de saída — VOPRIX

Aqui não há OS. O nome de entrada é `Produto_medida_cores_Cliente.cdr`, e a
chapa se chama pelo **CLIENTE em maiúscula na frente, produto em minúscula
atrás**:

| Original | Sai como |
|---|---|
| `Panfleto_15,0x21,0_4_0_M3RIN.cdr` | `510x400_CMYK_VOPRIX_M3RIN_panfleto.pdf` |
| `Envelope_Saco_23x31,5_Colegio_Unus.cdr` (só C e M) | `510x400_CM_VOPRIX_COLEGIO_UNUS_envelope_saco.pdf` |
| `Pasta_Bopp_Orelha_44x31_Colegio_Unus.cdr` (2 páginas) | `..._COLEGIO_UNUS_pasta_bopp_orelha 01.pdf` e `... 02.pdf` |

**O cliente são os dois últimos nomes do arquivo** — ou só o último, quando só
há um (`M3RIN`). Número solto não conta: nem a especificação de cores (`4_0`)
nem a data no fim (`_31_08`). Palavra de ligação também não, senão
`Campeao_Lubrificantes_e_Filtro` viraria `E_FILTRO`.

O produto é o que vem antes da medida; sem medida no nome, é tudo o que sobra na
frente do cliente. As tintas são as que a arte usa de verdade, não as do nome do
arquivo, e cor especial entra depois das quatro de escala.

**Por que o cliente vem primeiro:** o produto sozinho não identifica trabalho
nenhum. Dois `Panfleto` chegaram no mesmo dia, de clientes diferentes, e as
chapas foram para o CTP como `Panfleto.pdf` e `Panfleto_v2.pdf` — nada no nome
dizia qual era qual. Com o cliente na frente, os 16 arquivos de setembro dão 16
nomes diferentes.

### Quando ainda assim dois baterem: MODELO

Mesmo cliente, mesmo produto, mesmo dia, artes diferentes. Aí as duas passam a
se chamar MODELO — e a que **já estava gravada é renomeada** para `MODELO 1`:

```
510x400_CMYK_VOPRIX_COLEGIO_UNUS_pasta MODELO 1.pdf   ← era ..._pasta.pdf
510x400_CMYK_VOPRIX_COLEGIO_UNUS_pasta MODELO 2.pdf   ← a que acabou de chegar
```

Só assim as duas ficam simétricas: uma com nome limpo e outra numerada
esconderia que são duas artes diferentes. O registro é acertado junto, para não
apontar para uma chapa que mudou de nome, e o caso vai para o `_PENDENCIAS.txt`.
A terceira sai `MODELO 3`, e ninguém mexe mais em quem já está numerado.

## Cores da VOPRIX: quadricromia fecha sozinha, o resto espera

**Se a página vier em CMYK, o caminho é o de sempre e a chapa sai sozinha.**
Qualquer outra coisa — 1, 2 ou 3 cores, ou escala de cinza — **para antes de
gerar a chapa**: a prova sai do mesmo jeito, o PDF convertido fica guardado na
`PASTA_PENDENCIAS`, e o aviso aparece na tela com a cobertura de cada tinta e o
nome que a chapa teria:

```
!!!  motivo : pagina 1: NAO veio em quadricromia - GRAY
!!!            (C 0.0608 M 0.0608 Y 0.0608 K 0.0544).
!!!            Sairia como 510x400_GRAY_VOPRIX_Blocos. Nao fechei: confira antes
```

Em quadricromia o caminho é sempre o mesmo; em uma ou duas cores a decisão muda
de trabalho para trabalho, e aí quem manda fechar é gente. Para desligar a
trava: `AVISAR_QUANDO_NAO_FOR_CMYK = False` no `config.py`. Ela vale só para a
VOPRIX — a SOLIDA fecha tudo como sempre fez.

### Arte de uma cor sai em escala de cinza

Arte de uma cor **não chega como preto puro**: a Corel exporta o preto composto,
com C, M, Y e K juntos. Gerar isso como quadricromia daria quatro chapas onde o
trabalho pede uma; e pegar só o canal K daria uma chapa lavada, porque o preto
está espalhado pelos quatro canais. O certo é rasterizar a página em cinza —
`/DeviceGray`, uma chapa só — e escrever `GRAY` no nome:

```
510x400_GRAY_VOPRIX_Blocos_Rio_Quente
```

Duas perguntas decidem, e as duas precisam passar:

1. **a cobertura das três cores bate?** Num arquivo real: `C 0.06081`,
   `M 0.06079`, `Y 0.06080` — iguais até a quarta casa. Arte colorida nunca faz
   isso. Preto puro (CMY zerados) também conta como uma cor;
2. **existe cor gritante em algum pixel?** Rasteriza em 72 dpi e confere. Pega o
   caso que a conta acima não pega: vermelho de um lado e ciano do outro pode
   fechar os totais e passar por neutro sem ser.

A folga da segunda pergunta é larga (96 de 255) de propósito: arte cinza de
verdade não tem canal igualzinho pixel a pixel — a borda do texto sai com ruído
de anti-aliasing, medido em até 39 de diferença em 6% dos pixels. Na dúvida, o
programa erra para o lado da quadricromia, que é o que sempre foi feito.

## Estrutura

```
finart-ctp/
├─ run_ctp.py             ← ponto de entrada (é este que você roda)
├─ iniciar_ctp.bat        ← atalho de clique duplo para o PC da produção
├─ requirements.txt  requirements-dev.txt  pyproject.toml
├─ .vscode/               ← configuração do VS Code (F5, testes, extensões)
├─ src/finart_ctp/
│  ├─ config.py           ← PASTAS, FORMATOS, HORA_VIRADA  (o que você edita)
│  ├─ monitor.py          ← vigia a pasta do dia de cada cliente + registro
│  ├─ processador.py      ← mede, confere formato e conduz página a página
│  ├─ corel.py            ← .cdr → PDF pelo CorelDRAW da máquina (VOPRIX)
│  ├─ prova.py            ← monta e imprime a folha A4 da prova
│  ├─ nomes.py            ← como o arquivo de saída se chama, por cliente
│  ├─ ghostscript.py      ← inkcov (quais tintas) e tiffsep (separação)
│  ├─ pdf_builder.py      ← monta o PDF DeviceN com as tintas usadas
│  └─ utils.py            ← log, pasta do mês/dia, registro, pendências
├─ tests/                 ← pytest
```

## Instalação (uma vez por máquina)

1. **Ghostscript 64-bit** — <https://ghostscript.com>.
   **CorelDRAW** instalado é o que converte os `.cdr` (só para a VOPRIX).
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
   BASE_ENTRADA = r"V:\SOLIDA Grafica"       # dentro dela: MES\DIA
   BASE_ENTRADA_VOPRIX = r"V:\VOPRIX"        # idem; None para nao vigiar
   BASE_CTP = r"W:\CTP"                      # saída: MES\DIA\FIA
   PASTA_CONTROLE = r"C:\CTP\_controle"      # log, registro e temporários
   IMPRESSORA = "NOME EXATO NO WINDOWS"      # veja em Impressoras e scanners
   ```

   O `pywin32`, que fala com o CorelDRAW, já vem no `requirements.txt`. Sem ele
   o programa avisa e segue só com a SOLIDA.

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
- `C:\CTP\_pendencias\` — os arquivos que precisam da sua mão

Quando um `.cdr` da VOPRIX não dá para processar — grande demais, ilegível —, o
**PDF que a Corel já converteu não é jogado fora**: ele fica na
`PASTA_PENDENCIAS`, com o nome do arquivo original. Você abre esse PDF no
Photoshop/InDesign e continua do ponto onde o programa parou, sem esperar a
conversão de novo, que é a parte demorada. O caminho vai anotado no
`_PENDENCIAS.txt`.

A pasta fica no disco local, nunca na rede: são arquivos de centenas de MB.
Limpe de tempos em tempos.

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
