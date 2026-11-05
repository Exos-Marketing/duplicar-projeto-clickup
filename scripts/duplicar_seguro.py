#!/usr/bin/env python3
"""
duplicar_seguro.py — roda o engine duplicar_projeto.py com duas proteções, SEM alterar o engine.

1. list_tasks levanta erro se uma página da lista falhar. O engine original para em silêncio e
   monta um índice parcial; aí find_by_name não acha o que já existe e o --apply RECRIA (marco ou
   atividade reaproveitada vira duplicata).
2. POST de criação (task, Doc, checklist e item de checklist) não é repetido às cegas em
   429/timeout: espera, recheca pelo nome e só tenta de novo se não achar. O engine original
   repete o POST — se o primeiro tinha dado certo no servidor, nasce duplicata (e Doc não se
   apaga pela API: DELETE dá 405).

Uso (mesmos argumentos do engine; token do ambiente ou do Keychain):
  python3 duplicar_seguro.py discover --config config_X.json --out plano_X.json
  python3 duplicar_seguro.py execute  --plan plano_X.json            # dry-run
  python3 duplicar_seguro.py execute  --plan plano_X.json --apply
"""
import re, sys, time
import comum

dup = comum.engine()
_api_original = dup.api
STATS = {"recheck_evitou_duplicata": 0, "recheck_repetiu_post": 0, "lista_no_limite": 0}
CHK_TASK = {}   # checklist_id -> task_id (p/ rechecar item de checklist)

RX_TASK = re.compile(r"^/api/v2/list/([^/]+)/task$")
RX_DOC = re.compile(r"^/api/v3/workspaces/([^/]+)/docs$")
RX_CHK = re.compile(r"^/api/v2/task/([^/]+)/checklist$")
RX_ITEM = re.compile(r"^/api/v2/checklist/([^/]+)/checklist_item$")


def list_tasks_seguro(list_id):
    out, page = [], 0
    while True:
        c, b = _api_original("GET", f"/api/v2/list/{list_id}/task?archived=false&include_closed=true"
                                    f"&subtasks=false&page={page}")
        if c != 200 or not isinstance(b, dict):
            raise RuntimeError(f"lista {list_id}: página {page} falhou ({c}) — abortado para não montar "
                               f"índice parcial (re-rode; o engine é idempotente)")
        out += b.get("tasks", [])
        if b.get("last_page", True):
            break
        if page > 25:
            STATS["lista_no_limite"] += 1
            print(f"  ! lista {list_id}: limite de 27 páginas do engine atingido (tasks antigas ficam fora do índice)")
            break
        page += 1
    return out


def _nome(x):
    return comum.clean(x)


def _recheca(path, body):
    """-> corpo equivalente ao do POST se o item já existe; None se não existe."""
    nome = _nome((body or {}).get("name"))
    m = RX_TASK.match(path)
    if m:
        for t in list_tasks_seguro(m.group(1)):
            if _nome(t.get("name")) == nome:
                return {"id": t["id"]}
        return None
    m = RX_DOC.match(path)
    if m:
        pid = ((body or {}).get("parent") or {}).get("id")
        c, b = _api_original("GET", f"/api/v3/workspaces/{m.group(1)}/docs?parent_id={pid}&parent_type=1")
        if c != 200 or not isinstance(b, dict):
            raise RuntimeError(f"recheck de Doc falhou ({c}) — abortado para não criar Doc duplicado")
        for d in b.get("docs") or []:
            if _nome(d.get("name")) == nome and not d.get("deleted"):
                return {"id": d["id"]}
        return None
    m = RX_CHK.match(path)
    if m:
        c, t = _api_original("GET", f"/api/v2/task/{m.group(1)}")
        if c != 200:
            raise RuntimeError(f"recheck de checklist falhou ({c})")
        for cl in t.get("checklists") or []:
            if _nome(cl.get("name")) == nome:
                return {"checklist": {"id": cl["id"]}}
        return None
    m = RX_ITEM.match(path)
    if m:
        tid = CHK_TASK.get(m.group(1))
        if not tid:
            return None
        c, t = _api_original("GET", f"/api/v2/task/{tid}")
        if c != 200:
            raise RuntimeError(f"recheck de item de checklist falhou ({c})")
        for cl in t.get("checklists") or []:
            if cl.get("id") == m.group(1) and any(_nome(i.get("name")) == nome for i in cl.get("items") or []):
                return {}
        return None
    return None


def _cria(path, body):
    for k in range(6):
        c, r = comum.api("POST", path, body, create=True)
        if c not in (429, 0):
            return c, r
        time.sleep(10 * (k + 1))
        achado = _recheca(path, body)
        if achado is not None:
            STATS["recheck_evitou_duplicata"] += 1
            print(f"      ~ já existia após 429/timeout (evitou duplicar): {_nome((body or {}).get('name'))[:60]}")
            return 200, achado
        STATS["recheck_repetiu_post"] += 1
    return 0, "retry"


def api_seguro(method, path, body=None, tries=5):
    if method == "POST" and (RX_TASK.match(path) or RX_DOC.match(path) or RX_CHK.match(path) or RX_ITEM.match(path)):
        c, r = _cria(path, body)
        m = RX_CHK.match(path)
        if m and isinstance(r, dict) and (r.get("checklist") or {}).get("id"):
            CHK_TASK[r["checklist"]["id"]] = m.group(1)
        return c, r
    return _api_original(method, path, body, tries)


dup.api = api_seguro
dup.list_tasks = list_tasks_seguro

if __name__ == "__main__":
    dup.main()
    print("\n==== PROTEÇÕES (duplicar_seguro) ====")
    for k, v in STATS.items():
        print(f"  {k}: {v}")
