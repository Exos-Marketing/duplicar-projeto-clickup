#!/usr/bin/env python3
"""
remapear_descricoes.py — remonta a descrição das tasks NOVAS a partir do markdown da ORIGEM.

Por quê: o discover do engine lê a descrição em TEXTO PURO. Menção de Doc, bookmark de Drive e
formatação se perdem, e os links que sobram continuam apontando para a ORIGEM (marco de
planejamento, Docs, tasks, pastas). Aqui cada descrição é remontada do markdown_description da
origem (versão genérica do fix_et_bf_from_ll.py, SEM a troca de expert dele):

  1. name_swaps nas formas normal e escapada ([..] e \\[..\\]) + expert_swap do config (se houver);
  2. remove a seção plana **Atividades** antiga e as linhas "Documento(s) de entrega:" dos Docs da
     própria task na origem (são reescritas abaixo com os do destino);
  3. remove linha que aponta para task apagada;
  4. religa links: task (/t/{id} e /t/{ws}/{id}), Doc (/docs/{did}[/{pid}], /v/dc/{did}) e ids soltos
     da origem -> destino; pastas do Drive pelo mapa do espelhar_drive.py (id cru E com "\\_");
  5. reescreve as linhas do destino: "Documento(s) de entrega: {Doc} — {URL}" (atividades),
     "Planejamento estratégico: {marco}" (copies, sem duplicar) e, nos marcos, a seção plana
     **Atividades** só se a lista agrupada não cobrir todas as atividades;
  6. linhas_topo (config remap): linha fixa no topo de uma task (ex.: aviso de oferta adaptada).

Nunca escreve no card, nos reaproveitados (acabamento.reaproveitados) nem em remap.nunca_escrever.
Antes de tudo checa duplicata de task e de Doc (o resolvedor aborta).

Uso:
  python3 remapear_descricoes.py --config config_X.json --mapa-drive mapa_drive_X.json        # dry-run
  python3 remapear_descricoes.py --config config_X.json --mapa-drive mapa_drive_X.json --apply
  ... --show <id_destino>,<id>   (imprime origem e resultado completos dessas tasks)
"""
import argparse, re, sys
import comum
from comum import api, esc_colchetes, get_task, norm_ascii, t_url

SENT = "**Atividades**"
RX_TASK = re.compile(r"https://app\.clickup\.com/t/(?:\d+/)?([a-z0-9]{7,12})\b")
RX_DOC = re.compile(r"https://app\.clickup\.com/\d+/(?:docs|v/dc)/([a-z0-9]+-[0-9]+)(?:/([a-z0-9]+-[0-9]+))?(?:\?[^\s)\]]*)?")


def normaliza(s):
    s = re.sub(r"\[(https?://[^\]\s]+)\]\(\1\)", r"\1", s or "")
    s = re.sub(r"\[([^\]\s/]+\.[^\]\s/]+)\]\(https?://\1/?\)", r"\1", s)   # domínio solto que o ClickUp autolinka
    s = comum.unesc(s)
    return re.sub(r"\s+", " ", s).strip()


class Remap:
    def __init__(self, pj, mapa_drive):
        self.pj = pj
        self.rcfg = pj.cfg.get("remap") or {}
        ents, erros = pj.resolver()
        if erros:
            print("!! RESOLVEDOR COM ERROS — ABORTADO")
            [print("   " + x) for x in erros]
            sys.exit(2)
        self.ents = ents
        self.tmap = pj.tmap(ents)
        self.dmap, self.por_task, erros = pj.mapa_docs(ents)
        if erros:
            print("!! DOCS DUPLICADOS/SEM PAR — ABORTADO")
            [print("   " + x) for x in erros]
            sys.exit(2)
        for did, (d2, p2) in (self.rcfg.get("doc_extra") or {}).items():
            self.dmap[did] = {"did": d2, "pid": p2}
        self.drive = {}
        if mapa_drive:
            md = comum.load_json(mapa_drive)
            self.drive[md["origem_raiz"]] = md["destino_raiz"]
            for p in md["pastas"]:
                if p.get("destino"):
                    self.drive[p["origem"]] = p["destino"]
        self.nunca = set(self.rcfg.get("nunca_escrever") or []) | pj.reaproveitados | {pj.card_dst}
        pjm = [e for e in ents if e["kind"] == "marco" and
               norm_ascii(pj.cfg.get("planejamento_marco", "planejamento estrategico")) in norm_ascii(e["name"])]
        self.pj_url = t_url(pjm[0]["dst_id"]) if pjm else None
        self.own_src_docs = {}
        for e in ents:
            self.own_src_docs[e["dst_id"]] = {rd["url"].split("/docs/")[1].split("/")[0]
                                             for rd in (e["obj"].get("ref_docs") or [])}
        self.acts = {}
        for e in ents:
            if e["kind"] == "ativ":
                self.acts.setdefault(e["marco_src"], []).append((e["dst_id"], e["name"]))
        self._existe = {}
        self.rules = pj.cfg.get("task_type_rules", pj.eng.DEFAULT_TYPE_RULES)

    def _task(self, tid):
        if tid not in self._existe:
            c, b = api("GET", f"/api/v2/task/{tid}")
            self._existe[tid] = b if (c == 200 and isinstance(b, dict) and not b.get("deleted")) else None
        return self._existe[tid]

    def existe(self, tid):
        return self._task(tid) is not None

    def descartada_origem(self, tid):
        """Task do projeto de ORIGEM que ficou fora do plano por skip_status (ex.: descartada):
        a linha que a cita não tem equivalente no destino."""
        t = self._task(tid)
        if not t:
            return False
        skip = {s.lower() for s in (self.pj.cfg.get("source") or {}).get("skip_status") or []}
        nome = t.get("name") or ""
        da_origem = self.pj.src_suf in nome or any(a in nome for a, _ in self.pj.swaps)
        return da_origem and ((t.get("status") or {}).get("status") or "").lower() in skip

    def religa(self, txt, flags):
        ws = self.pj.ws

        def f_task(m):
            return t_url(self.tmap[m.group(1)]) if m.group(1) in self.tmap else m.group(0)

        def f_doc(m):
            d = self.dmap.get(m.group(1))
            if d:
                return f"https://app.clickup.com/{ws}/docs/{d['did']}/{d['pid']}"
            flags.add(f"doc fora do mapa: {m.group(0)}")
            return m.group(0)
        txt = RX_TASK.sub(f_task, txt)
        txt = RX_DOC.sub(f_doc, txt)
        for a, b in self.drive.items():
            txt = txt.replace(a, b).replace(a.replace("_", "\\_"), b.replace("_", "\\_"))
        for a, b in self.tmap.items():
            if a in txt:
                txt = re.sub(rf"(?<![a-z0-9]){a}(?![a-z0-9])", b, txt)
        return txt

    def remonta(self, e, md):
        flags = set()
        txt = md or ""
        for a, b in self.pj.swaps:
            txt = txt.replace(a, b).replace(esc_colchetes(a), esc_colchetes(b))
        for a, b in self.pj.exp.items():
            txt = txt.replace(a, b)
        if SENT in txt:
            txt = txt.split(SENT)[0].rstrip()
        novas = []
        for ln in txt.split("\n"):
            if ln.strip().startswith("Documento(s) de entrega:"):
                dids = {m.group(1) for m in RX_DOC.finditer(ln)}
                if dids and dids <= self.own_src_docs.get(e["dst_id"], set()):
                    continue
            mortos = [m.group(1) for m in RX_TASK.finditer(ln)
                      if m.group(1) not in self.tmap and not self.existe(m.group(1))]
            if mortos:
                flags.add(f"linha removida (task apagada {mortos}): {ln.strip()[:80]}")
                continue
            fora = [m.group(1) for m in RX_TASK.finditer(ln)
                    if m.group(1) not in self.tmap and self.descartada_origem(m.group(1))]
            if fora:
                flags.add(f"linha removida (task da origem descartada, fora do plano {fora}): {ln.strip()[:70]}")
                continue
            novas.append(ln)
        txt = self.religa("\n".join(novas), flags)
        destino = set(self.tmap.values())
        for m in RX_TASK.finditer(txt):
            if m.group(1) not in destino:
                flags.add(f"task externa citada: {m.group(0)}")
        txt = re.sub(r"\n*Atividades:\s*$", "", txt.rstrip()).rstrip()
        if e["kind"] == "ativ":
            for d in self.por_task.get(e["dst_id"], []):
                url = f"https://app.clickup.com/{self.pj.ws}/docs/{d['did']}/{d['pid']}"
                if url not in txt:
                    txt = (txt + f"\n\nDocumento(s) de entrega: {d['name']} — {url}").lstrip("\n")
            if self.pj_url and self.pj.eng.type_for_name(e["name"], self.rules) == "Copy":
                if self.pj_url not in txt:
                    txt = (txt + f"\n\nPlanejamento estratégico: {self.pj_url}").lstrip("\n")
                else:
                    vistos, out = 0, []
                    for ln in txt.split("\n"):
                        if ln.strip().lower().startswith("planejamento estratégico:") and self.pj_url in ln:
                            vistos += 1
                            if vistos > 1:
                                continue
                        out.append(ln)
                    txt = "\n".join(out)
        if e["kind"] == "marco":
            acts = self.acts.get(e["src_id"], [])
            if acts and [1 for aid, _ in acts if f"/t/{aid}" not in txt]:
                txt = (txt.rstrip() + "\n\n" + SENT + "\n" + "\n".join(
                    f"{nm} — {t_url(aid)}" for aid, nm in acts)).lstrip("\n")
        topo = (self.rcfg.get("linhas_topo") or {}).get(e["src_id"])
        if topo and topo not in txt:
            txt = topo + "\n\n" + txt
        return re.sub(r"\n{3,}", "\n\n", txt).strip(), flags

    def rodar(self, apply, show):
        mudou, fila = 0, []
        alvo = [e for e in self.ents if e["kind"] != "card" and e["dst_id"] not in self.nunca]
        print(f"descrições a remontar: {len(alvo)} (protegidas: {sorted(self.nunca)})")
        for e in alvo:
            md = get_task(e["src_id"], md=True).get("markdown_description") or ""
            novo, flags = self.remonta(e, md)
            atual = (get_task(e["dst_id"], md=True).get("markdown_description") or "").strip()
            if flags:
                fila.append({"task": e["dst_id"], "nome": e["name"], "motivos": sorted(flags)})
            if e["dst_id"] in show:
                print(f"\n######## {e['name']} ({e['dst_id']})\n--- ORIGEM ---\n{md}\n--- NOVO ---\n{novo}\n--- FLAGS: {sorted(flags)}\n")
            if normaliza(novo) == normaliza(atual):
                continue
            mudou += 1
            print(f"  ~ {e['kind']:<5} {e['dst_id']}  {e['name'][:62]}  ({len(atual)} -> {len(novo)}){'  [flags]' if flags else ''}")
            if apply:
                c, b = api("PUT", f"/api/v2/task/{e['dst_id']}", {"markdown_content": novo})
                if c != 200:
                    print(f"      ! PUT {c} {str(b)[:120]}")
                    continue
                back = get_task(e["dst_id"], md=True).get("markdown_description") or ""
                if normaliza(back) != normaliza(novo):
                    print("      (o ClickUp normalizou o markdown — conferir no verify)")
        print(f"\ndescrições {'gravadas' if apply else 'a gravar'}: {mudou}")
        if fila:
            print(f"avisos ({len(fila)} task(s)):")
            for f in fila:
                print(f"   - {f['nome'][:60]}: {'; '.join(f['motivos'])[:300]}")
        if not apply:
            print("[DRY-RUN] rode com --apply para gravar")
        return fila


def main():
    ap = comum.args_comuns(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--mapa-drive", help="JSON gerado pelo espelhar_drive.py")
    ap.add_argument("--show", default="", help="ids de destino para imprimir por inteiro")
    a = ap.parse_args()
    pj = comum.Projeto(a.config, a.plan or comum.plano_padrao(a.config))
    Remap(pj, a.mapa_drive).rodar(a.apply, set(x for x in a.show.split(",") if x))


if __name__ == "__main__":
    main()
