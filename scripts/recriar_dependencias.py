#!/usr/bin/env python3
"""
recriar_dependencias.py — recria no destino as dependências (waiting_on) que existem na ORIGEM
entre tasks do projeto. O engine não copia dependências porque os ids mudam.

Generaliza clickup_deps_ll_bf.py: o mapeamento origem->destino vem do resolvedor do comum.py
(new_name na lista destino, NFC, duplicata = erro). Só entram arestas com as DUAS pontas no plano
(task descartada e fora do plano não gera aresta). Idempotente: pula aresta que já existe.

Rode DEPOIS das datas do acabamento: dependência criada antes do vencimento faz o ClickUp gravar
start_date sozinho (o sweep do acabamento limpa, mas é melhor não sujar).

Uso:
  python3 recriar_dependencias.py --config config_X.json            # dry-run
  python3 recriar_dependencias.py --config config_X.json --apply
"""
import argparse, sys
import comum
from comum import api, get_task


def main():
    ap = comum.args_comuns(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--esperado", type=int, help="nº de arestas esperado (aborta se diferente)")
    a = ap.parse_args()
    pj = comum.Projeto(a.config, a.plan or comum.plano_padrao(a.config))
    ents, erros = pj.resolver(incluir_card=False)
    if erros:
        print("!! RESOLVEDOR COM ERROS — ABORTADO")
        for x in erros:
            print("   " + x)
        sys.exit(2)
    m = pj.tmap(ents)
    nome = {e["src_id"]: e["name"] for e in ents}
    arestas = set()
    for sid in m:
        for d in get_task(sid).get("dependencies") or []:
            dep, on = d.get("task_id"), d.get("depends_on")
            if dep in m and on in m:
                arestas.add((dep, on))
    print(f"arestas na origem (as duas pontas no plano): {len(arestas)}")
    if a.esperado is not None and len(arestas) != a.esperado:
        sys.exit(f"!! esperado {a.esperado} — ABORTADO")
    feitas = ja = 0
    for dep, on in sorted(arestas, key=lambda x: (nome[x[0]], nome[x[1]])):
        aid, bid = m[dep], m[on]
        have = any(x.get("depends_on") == bid for x in get_task(aid).get("dependencies") or [])
        if have:
            ja += 1
            continue
        print(f"  + {nome[dep][:52]}  ⟵ espera ⟵  {nome[on][:52]}")
        if a.apply:
            c, b = api("POST", f"/api/v2/task/{aid}/dependency", {"depends_on": bid})
            if c not in (200, 204):
                print(f"      ! {c} {str(b)[:120]}")
            else:
                feitas += 1
    print(f"\n  arestas: {len(arestas)} | criadas: {feitas} | já existiam: {ja}"
          f"{'' if a.apply else '  (DRY-RUN — use --apply)'}")


if __name__ == "__main__":
    main()
