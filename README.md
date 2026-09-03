# FINART — Automação CTP

Vigia a pasta do dia do cliente no servidor. A cada PDF novo: mede cada página,
descobre quais tintas ela usa de verdade e gera **um PDF por página, só com essas
tintas**, no dpi certo e com o nome montado a partir da OS. Substitui o passo
manual no Photoshop/InDesign.

**O original nunca é movido nem apagado** — a pasta de entrada é compartilhada.
O controle do que já foi feito fica num `_processados.json` no próprio PC.

## Pastas

| | |
|---|---|
| Entrada | `X:\ENTRADA\<MÊS>\<DIA>` — ex.: `X:\ENTRADA\SETEMBRO\02` |
| Saída | `Y:\CTP\<MÊS>\<DIA>\FIA` — ex.: `Y:\CTP\SETEMBRO\03\FIA` |
| Controle | `C:\CTP\_controle` — log e registro ficam no PC, fora da rede |

A pasta `FIA` fica ao lado das dos outros operadores (uma pasta por operador)
e é criada sozinha todo dia. O nome do mês é encontrado como está escrito no
servidor — `MARÇO`, `Marco`, `Fevereiro` e `FEVEREIRO` são a mesma pasta.

## Passo 1: prova impressa

Antes de gerar qualquer chapa, o **arquivo original do cliente** sai impresso na
a impressora configurada, em **A4 retrato, só na frente**.

A prova é montada aqui: a arte é rasterizada e centralizada numa folha A4 em pé
(arte deitada é girada). Duas razões para não mandar o PDF do cliente direto:

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

## Estrutura

```
finart-ctp/
├─ run_ctp.py             ← ponto de entrada (é este que você roda)
├─ iniciar_ctp.bat        ← atalho de clique duplo para o PC da produção
├─ requirements.txt  requirements-dev.txt  pyproject.toml
├─ .vscode/               ← configuração do VS Code (F5, testes, extensões)
├─ src/finart_ctp/
│  ├─ config.py           ← PASTAS, FORMATOS, HORA_VIRADA  (o que você edita)
│  ├─ monitor.py          ← laço que vigia a pasta do dia + registro
│  ├─ processador.py      ← mede, confere formato e conduz página a página
│  ├─ nomes.py            ← como o arquivo de saída se chama
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
   BASE_CTP = r"W:\CTP"                      # saída: MES\DIA\FIA
   PASTA_CONTROLE = r"C:\CTP\_controle"      # log, registro e temporários
   IMPRESSORA = "NOME EXATO NO WINDOWS"      # veja em Impressoras e scanners
   ```

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
- `Y:\CTP\<MÊS>\<DIA>\FIA\_PENDENCIAS.txt` — o que não deu para processar e por quê
