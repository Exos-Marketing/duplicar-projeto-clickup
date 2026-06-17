#!/usr/bin/env python3
"""
Corrige o titulo das paginas dos Docs do projeto Daniela Moleiro [DM][LB][POS][AGO][26].

Na duplicacao, cada atividade/marco recebeu um Doc nativo, mas a PRIMEIRA pagina ficou
sem nome (name=None) -> o ClickUp mostra "Sem titulo" ao abrir. Este script define o nome
da pagina raiz de cada doc anexado = nome ATUAL da task (que ja esta com [AGO]), resolvendo
tanto o "Sem titulo" quanto eventual residuo de [JUL] nas paginas.

(O nome do DOC em si - breadcrumb/hub - e imutavel via API: PUT/PATCH/.../docs/{id} -> 405.
 O titulo visivel ao ABRIR o doc e o nome da PAGINA, que e editavel.)

API-first (REST direta), token no Keychain (servico clickup-exos-api).
Dry-run por padrao; use --apply para escrever de verdade.

Uso:
  CLICKUP_TOKEN=$(security find-generic-password -s clickup-exos-api -w) \
    python3 clickup_fix_doc_titles.py            # dry-run
  python3 clickup_fix_doc_titles.py --apply      # executa
"""
import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.error

WS = "9013012202"
API = "https://api.clickup.com/api/v2"
V3 = "https://api.clickup.com/api/v3/workspaces/" + WS  # Docs (rate limit baixo)

# Sufixos do projeto (NEW = atual; OLD = fallback de seguranca, caso algum nao tenha sido renomeado)
NEW = "[AGO][26]"
OLD = "[JUL][26]"

# Listas a varrer (card de painel, fases de lancamento, processos de marketing) -- mesmas do rename
LISTS = [
    "901302496038",  # Painel Projeto Lancamentos (card do projeto)
    "901302376636",  # Concepcao
    "901302376637",  # Setup
    "901302378944",  # Captacao
    "901302378939",  # Aquecimento
    "901302376639",  # Evento
    "901302376640",  # Lancamento
    "901302376641",  # Pos Venda
    "901310974062",  # Downsell
    "901301657744",  # Marketing: Processo de Copywriting
    "901301657750",  # Marketing: Processo de Design & Criacao
    "901301657745",  # Marketing: Agendamentos, Publicacoes & Disparos
    "901301657755",  # Marketing: Gestao de WhatsApps
    "901301657746",  # Marketing: Landing Page
]


def get_token():
    tok = os.environ.get("CLICKUP_TOKEN")
    if tok:
        return tok.strip()
    out = subprocess.run(
        ["security", "find-generic-password", "-s", "clickup-exos-api", "-w"],
        capture_output=True, text=True,
    )
    if out.returncode != 0 or not out.stdout.strip():
        sys.exit("Nao consegui obter o token (Keychain clickup-exos-api).")
    return out.stdout.strip()


TOKEN = get_token()


def req(method, path, body=None, retries=6):
    url = path if path.startswith("http") else API + path
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(retries):
        r = urllib.request.Request(url, data=data, method=method)
        r.add_header("Authorization", TOKEN)
        r.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(r) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 ** attempt
                sys.stderr.write(f"  429, aguardando {wait}s...\n")
                time.sleep(wait)
                continue
            sys.stderr.write(f"  HTTP {e.code} em {method} {url}: {e.read().decode()[:300]}\n")
            raise
    raise RuntimeError(f"Falha apos {retries} tentativas: {method} {url}")


def discover():
    """Varre as listas e retorna tasks do projeto (sufixo NEW ou OLD) sem duplicatas."""
    found = {}
    for lid in LISTS:
        page = 0
        while True:
            data = req("GET", f"/list/{lid}/task?include_closed=true&subtasks=true&page={page}")
            tasks = data.get("tasks", [])
            for t in tasks:
                name = t.get("name") or ""
                if NEW in name or OLD in name:
                    found[t["id"]] = t
            if data.get("last_page") or len(tasks) < 100 or page >= 20:
                break
            page += 1
    return found


def task_attached_docs(tid):
    """Docs v3 anexados a uma task (parent_type=1). Endpoint tem rate limit baixo."""
    try:
        data = req("GET", f"{V3}/docs?parent_id={tid}&parent_type=1")
    except Exception:
        data = {}
    time.sleep(1.5)
    return data.get("docs", []) if isinstance(data, dict) else []


def doc_pages_all(doc_id):
    """Lista (flat, em ordem) das paginas de um doc v3, INCLUINDO paginas sem nome (name=None).

    Diferente do doc_pages() do script de rename, NAO filtra name is None -- justamente as
    paginas 'Sem titulo' que precisamos corrigir."""
    try:
        data = req("GET", f"{V3}/docs/{doc_id}/pages?max_page_depth=-1")
    except Exception:
        data = []
    time.sleep(1.5)
    out = []

    def walk(node):
        if isinstance(node, dict):
            # uma pagina de doc tem 'id' + 'doc_id' (ou 'parent_page_id'); usamos a presenca de
            # 'id' junto com chaves tipicas de pagina para nao capturar objetos aninhados aleatorios
            if node.get("id") and ("doc_id" in node or "parent_page_id" in node or "pages" in node or "name" in node):
                out.append({"id": node["id"], "name": node.get("name")})
            for k, v in node.items():
                if k == "pages":
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(data)
    # dedup preservando ordem
    seen, uniq = set(), []
    for p in out:
        if p["id"] not in seen:
            seen.add(p["id"])
            uniq.append(p)
    return uniq


def main():
    apply = "--apply" in sys.argv
    mode = "APPLY" if apply else "DRY-RUN"
    print(f"=== clickup_fix_doc_titles [{mode}] ===\n")

    found = discover()
    print(f"Tasks do projeto encontradas (NEW/OLD): {len(found)}\n")

    print("Varrendo docs anexados as tasks (parent_type=1)... pode demorar (rate limit dos Docs).")
    changes = []   # (doc_id, page_id, old_name, new_name, task_name)
    ja_nomeadas = 0
    # REGRA SEGURA: so renomeia paginas SEM nome (name None/"") -> as genuinas "Sem titulo".
    # Paginas que ja tem nome descritivo (inclusive editadas manualmente pelo gestor) sao
    # PRESERVADAS, nunca sobrescritas pelo nome da task.
    for tid, t in found.items():
        task_name = t.get("name") or ""
        for d in task_attached_docs(tid):
            for p in doc_pages_all(d["id"]):
                nm = p.get("name")
                if nm in (None, ""):
                    changes.append((d["id"], p["id"], nm, task_name, task_name))
                else:
                    ja_nomeadas += 1

    print(f"\n  - paginas SEM nome a corrigir: {len(changes)}")
    print(f"  - paginas ja nomeadas (PRESERVADAS): {ja_nomeadas}\n")

    print("--- PREVIEW ---")
    for doc_id, page_id, old_n, new_n, _ in changes:
        print(f"  doc {doc_id} / page {page_id}: {repr(old_n)} -> {new_n}")

    if not apply:
        print(f"\nDry-run. Rode com --apply para executar.")
        return

    print("\n--- Renomeando paginas dos docs ---")
    ok = 0
    for doc_id, page_id, old_n, new_n, _ in changes:
        req("PUT", f"{V3}/docs/{doc_id}/pages/{page_id}", {"name": new_n})
        time.sleep(1.5)
        ok += 1
        print(f"  OK doc {doc_id}: {new_n}")

    print(f"\n=== CONCLUIDO: {ok} paginas renomeadas ===")


if __name__ == "__main__":
    main()
