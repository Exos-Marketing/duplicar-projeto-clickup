#!/usr/bin/env python3
"""
acabamento.py — acabamento pós-duplicação (skill duplicar-projeto-clickup).

O engine cria marcos, atividades e Docs, mas NÃO copia os campos da origem (só os de config.fields,
iguais para todos), aplica uma etiqueta só e não mexe em responsável, data nem status. Este script
fecha isso por REGRA, lendo o bloco "acabamento" do config do projeto:

  campos      copia, task a task, os campos editáveis da origem: drop_down (orderindex -> uuid), labels,
              users, texto, número/moeda, data, checkbox, emoji e progresso manual. Aplica
              campos_override (ex.: Idioma) e substituir_usuarios (ex-membro -> substituto).
              Pula list_relationship (apontaria para o card da ORIGEM), tasks, automáticos e fórmula.
  etiquetas   etiquetas da origem + etiquetas_extra (nome codificado na URL: perpétuo -> perp%C3%A9tuo;
              sem isso a chamada falha em silêncio).
  pessoas     responsáveis por regra (card / marco / ativ). [] = ninguém; null = não mexe.
  datas       vencimento por regra, sempre com start_date nulo (a Exos não usa data de início).
  prioridade  prioridade por regra.
  reparo      nas tasks NOVAS: vínculo atividade->marco, marco->card e os checklists do plano.
  sweep       zera o start_date que o ClickUp grava sozinho (dependências), em até 3 passadas.
  status      SÓ com --only status: status por regra (tipo/nome). Com status_exige_marcador_doc, só
              move a task cujos Docs já contêm o marcador (ex.: tradução gravada e relida).

Itens em "reaproveitados" (criados antes, à mão) só recebem o que está VAZIO — nada é sobrescrito.
Sem --apply é dry-run (só GET). --verify relê tudo e lista o que diverge da regra.

Uso:
  python3 acabamento.py --config config_X.json                       # dry-run, fases padrão
  python3 acabamento.py --config config_X.json --apply
  python3 acabamento.py --config config_X.json --apply --only status
  python3 acabamento.py --config config_X.json --verify
"""
import argparse, sys, time, urllib.parse
import comum
from comum import clean, day_of, due_ms, get_task, must_get, api

FASES_PADRAO = ["campos", "etiquetas", "pessoas", "datas", "prioridade", "reparo", "sweep"]
PULA_TIPOS = {"list_relationship", "tasks", "automatic_progress", "formula", "rollup", "button",
              "signature", "votes", "attachment", "location"}


# ---------------------------------------------------------------- valores de campo
def valor_normal(f, subst=None):
    """Valor comparável de um custom field lido da API (None = vazio)."""
    t, v = f.get("type"), f.get("value")
    if v in (None, "", []):
        return None
    if t == "drop_down":
        for o in (f.get("type_config") or {}).get("options") or []:
            if str(o.get("orderindex")) == str(v) or o.get("id") == v:
                return o["id"]
        return None
    if t == "labels":
        return sorted(v)
    if t == "users":
        ids = []
        for u in v:
            uid = u.get("id") if isinstance(u, dict) else u
            if subst:
                uid = subst.get(str(uid), uid)
            ids.append(int(uid))
        return sorted(set(ids))
    if t in ("number", "currency"):
        try:
            return float(v)
        except Exception:
            return v
    if t == "emoji":
        return int(float(v))
    if t == "date":
        return int(v)
    if t == "checkbox":
        return v in (True, "true", 1, "1")
    if t == "manual_progress":
        return float((v or {}).get("current", 0)) if isinstance(v, dict) else float(v)
    return v


def corpo_campo(tipo, quero, atual):
    if tipo == "users":
        add = [u for u in quero if u not in (atual or [])]
        rem = [u for u in (atual or []) if u not in quero]
        val = {"add": add}
        if rem:
            val["rem"] = rem
        return {"value": val}
    if tipo == "manual_progress":
        return {"value": {"current": quero}}
    return {"value": quero}


def campos_por_id(t):
    return {f["id"]: f for f in t.get("custom_fields") or []}


# ---------------------------------------------------------------- regras
class Acabamento:
    def __init__(self, pj, apply):
        self.pj, self.apply, self.a = pj, apply, pj.acab
        self.subst = {str(k): v for k, v in (self.a.get("substituir_usuarios") or {}).items()}
        self.override = self.a.get("campos_override") or {}
        self.ignorar = set(self.a.get("campos_ignorar") or [])
        self.regras = self.a.get("regras") or {}
        self.problemas, self.mudancas = [], 0
        self._src, self._dst = {}, {}

    def src(self, e):
        if e["src_id"] not in self._src:
            self._src[e["src_id"]] = get_task(e["src_id"])
        return self._src[e["src_id"]]

    def dst(self, e, fresh=False):
        if fresh or e["dst_id"] not in self._dst:
            self._dst[e["dst_id"]] = get_task(e["dst_id"])
        return self._dst[e["dst_id"]]

    def regra(self, e, chave):
        return (self.regras.get(e["kind"]) or {}).get(chave)

    def log(self, e, msg):
        print(f"   {'·' if not self.apply else '~'} [{e['kind']}{'/reap' if e['reap'] else ''}] {e['name'][:58]} :: {msg}")

    # -- campos
    def campos_quero(self, e):
        """-> {fid: (tipo, valor, nome)} desejado no destino."""
        quero = {}
        s = self.src(e)
        if self.a.get("copiar_campos_origem", True):
            for f in s.get("custom_fields") or []:
                if f.get("type") in PULA_TIPOS or f["id"] in self.ignorar:
                    continue
                v = valor_normal(f, self.subst)
                if v is not None:
                    quero[f["id"]] = (f["type"], v, f.get("name"))
        d = campos_por_id(self.dst(e))
        for fid, val in self.override.items():
            if fid in d:
                quero[fid] = (d[fid]["type"], val, d[fid].get("name"))
        return quero

    def diffs_campos(self, e):
        d = campos_por_id(self.dst(e, fresh=True))
        out = []
        for fid, (tipo, val, nome) in self.campos_quero(e).items():
            if fid not in d:
                out.append((fid, tipo, val, nome, "AUSENTE"))
                continue
            atual = valor_normal(d[fid])
            if atual == val:
                continue
            if e["reap"] and atual is not None:
                continue   # reaproveitado: só o vazio
            out.append((fid, tipo, val, nome, atual))
        return out

    def fase_campos(self, e):
        todos = self.diffs_campos(e)
        for x in todos:
            if x[4] == "AUSENTE":
                self.problemas.append(f"{e['name']}: campo {x[3]} não existe na lista destino (pulado)")
        diffs = [x for x in todos if x[4] != "AUSENTE"]
        if not diffs:
            return
        self.log(e, "campos: " + ", ".join(f"{n}" for _, _, _, n, _ in diffs))
        if not self.apply:
            return
        for fid, tipo, val, nome, atual in diffs:
            c, b = api("POST", f"/api/v2/task/{e['dst_id']}/field/{fid}", corpo_campo(tipo, val, atual if isinstance(atual, list) else None))
            if c != 200:
                self.problemas.append(f"{e['name']}: campo {nome} -> {c} {str(b)[:90]}")
        self.mudancas += 1
        sobra = self.diffs_campos(e)
        for fid, tipo, val, nome, atual in sobra:
            self.problemas.append(f"{e['name']}: campo {nome} NÃO GRAVOU (quero {val}, ficou {atual})")

    # -- etiquetas
    def etiquetas_quero(self, e):
        q = []
        if self.a.get("copiar_etiquetas_origem", True):
            q += [x["name"] for x in self.src(e).get("tags") or []]
        q += self.a.get("etiquetas_extra") or []
        out = []
        for x in q:
            if x.lower() not in [y.lower() for y in out]:
                out.append(x)
        return out

    def fase_etiquetas(self, e):
        tem = {x["name"].lower() for x in self.dst(e, fresh=True).get("tags") or []}
        falta = [x for x in self.etiquetas_quero(e) if x.lower() not in tem]
        if not falta:
            return
        self.log(e, f"etiquetas + {falta}")
        if not self.apply:
            return
        for x in falta:
            c, b = api("POST", f"/api/v2/task/{e['dst_id']}/tag/{urllib.parse.quote(x, safe='')}")
            if c != 200:
                self.problemas.append(f"{e['name']}: etiqueta {x} -> {c} {str(b)[:90]}")
        self.mudancas += 1
        tem = {x["name"].lower() for x in self.dst(e, fresh=True).get("tags") or []}
        for x in falta:
            if x.lower() not in tem:
                self.problemas.append(f"{e['name']}: etiqueta {x} NÃO GRAVOU")

    # -- pessoas
    def fase_pessoas(self, e):
        quero = self.regra(e, "responsaveis")
        if quero is None:
            return
        cur = [a["id"] for a in self.dst(e, fresh=True).get("assignees") or []]
        if e["reap"]:
            if cur or not quero:
                return
            add, rem = list(quero), []
        else:
            add = [u for u in quero if u not in cur]
            rem = [u for u in cur if u not in quero]
        if not add and not rem:
            return
        self.log(e, f"responsáveis +{add} -{rem}")
        if not self.apply:
            return
        c, b = api("PUT", f"/api/v2/task/{e['dst_id']}", {"assignees": {"add": add, "rem": rem}})
        if c != 200:
            self.problemas.append(f"{e['name']}: responsáveis -> {c} {str(b)[:90]}")
        self.mudancas += 1
        back = sorted(a["id"] for a in self.dst(e, fresh=True).get("assignees") or [])
        esperado = sorted(set(cur + add) - set(rem))
        if back != esperado:
            self.problemas.append(f"{e['name']}: responsáveis NÃO GRAVARAM (quero {esperado}, ficou {back})")

    # -- datas
    def fase_datas(self, e):
        venc = self.regra(e, "vencimento")
        if not venc:
            return
        t = self.dst(e, fresh=True)
        if e["reap"] and t.get("due_date"):
            return
        if day_of(t.get("due_date")) == venc and not t.get("start_date"):
            return
        self.log(e, f"vencimento {day_of(t.get('due_date'))} -> {venc}")
        if not self.apply:
            return
        c, b = api("PUT", f"/api/v2/task/{e['dst_id']}", {"due_date": due_ms(venc), "due_date_time": False,
                                                          "start_date": None, "start_date_time": False})
        if c != 200:
            self.problemas.append(f"{e['name']}: vencimento -> {c} {str(b)[:90]}")
        self.mudancas += 1

    # -- prioridade
    def fase_prioridade(self, e):
        p = self.regra(e, "prioridade")
        if p is None:
            return
        pr = self.dst(e, fresh=True).get("priority")
        cur = int(pr["id"]) if pr else None
        if cur == p or (e["reap"] and cur is not None):
            return
        self.log(e, f"prioridade {cur} -> {p}")
        if not self.apply:
            return
        c, b = api("PUT", f"/api/v2/task/{e['dst_id']}", {"priority": p})
        if c != 200:
            self.problemas.append(f"{e['name']}: prioridade -> {c} {str(b)[:90]}")
        self.mudancas += 1

    # -- reparo (só tasks novas)
    def fase_reparo(self, e):
        if e["kind"] == "card":
            return
        t = self.dst(e, fresh=True)
        if e["kind"] == "marco" and not e["reap"]:
            rel = e["obj"].get("rel_field")
            d = campos_por_id(t).get(rel) if rel else None
            ligados = [x.get("id") for x in (d or {}).get("value") or []] if d else []
            if rel and self.pj.card_dst not in ligados:
                self.log(e, "vínculo marco->card")
                if self.apply:
                    c, b = api("POST", f"/api/v2/task/{e['dst_id']}/field/{rel}", {"value": {"add": [self.pj.card_dst]}})
                    if c != 200:
                        self.problemas.append(f"{e['name']}: vínculo ao card -> {c}")
        if e["kind"] == "ativ" and e.get("marco_dst"):
            ids = {x.get("task_id") for x in t.get("linked_tasks") or []} | {x.get("link_id") for x in t.get("linked_tasks") or []}
            if e["marco_dst"] not in ids:
                self.log(e, "vínculo atividade->marco")
                if self.apply:
                    c, b = api("POST", f"/api/v2/task/{e['marco_dst']}/link/{e['dst_id']}")
                    if c != 200:
                        self.problemas.append(f"{e['name']}: link ao marco -> {c}")
        if e["reap"] and not self.a.get("checklists_nos_reaproveitados"):
            return
        for cl in e["obj"].get("checklists") or []:
            self.checklist(e, cl["name"], cl["items"])

    def checklist(self, e, nome, itens):
        t = self.dst(e, fresh=True)
        cl = next((c for c in t.get("checklists") or [] if clean(c["name"]) == clean(nome)), None)
        tem = {clean(i["name"]) for i in (cl or {}).get("items") or []}
        falta = [i for i in itens if clean(i) not in tem]
        if cl and not falta:
            return
        self.log(e, f"checklist '{nome}': {len(falta)} item(ns)")
        if not self.apply:
            return
        if not cl:
            c, b = api("POST", f"/api/v2/task/{e['dst_id']}/checklist", {"name": nome}, create=True)
            if c in (429, 0):
                time.sleep(10)
                cl = next((x for x in self.dst(e, fresh=True).get("checklists") or [] if clean(x["name"]) == clean(nome)), None)
                if not cl:
                    self.problemas.append(f"{e['name']}: checklist {nome} 429/timeout e não encontrado")
                    return
                cid = cl["id"]
            elif c != 200:
                self.problemas.append(f"{e['name']}: checklist {nome} -> {c}")
                return
            else:
                cid = b["checklist"]["id"]
        else:
            cid = cl["id"]
        for i in falta:
            c, b = api("POST", f"/api/v2/checklist/{cid}/checklist_item", {"name": i}, create=True)
            if c in (429, 0):
                time.sleep(10)
                cur = next((x for x in self.dst(e, fresh=True).get("checklists") or [] if x["id"] == cid), {})
                if clean(i) not in {clean(x["name"]) for x in cur.get("items") or []}:
                    api("POST", f"/api/v2/checklist/{cid}/checklist_item", {"name": i})
        self.mudancas += 1

    # -- status
    def status_quero(self, e):
        if e["kind"] != "ativ" or e["reap"]:
            return None
        t = self.dst(e)
        for r in self.a.get("status") or []:
            if r.get("tipo") and t.get("custom_item_id") == comum.tipo_id(self.pj.ws, r["tipo"]):
                return r["status"]
            if r.get("nome_comeca") and clean(t.get("name")).lower().startswith(clean(r["nome_comeca"]).lower()):
                return r["status"]
        return None

    def docs_prontos(self, e):
        marca = self.a.get("status_exige_marcador_doc")
        if not marca:
            return True, ""
        ds = self.pj.docs_de(e["dst_id"])
        if not ds:
            return False, "sem Doc"
        for d in ds:
            pg = must_get(f"/api/v3/workspaces/{self.pj.ws}/docs/{d['did']}/pages/{d['pid']}?content_format=text%2Fmd")
            if comum.norm_ascii(marca) not in comum.norm_ascii(comum.unesc(pg.get("content") or "")):
                return False, f"Doc sem o marcador: {d['name'][:50]}"
        return True, ""

    def fase_status(self, e):
        st = self.status_quero(e)
        if not st:
            return
        t = self.dst(e, fresh=True)
        cur = ((t.get("status") or {}).get("status") or "").lower()
        if cur == st.lower():
            return
        ok, motivo = self.docs_prontos(e)
        if not ok:
            self.log(e, f"status fica '{cur}' ({motivo})")
            return
        self.log(e, f"status {cur} -> {st}")
        if not self.apply:
            return
        c, b = api("PUT", f"/api/v2/task/{e['dst_id']}", {"status": st})
        if c != 200:
            self.problemas.append(f"{e['name']}: status -> {c} {str(b)[:90]}")
            return
        self.mudancas += 1
        time.sleep(1.5)
        back = self.dst(e, fresh=True)
        if ((back.get("status") or {}).get("status") or "").lower() != st.lower():
            self.problemas.append(f"{e['name']}: status NÃO GRAVOU")
        quero = self.regra(e, "responsaveis")
        tem = [a["id"] for a in back.get("assignees") or []]
        if quero is not None and sorted(tem) != sorted(quero):
            self.problemas.append(f"{e['name']}: responsáveis mudaram após o status (automação?) -> {tem}")
            api("PUT", f"/api/v2/task/{e['dst_id']}", {"assignees": {"add": [u for u in quero if u not in tem],
                                                                   "rem": [u for u in tem if u not in quero]}})

    # -- sweep de start_date (só tasks novas)
    def sweep(self, ents):
        alvo = [e for e in ents if e["kind"] != "card" and not e["reap"]]
        print(f"\n== SWEEP start_date ({len(alvo)} tasks novas)")
        if self.apply:
            time.sleep(20)   # o reagendamento por dependência do ClickUp é assíncrono
        for passo in range(1, 4):
            sujas = []
            for e in alvo:
                t = self.dst(e, fresh=True)
                if t.get("start_date"):
                    sujas.append((e, t))
            print(f"   passada {passo}: {len(sujas)} task(s) com start_date")
            if not sujas or not self.apply:
                break
            for e, t in sujas:
                body = {"start_date": None, "start_date_time": False}
                if t.get("due_date"):
                    body.update({"due_date": int(t["due_date"]), "due_date_time": False})
                c, b = api("PUT", f"/api/v2/task/{e['dst_id']}", body)
                print(f"      {e['name'][:60]}: start={day_of(t.get('start_date'))} -> {c}")
            time.sleep(8)

    # -- verify
    def verify(self, ents):
        print("\n== VERIFY (só leitura)")
        div = []
        for e in ents:
            nome = f"[{e['kind']}{'/reap' if e['reap'] else ''}] {e['name'][:56]}"
            for fid, tipo, val, n, atual in self.diffs_campos(e):
                div.append(f"{nome}: campo {n} quero {val} · está {atual}")
            tem = {x["name"].lower() for x in self.dst(e).get("tags") or []}
            falta = [x for x in self.etiquetas_quero(e) if x.lower() not in tem]
            if falta:
                div.append(f"{nome}: faltam etiquetas {falta}")
            t = self.dst(e)
            resp = self.regra(e, "responsaveis")
            cur = sorted(a["id"] for a in t.get("assignees") or [])
            if resp is not None and not (e["reap"] and cur) and cur != sorted(resp):
                div.append(f"{nome}: responsáveis {cur} (regra {resp})")
            venc = self.regra(e, "vencimento")
            if venc and day_of(t.get("due_date")) != venc and not (e["reap"] and t.get("due_date")):
                div.append(f"{nome}: vencimento {day_of(t.get('due_date'))} (regra {venc})")
            p = self.regra(e, "prioridade")
            pr = int(t["priority"]["id"]) if t.get("priority") else None
            if p is not None and pr != p and not (e["reap"] and pr is not None):
                div.append(f"{nome}: prioridade {pr} (regra {p})")
            if not e["reap"] and e["kind"] != "card" and t.get("start_date"):
                div.append(f"{nome}: start_date preenchido ({day_of(t.get('start_date'))})")
            if e["kind"] == "ativ" and e.get("marco_dst"):
                ids = {x.get("task_id") for x in t.get("linked_tasks") or []} | {x.get("link_id") for x in t.get("linked_tasks") or []}
                if e["marco_dst"] not in ids:
                    div.append(f"{nome}: sem vínculo com o marco")
            if not e["reap"] and e["kind"] != "card":
                have = {clean(c["name"]): {clean(i["name"]) for i in c.get("items") or []} for c in t.get("checklists") or []}
                for cl in e["obj"].get("checklists") or []:
                    if not set(clean(i) for i in cl["items"]) <= have.get(clean(cl["name"]), set()):
                        div.append(f"{nome}: checklist '{cl['name']}' incompleto")
            stq = self.status_quero(e)
            if stq:
                cur_st = ((t.get("status") or {}).get("status") or "").lower()
                if cur_st != stq.lower():
                    div.append(f"{nome}: status '{cur_st}' (regra '{stq}', só depois do Doc)")
        print(f"   divergências: {len(div)}")
        for d in div:
            print("   - " + d)
        return div


def main():
    ap = comum.args_comuns(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--only", help="fases separadas por vírgula: " + ",".join(FASES_PADRAO + ["status"]))
    ap.add_argument("--ids", help="restringe a estes ids de destino (vírgula)")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    pj = comum.Projeto(a.config, a.plan or comum.plano_padrao(a.config))
    ents, erros = pj.resolver()
    print(f"resolvedor: {len(ents)} item(ns) (card + marcos + atividades) · reaproveitados: "
          f"{sum(1 for e in ents if e['reap'])}")
    if erros:
        print("!! RESOLVEDOR COM ERROS (faltando ou duplicado) — ABORTADO")
        for x in erros:
            print("   " + x)
        sys.exit(2)
    if a.ids:
        ids = set(a.ids.split(","))
        ents = [e for e in ents if e["dst_id"] in ids]
    ac = Acabamento(pj, a.apply and not a.verify)
    if a.verify:
        div = ac.verify(ents)
        sys.exit(1 if div else 0)
    fases = a.only.split(",") if a.only else FASES_PADRAO
    print(f"== ACABAMENTO [{'APLICANDO' if ac.apply else 'DRY-RUN'}] fases: {fases}")
    for fase in fases:
        if fase == "sweep":
            ac.sweep(ents)
            continue
        print(f"\n== {fase.upper()}")
        fn = getattr(ac, f"fase_{fase}")
        for e in ents:
            fn(e)
    print(f"\n==== RESUMO ==== tasks alteradas (por fase): {ac.mudancas} · problemas: {len(ac.problemas)}")
    for p in ac.problemas:
        print("   ! " + p)
    if not ac.apply:
        print("[DRY-RUN] rode com --apply para gravar")


if __name__ == "__main__":
    main()
