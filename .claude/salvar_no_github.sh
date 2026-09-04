#!/usr/bin/env bash
# ---------------------------------------------------------------------
# Sobe para o GitHub o que ja esta commitado.
#
# Roda sozinho, pelo hook Stop do Claude Code, toda vez que ele termina
# de responder. Assim ninguem precisa pedir "salva no github".
#
# O que ele NAO faz: commitar. Commit continua sendo escrito a mao, com
# mensagem de verdade - o historico deste projeto conta como cada regra
# nasceu, e isso nao se joga fora por conveniencia.
#
# Nunca derruba a sessao: qualquer erro vira aviso e o hook sai com 0.
# ---------------------------------------------------------------------

cd "$(dirname "$0")/.." 2>/dev/null || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

aviso() {
    # o Claude Code le esta linha e mostra a mensagem para o operador
    printf '{"systemMessage":"%s","suppressOutput":true}\n' "$1"
    exit 0
}

frente=$(git rev-list --count '@{u}..HEAD' 2>/dev/null) || frente=0
sujos=$(git status --porcelain 2>/dev/null | grep -c .)

if [ "${frente:-0}" -eq 0 ]; then
    # nada para subir. So avisa se houver trabalho parado sem commit
    [ "${sujos:-0}" -gt 0 ] && aviso "GitHub em dia. $sujos arquivo(s) alterado(s) ainda sem commit."
    exit 0
fi

if erro=$(git push --porcelain origin HEAD 2>&1); then
    msg="GitHub: $frente commit(s) enviados"
    [ "${sujos:-0}" -gt 0 ] && msg="$msg. $sujos arquivo(s) ainda sem commit"
    aviso "$msg"
fi

# push recusado - quase sempre porque o remoto andou. Nao resolvo sozinho:
# juntar historico e decisao de gente.
if printf '%s' "$erro" | grep -qi "fetch first\|non-fast-forward\|rejected"; then
    aviso "GitHub RECUSOU o push: o remoto tem commit que nao esta aqui. Rode git pull --rebase e peca para eu subir de novo."
fi
aviso "GitHub: nao consegui subir $frente commit(s). Sem rede ou sem credencial?"
