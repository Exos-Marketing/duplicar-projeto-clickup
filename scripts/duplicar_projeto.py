#!/usr/bin/env python3
"""
Engine de duplicacao de projetos ClickUp (Exos) - API-first, flexivel.
Fluxo em 2 fases:
  discover : le a origem dinamicamente e gera um plano.json (marcos, atividades, docs, mapa de fases)
  execute  : aplica o plano via API (dry-run por padrao; --apply para escrever)

Uso:
  CLICKUP_TOKEN=$(security find-generic-password -s clickup-exos-api -w) \
    python3 duplicar_projeto.py discover --config config_km_apb.json --out plano.json
  python3 duplicar_projeto.py execute --plan plano.json            # dry-run
  python3 duplicar_projeto.py execute --plan plano.json --apply    # escreve de verdade
"""
import os, sys, json, time, re, argparse, urllib.request, urllib.error

TOKEN = os.environ.get("CLICKUP_TOKEN", "")
WS = "9013012202"     # workspace padrao (fallback p/ configs antigos same-workspace)
SRC_WS = WS           # workspace de ORIGEM (leitura de Docs) - setado em discover/execute
DST_WS = WS           # workspace de DESTINO (criacao de Docs) - setado em discover/execute

def api(method, path, body=None, tries=5):
    data = json.dumps(body).encode() if body is not None else None
    for a in range(tries):
        req = urllib.request.Request("https://api.clickup.com" + path, data=data, method=method)
        req.add_header("Authorization", TOKEN); req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                t = r.read().decode(); return r.status, (json.loads(t) if t.strip() else {})
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(3*(a+1)); continue
            return e.code, _safe(e.read().decode())
        except Exception as ex:
            time.sleep(2); continue
    return 0, "retry"

def _safe(s):
    try: return json.loads(s)
    except Exception: return s

# ---------- transforms ----------
def swap_suffix(name, src_suffix, dst_suffix):
    return name.replace(src_suffix, dst_suffix) if name else name

def swap_expert(text, mapping):
    if not text: return text
    for a, b in mapping.items(): text = text.replace(a, b)
    return text

def apply_name_swaps(text, swaps):
    """Aplica uma lista de pares [de,para] ao texto, em ordem. Usado p/ normalizar nomes
    (marco/atividade/doc) e descricoes quando a origem tem sufixos inconsistentes ou prefixo
    de cliente (ex.: '[ET][RS][POS][FEV][26]' e '[ET][RS][EP][FEV][26]' -> '[KM][PEP][APB][26]')."""
    if not text or not swaps: return text
    for pair in swaps:
        text = text.replace(pair[0], pair[1])
    return text

def norm_name(name, ssuf, dsuf, swaps):
    if swaps: return apply_name_swaps(name, swaps)
    return swap_suffix(name, ssuf, dsuf)

def norm_desc(text, swaps, exp):
    return swap_expert(apply_name_swaps(text or "", swaps), exp)

# ---------- normalizacao de tipo de task (custom_item_id) ----------
# tipos de task resolvidos por NOME (cache por workspace) — robusto e seguro cross-workspace
_type_cache = {}
def type_name_to_id(ws, name):
    ws = str(ws)
    if ws not in _type_cache:
        c, b = api("GET", f"/api/v2/team/{ws}/custom_item")
        m = {}
        if c == 200 and isinstance(b, dict):
            for it in b.get("custom_items", []) or []:
                if it.get("name"): m[it["name"].strip().lower()] = it["id"]
        _type_cache[ws] = m
    return _type_cache[ws].get((name or "").strip().lower())

# regra-padrao Exos: 1a que casa vence (Copy tem prioridade sobre Criativo p/ "Copy Criativos …")
DEFAULT_TYPE_RULES = [
    {"prefix": "Copy",       "type": "Copy"},
    {"contains": "Criativo", "type": "Criativo"},   # cobre "Criativos" e "Criativo"
]
def type_for_name(name, rules):
    nl = (name or "").strip().lower()
    for r in rules:
        if r.get("prefix")   and nl.startswith(r["prefix"].lower()):   return r["type"]
        if r.get("contains") and r["contains"].lower() in nl:          return r["type"]
    return None

# ---------- discovery ----------
def list_tasks(list_id):
    out, page = [], 0
    while True:
        c, b = api("GET", f"/api/v2/list/{list_id}/task?archived=false&include_closed=true&subtasks=false&page={page}")
        if c != 200 or not isinstance(b, dict): break
        out += b.get("tasks", [])
        if b.get("last_page", True) or page > 25: break
        page += 1
    return out

def task_docs(task_id):
    """Lista TODOS os docs da task na ORIGEM (cada um vira um link de referencia).
    Retorna [{"id","name","url"}]. Uma task de copy costuma ter varios docs (ex.: Slides,
    Script, Atendimento) — replicar todos, nao so o primeiro."""
    c, b = api("GET", f"/api/v3/workspaces/{SRC_WS}/docs?parent_id={task_id}&parent_type=1")
    out = []
    if c == 200 and isinstance(b, dict) and b.get("docs"):
        for d in b["docs"]:
            cp, pg = api("GET", f"/api/v3/workspaces/{SRC_WS}/docs/{d['id']}/pages")
            pid = pg[0]["id"] if (cp == 200 and isinstance(pg, list) and pg) else d["id"]
            out.append({"id": d["id"], "name": d.get("name"),
                        "url": f"https://app.clickup.com/{SRC_WS}/docs/{d['id']}/{pid}"})
    return out

def task_doc_url(task_id):
    # compat: retorna so o 1o doc (use task_docs p/ todos)
    ds = task_docs(task_id)
    return (ds[0]["url"], ds[0]["name"]) if ds else (None, None)

def doc_ref_name(src_name, ssuf, dsuf, exp, swaps=None):
    """Nome do Doc novo = nome do Doc de ORIGEM com sufixo trocado p/ o destino + expert_swap.
    Tolera sufixos baguncados/divergentes (ex.: '[LB][POS][JAN][26]', '[LS][LAS][OUT][25]').
    Se 'swaps' (name_swaps) vier, ele tem prioridade (mapeia variantes/prefixo de cliente)."""
    n = src_name or ""
    if swaps:
        n = apply_name_swaps(n, swaps)
    elif ssuf and ssuf in n:
        n = n.replace(ssuf, dsuf)
    elif dsuf:
        base = re.split(r"\s*\[", n)[0].rstrip()   # corta o 1o grupo de colchetes em diante
        n = (base + " " + dsuf) if base else dsuf
    return swap_expert(n, exp).strip()

def checklists_of(task):
    out = []
    for cl in task.get("checklists", []) or []:
        items = [it["name"] for it in cl.get("items", []) if (it.get("name") or "").strip()]
        if items: out.append({"name": cl.get("name") or "Checklist", "items": items})
    return out

def resolve_rel_field(task, panel_id, fallback=None):
    """Acha o custom field list_relationship do marco que aponta pro painel (subcategory_id)."""
    for f in task.get("custom_fields", []) or []:
        if f.get("type") == "list_relationship":
            sub = (f.get("type_config") or {}).get("subcategory_id")
            if str(sub) == str(panel_id):
                return f["id"]
    return fallback

def discover(cfg):
    global SRC_WS, DST_WS
    src = cfg["source"]; tgt = cfg["target"]
    SRC_WS = str(src.get("workspace") or cfg.get("workspace") or WS)
    DST_WS = str(tgt.get("workspace") or cfg.get("workspace") or WS)
    amap = cfg.get("activity_map", {})   # src_list_id -> dst_list_id (cross-workspace)
    ssuf, dsuf = src["suffix"], tgt["suffix"]
    skip = set(s.lower() for s in src.get("skip_status", []))
    exp = cfg.get("expert_swap", {})
    swaps = cfg.get("name_swaps")
    dcfg = cfg.get("docs", {})
    docs_on = dcfg.get("enabled"); docs_on_marcos = dcfg.get("on_marcos")
    panel = tgt.get("panel_id") or "901302496038"
    plan = {"config": cfg, "marcos": []}
    for phase, list_id in src["phase_lists"].items():
        pm = cfg["phase_map"].get(phase)
        if not pm:
            print(f"  ! fase '{phase}' sem mapeamento, pulando"); continue
        for t in list_tasks(list_id):
            if ssuf not in t.get("name", ""): continue
            if t.get("custom_item_id") != 1: continue  # so marcos (milestone)
            if (t.get("status", {}).get("status", "") or "").lower() in skip: continue
            c, m = api("GET", f"/api/v2/task/{t['id']}")
            if c != 200: continue
            # rel field: auto-resolve do proprio marco (correto p/ mapa identidade); fallback config
            rel = resolve_rel_field(m, panel, pm.get("rel"))
            # docs no proprio marco (modelo flat): so quando nao ha atividades linkadas
            m_docs = []
            has_acts = bool(m.get("linked_tasks"))
            if docs_on and docs_on_marcos and not has_acts:
                m_docs = task_docs(m["id"])   # TODOS os docs, nao so o 1o
            marco = {
                "phase": phase, "dst_list": pm["dst"], "rel_field": rel,
                "src_id": m["id"], "src_name": m["name"], "new_name": norm_name(m["name"], ssuf, dsuf, swaps),
                "description": norm_desc(m.get("description"), swaps, exp),
                "checklists": checklists_of(m), "activities": [],
                "ref_docs": m_docs,
                "ref_doc_url": (m_docs[0]["url"] if m_docs else None),
                "ref_doc_name": (m_docs[0]["name"] if m_docs else None)
            }
            for ln in m.get("linked_tasks", []) or []:
                aid = ln.get("link_id") or ln.get("task_id")
                if not aid or aid == m["id"]: aid = ln.get("task_id")
                if not aid or aid == m["id"]: continue
                ca, act = api("GET", f"/api/v2/task/{aid}")
                if ca != 200: continue
                if (act.get("status", {}).get("status", "") or "").lower() in skip: continue
                a_docs = task_docs(aid) if cfg.get("docs", {}).get("enabled") else []
                _alist = act.get("list", {}).get("id")
                marco["activities"].append({
                    "src_id": act["id"], "src_name": act["name"],
                    "new_name": norm_name(act["name"], ssuf, dsuf, swaps),
                    "src_list": _alist,
                    "src_list_name": act.get("list", {}).get("name"),
                    "dst_list": amap.get(_alist, _alist),
                    "task_type": act.get("custom_item_id"),
                    "description": norm_desc(act.get("description"), swaps, exp),
                    "checklists": checklists_of(act),
                    "ref_docs": a_docs,
                    "ref_doc_url": (a_docs[0]["url"] if a_docs else None),
                    "ref_doc_name": (a_docs[0]["name"] if a_docs else None)
                })
            plan["marcos"].append(marco)
            ndocs = len(marco.get("ref_docs") or []) + sum(len(a.get("ref_docs") or []) for a in marco["activities"])
            doc_flag = f" +{ndocs}doc" if ndocs else ""
            print(f"  + [{phase}] {marco['new_name']}  ({len(marco['activities'])} ativ, {len(marco['checklists'])} checklist{doc_flag})")
    return plan

def _ndocs(o):
    if o.get("ref_docs") is not None: return len(o["ref_docs"])
    return 1 if o.get("ref_doc_url") else 0

def print_summary(plan):
    M = plan["marcos"]; A = sum(len(m["activities"]) for m in M)
    docs = sum(_ndocs(a) for m in M for a in m["activities"]) + sum(_ndocs(m) for m in M)
    cls = sum(len(m["checklists"]) for m in M) + sum(len(a["checklists"]) for m in M for a in m["activities"])
    print(f"\n==== PLANO ====\n  marcos: {len(M)} | atividades: {A} | docs de referencia achados: {docs} | checklists: {cls}")
    by = {}
    for m in M: by.setdefault(m["phase"], 0); by[m["phase"]] += 1
    print("  por fase:", json.dumps(by, ensure_ascii=False))

# ---------- execution ----------
_list_cache = {}
def find_by_name(list_id, name):
    if list_id not in _list_cache:
        _list_cache[list_id] = list_tasks(list_id)
    nm = (name or "").strip()
    for t in _list_cache[list_id]:
        if (t.get("name") or "").strip() == nm:
            return t["id"]
    return None

def set_fields(tid, fields, current=None):
    for f in fields:
        if f["type"] == "drop":
            val = f["value"]
        else:
            val = {"add": [f["value"]]}
            # ao normalizar tarefa existente: remover usuario antigo diferente do novo
            if current and current.get(f["id"]):
                rem = [u for u in current[f["id"]] if str(u) != str(f["value"])]
                if rem: val["rem"] = rem
        c, b = api("POST", f"/api/v2/task/{tid}/field/{f['id']}", {"value": val})
        if c != 200 and "does not exist" not in str(b).lower():
            print(f"      ! campo {f.get('name')} -> {c}")

def current_user_fields(tid):
    """Le valores atuais dos custom fields de usuario (p/ substituir antigo->novo)."""
    c, t = api("GET", f"/api/v2/task/{tid}")
    out = {}
    if c == 200 and isinstance(t, dict):
        for f in t.get("custom_fields", []) or []:
            if f.get("type") == "users" and f.get("value"):
                out[f["id"]] = [u.get("id") for u in f["value"] if isinstance(u, dict)]
    return out

def ensure_checklists(tid, checklists):
    for cl in checklists:
        c, r = api("POST", f"/api/v2/task/{tid}/checklist", {"name": cl["name"]})
        cid = (r or {}).get("checklist", {}).get("id") if isinstance(r, dict) else None
        if not cid: continue
        for it in cl["items"]:
            api("POST", f"/api/v2/checklist/{cid}/checklist_item", {"name": it})

def has_doc(tid):
    # checa/cria docs no DESTINO
    c, b = api("GET", f"/api/v3/workspaces/{DST_WS}/docs?parent_id={tid}&parent_type=1")
    return bool(c == 200 and isinstance(b, dict) and b.get("docs"))

def has_doc_named(tid, name):
    # idempotencia por NOME do doc (permite multiplos docs distintos por task)
    c, b = api("GET", f"/api/v3/workspaces/{DST_WS}/docs?parent_id={tid}&parent_type=1")
    if c == 200 and isinstance(b, dict):
        nm = (name or "").strip()
        for d in (b.get("docs") or []):
            if (d.get("name") or "").strip() == nm: return True
    return False

def make_docs(tid, obj, ssuf, dsuf, exp, label, apply, st, who, swaps=None):
    """Replica TODOS os docs da origem (obj.ref_docs) na task destino, cada um nomeado pelo
    doc de origem (sufixo trocado) e com link de referencia. Idempotente por nome.
    Compat: se o plano so tiver ref_doc_url (formato antigo), cria 1 doc com o nome da task."""
    refs = obj.get("ref_docs")
    pairs = []
    if refs:
        for rd in refs:
            if rd.get("url"):
                pairs.append((doc_ref_name(rd.get("name") or "", ssuf, dsuf, exp, swaps), rd["url"]))
    elif obj.get("ref_doc_url"):
        nm = obj.get("new_name") or doc_ref_name(obj.get("ref_doc_name") or "", ssuf, dsuf, exp)
        pairs.append((nm, obj["ref_doc_url"]))
    for dname, url in pairs:
        if tid and has_doc_named(tid, dname):
            st["doc_skip"] += 1
        else:
            print(f"      doc -> {who}  ::  {dname[:48]}")
            if apply and tid:
                if create_doc(tid, dname, url, label): st["doc_new"] += 1
            else:
                st["doc_new"] += 1

def create_doc(tid, name, ref_url, label):
    c, doc = api("POST", f"/api/v3/workspaces/{DST_WS}/docs",
                 {"name": name, "parent": {"id": tid, "type": 1}, "visibility": "PUBLIC", "create_page": True})
    if c not in (200, 201) or not isinstance(doc, dict): return False
    did = doc["id"]
    cp, pg = api("GET", f"/api/v3/workspaces/{DST_WS}/docs/{did}/pages")
    pid = pg[0]["id"] if (cp == 200 and isinstance(pg, list) and pg) else None
    content = f"**{label}:** [{ref_url}]({ref_url})" if ref_url else "_(documento de trabalho)_"
    if pid:
        api("PUT", f"/api/v3/workspaces/{DST_WS}/docs/{did}/pages/{pid}",
            {"name": name, "content": content, "content_format": "text/md", "content_edit_mode": "replace"})
    return True

ATIV_SENTINEL = "**Atividades**"  # linha-marca da secao auto (distinta de "Atividades:" do briefing)

def append_atividades(tid, acts, apply):
    """Acrescenta/atualiza na descricao do marco uma secao 'Atividades' com os links
    (nome com hyperlink) das tasks relacionadas, uma por linha. Idempotente: se a
    linha-marca ja existir, corta dali pra baixo e regrava. Preserva o briefing acima.
    acts: lista de (task_id_destino, nome_destino)."""
    acts = [(aid, nm) for aid, nm in acts if aid]
    if not acts:
        return
    section = ATIV_SENTINEL + "\n" + "\n".join(
        f"[{nm}](https://app.clickup.com/t/{aid})" for aid, nm in acts)
    if not apply:
        return
    c, t = api("GET", f"/api/v2/task/{tid}?include_markdown_description=true")
    cur = (t.get("markdown_description", "") if isinstance(t, dict) else "") or ""
    base = cur.split(ATIV_SENTINEL)[0].rstrip() if ATIV_SENTINEL in cur else cur.rstrip()
    new_desc = (base + "\n\n" + section).lstrip("\n")
    api("PUT", f"/api/v2/task/{tid}", {"markdown_content": new_desc})

def execute(plan, apply, docs_only=False):
    global SRC_WS, DST_WS
    cfg = plan["config"]; tgt = cfg["target"]
    _src = cfg.get("source", {})
    SRC_WS = str(_src.get("workspace") or cfg.get("workspace") or WS)
    DST_WS = str(tgt.get("workspace") or cfg.get("workspace") or WS)
    card, tag, prio = tgt["card_id"], tgt.get("tag"), tgt.get("priority")
    fields = cfg["fields"]; dcfg = cfg.get("docs", {})
    ttmap = cfg.get("task_type_map")   # cross-workspace: traduz custom_item_id de atividade (src->dst); dropa se nao mapeado
    type_rules = cfg.get("task_type_rules", DEFAULT_TYPE_RULES)   # normaliza tipo por nome (Copy/Criativo); [] desliga
    docs_on = dcfg.get("enabled"); doclabel = dcfg.get("reference_label", "Documento de referência")
    ssuf = (cfg.get("source") or {}).get("suffix", ""); dsuf = tgt.get("suffix", ""); exp = cfg.get("expert_swap", {})
    swaps = cfg.get("name_swaps")
    upd = cfg.get("update_existing")
    st = {"marco_new": 0, "marco_skip": 0, "marco_upd": 0, "ativ_new": 0, "ativ_skip": 0, "doc_new": 0, "doc_skip": 0}
    print(f"== EXECUTE [{'APLICANDO' if apply else 'DRY-RUN'}] ==")
    for m in plan["marcos"]:
        mid = find_by_name(m["dst_list"], m["new_name"])
        if mid:
            st["marco_skip"] += 1
            if upd and not docs_only:
                print(f"  ~ normalizar [{m['phase']}] {m['new_name']}")
                if apply:
                    cur = current_user_fields(mid)
                    set_fields(mid, fields, cur)
                    if m.get("rel_field"):
                        api("POST", f"/api/v2/task/{mid}/field/{m['rel_field']}", {"value": {"add": [card]}})
                    if prio: api("PUT", f"/api/v2/task/{mid}", {"priority": prio})
                st["marco_upd"] += 1
        else:
            if not docs_only: print(f"  + marco [{m['phase']}] {m['new_name']}")
            if apply and not docs_only:
                c, t = api("POST", f"/api/v2/list/{m['dst_list']}/task",
                           {"name": m["new_name"], "description": m["description"],
                            "tags": [tag] if tag else [], "custom_item_id": 1})
                mid = t.get("id") if c == 200 else None
                if mid:
                    set_fields(mid, fields)
                    if m.get("rel_field"):
                        api("POST", f"/api/v2/task/{mid}/field/{m['rel_field']}", {"value": {"add": [card]}})
                    else:
                        print(f"      ! sem rel_field p/ {m['phase']} — vinculo ao card nao feito")
                    ensure_checklists(mid, m["checklists"])
                    if prio: api("PUT", f"/api/v2/task/{mid}", {"priority": prio})
            st["marco_new"] += 1
        # documentos de referencia no proprio marco (replica TODOS os docs da origem)
        if docs_on:
            make_docs(mid, m, ssuf, dsuf, exp, doclabel, apply, st, "marco " + m["new_name"][:30], swaps)
        acts_for_marco = []   # (id_destino, nome) p/ a secao "Atividades" na descricao do marco
        for a in m["activities"]:
            adst = a.get("dst_list") or a.get("src_list")   # destino (cross-workspace via activity_map)
            aid = find_by_name(adst, a["new_name"]) if adst else None
            if aid:
                st["ativ_skip"] += 1
                if upd and apply and not docs_only:   # auto-heal: normaliza tipo de atividade ja existente
                    rn = type_for_name(a["new_name"], type_rules)
                    if rn:
                        rid = type_name_to_id(DST_WS, rn)
                        if rid: api("PUT", f"/api/v2/task/{aid}", {"custom_item_id": rid})
            else:
                if not docs_only: print(f"    + ativ {a['new_name'][:48]}")
                if apply and not docs_only and adst:
                    body = {"name": a["new_name"], "description": a["description"], "tags": [tag] if tag else []}
                    tt = a.get("task_type")
                    if ttmap is not None: tt = ttmap.get(str(tt))   # traduz/dropa tipo no cross-workspace
                    rn = type_for_name(a["new_name"], type_rules)   # normalizacao por nome (padrao Exos)
                    if rn:
                        rid = type_name_to_id(DST_WS, rn)
                        if rid: tt = rid                            # regra por nome PREVALECE sobre o tipo da origem
                    if tt: body["custom_item_id"] = tt
                    c, t = api("POST", f"/api/v2/list/{adst}/task", body)
                    aid = t.get("id") if c == 200 else None
                    if aid:
                        set_fields(aid, fields)
                        if mid: api("POST", f"/api/v2/task/{aid}/link/{mid}")
                        ensure_checklists(aid, a["checklists"])
                        if prio: api("PUT", f"/api/v2/task/{aid}", {"priority": prio})
                        # fix [ID]: tasks de Campanha referenciam o proprio id da task no nome/descricao
                        sid = a.get("src_id")
                        if sid and (sid in a["new_name"] or sid in (a.get("description") or "")):
                            api("PUT", f"/api/v2/task/{aid}", {
                                "name": a["new_name"].replace(sid, aid),
                                "description": (a.get("description") or "").replace(sid, aid)})
                st["ativ_new"] += 1
            if aid:
                acts_for_marco.append((aid, a["new_name"]))
            # documentos de trabalho (replica TODOS os docs da origem da atividade)
            if docs_on:
                make_docs(aid, a, ssuf, dsuf, exp, doclabel, apply, st, a["new_name"][:36], swaps)
        # secao "Atividades" (links das tasks relacionadas) na descricao do marco
        if mid and acts_for_marco and not docs_only:
            print(f"      secao Atividades -> marco {m['new_name'][:40]} ({len(acts_for_marco)} links)")
            append_atividades(mid, acts_for_marco, apply)
    print("\n==== RESUMO EXECUTE ====")
    print(json.dumps(st, indent=2, ensure_ascii=False))

# ---------- main ----------
def main():
    if not TOKEN: print("ERRO: defina CLICKUP_TOKEN"); sys.exit(1)
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("discover"); d.add_argument("--config", required=True); d.add_argument("--out", default="plano.json")
    e = sub.add_parser("execute"); e.add_argument("--plan", required=True); e.add_argument("--apply", action="store_true"); e.add_argument("--docs-only", action="store_true")
    args = ap.parse_args()
    if args.cmd == "discover":
        cfg = json.load(open(args.config))
        print(f"Descobrindo origem {cfg['source']['suffix']} ...")
        plan = discover(cfg)
        json.dump(plan, open(args.out, "w"), ensure_ascii=False, indent=2)
        print_summary(plan)
        print(f"\nplano salvo em {args.out} (edite-o para adaptar; depois rode 'execute --plan {args.out}')")
    elif args.cmd == "execute":
        execute(json.load(open(args.plan)), args.apply, getattr(args, "docs_only", False))

if __name__ == "__main__":
    main()
