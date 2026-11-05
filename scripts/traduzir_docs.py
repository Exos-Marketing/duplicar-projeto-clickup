#!/usr/bin/env python3
"""
traduzir_docs.py — versão em outro idioma dos Docs de um projeto duplicado (skill duplicar-projeto-clickup).

Três modos, todos lendo o bloco "traducao" do config do projeto:

  pacotes   (só leitura) um JSON por Doc de ORIGEM do plano, em <pasta>/pacotes/NN_<slug>.json:
            markdown completo da origem (todas as páginas), nome do Doc destino, regras de idioma,
            tratamento, oferta e glossário, mapa de links origem->destino, "versão no ar" e texto já
            existente no idioma (quando houver). Gera também <pasta>/INSTRUCOES.md e INDEX.json.
            Não depende dos Docs de destino existirem — roda em paralelo com o --apply do engine.
            A TRADUÇÃO é feita fora daqui (subagentes), em <pasta>/es/NN_<slug>.md (só o corpo).

  aplicar   monta a página final de cada Doc de destino e grava (dry-run sem --apply):
              [Planejamento estratégico: … (Central de Link)]
              **Briefing:** <briefing do config>
              **Referência:** [url do Doc de origem]
              [**Versão no ar:** url] [aviso de "fora da oferta"]
              ---
              <corpo traduzido, com ids de task/Doc da origem trocados pelos do destino>
            Gates antes de gravar: corpo não vazio; toda URL da origem presente ou mapeada; anexos
            clickup-attachments intactos; nº de títulos; razão de tamanho; sobra de idioma de origem;
            termos proibidos fora das notas; nenhum id do projeto de origem; trecho reaproveitado com
            identificadores técnicos byte a byte.
            Só grava se a página estiver vazia, só com o cabeçalho do engine, ou (com --force) já com o
            marcador desta tradução. PUT replace SEM "name" e nunca com conteúdo vazio; relê e compara
            palavra a palavra + URLs. Se truncar, regrava em partes (append por "## ").

  verificar relê os Docs de destino e confere marcador, Referência e corpo.

Uso:
  python3 traduzir_docs.py pacotes   --config config_X.json
  python3 traduzir_docs.py aplicar   --config config_X.json [--only 07,12] [--apply] [--force]
  python3 traduzir_docs.py verificar --config config_X.json
"""
import argparse, json, os, re, sys, time
import comum
from comum import api, clean, must_get, norm_ascii

RX_URL = re.compile(r"https?://[^\s)\]>\"'`]+")
RX_NOTA = re.compile(r"\[⚠️ REVISAR \(LatAm\):[^\]]*\]")
RX_TIT = re.compile(r"^\s{0,3}#{1,6}\s", re.M)
RX_TASK = re.compile(r"https://app\.clickup\.com/t/(?:\d+/)?([a-z0-9]{7,12})\b")
RX_DOC = re.compile(r"https://app\.clickup\.com/\d+/(?:docs|v/dc)/([a-z0-9]+-[0-9]+)(?:/([a-z0-9]+-[0-9]+))?(?:\?[^\s)\]]*)?")
PT_PALAVRAS = re.compile(
    r"(?<![\wÀ-ÿ])(você|vocês|não|também|então|estão|são|pra|muito|muita|muitos|muitas|obrigad[oa]s?|seu|sua|seus|"
    r"suas|nosso|nossa|nossos|nossas|hoje|clique|garanta|aproveite|inscrição|inscrições|desconto|parcelamento|"
    r"cirurgião|consultório|lesões|até|já|ainda|agora|isso|esse|essa|esses|essas|onde|quando|pelo|pela|pelos|pelas|"
    r"uma|umas|um|uns|com|sem|mais|melhor|fazer|feito|pode|podem|vai|vão|aula|aulas)(?![\wÀ-ÿ])", re.I)
RX_PT_CHAR = re.compile(r"[\wÀ-ÿ]*[ãõç][\wÀ-ÿ]*", re.I)


def slug(s):
    s = norm_ascii(re.split(r"\s*\[", s or "")[0])
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60] or "doc"


def tokens(s):
    s = comum.unesc(s or "")
    s = re.sub(r"\[(https?://[^\]\s]+)\]\(\1\)", r"\1", s)
    s = re.sub(r"\[([^\]\s/]+\.[^\]\s/]+)\]\(https?://\1/?\)", r"\1", s)   # domínio solto que o ClickUp autolinka
    return re.findall(r"[0-9a-zà-ÿñ]+", s.lower())


def urls(s):
    return {u.rstrip(".,;:!?*_") for u in RX_URL.findall(comum.unesc(s or ""))}


class Trad:
    def __init__(self, pj):
        self.pj = pj
        self.t = pj.cfg.get("traducao") or {}
        self.pasta = self.t["pasta"]
        self.dir_p = os.path.join(self.pasta, "pacotes")
        self.dir_es = os.path.join(self.pasta, "es")

    # ------------------------------------------------------------ pacotes
    def docs_origem(self):
        """Docs de origem na ordem do plano -> [(nn, obj, ref_doc, kind)]."""
        out = []
        for m in self.pj.plan["marcos"]:
            for rd in m.get("ref_docs") or []:
                out.append((m, rd, "marco"))
            for a in m["activities"]:
                for rd in a.get("ref_docs") or []:
                    out.append((a, rd, "ativ"))
        return [(f"{i + 1:02d}", o, rd, k) for i, (o, rd, k) in enumerate(out)]

    def conteudo(self, did, ws=None):
        ws = ws or self.pj.src_ws
        pgs = must_get(f"/api/v3/workspaces/{ws}/docs/{did}/pages")
        out = []
        for p in pgs if isinstance(pgs, list) else []:
            c = must_get(f"/api/v3/workspaces/{ws}/docs/{did}/pages/{p['id']}?content_format=text%2Fmd")
            out.append({"id": p["id"], "name": p.get("name"), "content": c.get("content") or ""})
        return out

    def pacotes(self):
        os.makedirs(self.dir_p, exist_ok=True)
        os.makedirs(self.dir_es, exist_ok=True)
        idx = []
        for nn, obj, rd, kind in self.docs_origem():
            did = rd["url"].split("/docs/")[1].split("/")[0]
            pgs = self.conteudo(did)
            txt = "\n\n".join((f"## {p['name']}\n\n" if len(pgs) > 1 and p.get("name") else "") + p["content"] for p in pgs)
            dst_nome = self.pj.doc_alvo(rd.get("name"))
            sl = slug(dst_nome)
            modo = "traduzir"
            if did in (self.t.get("copiar_secao") or {}):
                modo = "secao"
            elif did in (self.t.get("texto_es_existente") or {}):
                modo = "base_existente"
            exist = None
            if modo == "base_existente":
                ref = self.t["texto_es_existente"][did]
                if isinstance(ref, dict) and ref.get("secao_na_origem"):
                    i = txt.find(ref["secao_na_origem"])
                    exist = txt[txt.rfind("\n", 0, i) + 1:] if i >= 0 else None
                else:
                    exist = open(ref, encoding="utf-8").read()
                if not exist:
                    sys.exit(f"!! texto existente não encontrado para {did}")
            pac = {"nn": nn, "slug": sl, "modo": modo, "src_did": did, "src_url": rd["url"], "src_nome": clean(rd.get("name")),
                   "dst_nome": dst_nome, "task_origem": obj["src_id"], "task_nome": clean(obj["new_name"]), "kind": kind,
                   "fora_da_oferta": (self.t.get("fora_da_oferta") or {}).get(did),
                   "versao_no_ar": (self.t.get("versao_no_ar") or {}).get(did),
                   "texto_existente": exist, "conteudo_origem": txt, "paginas": len(pgs),
                   "saida": os.path.join(self.dir_es, f"{nn}_{sl}.md")}
            comum.save_json(os.path.join(self.dir_p, f"{nn}_{sl}.json"), pac)
            idx.append({k: pac[k] for k in ("nn", "slug", "modo", "src_did", "dst_nome", "task_nome", "paginas")}
                       | {"chars": len(txt), "fora_da_oferta": bool(pac["fora_da_oferta"])})
            print(f"  {nn} [{modo:<14}] {len(txt):>6} chars · {dst_nome[:70]}")
        comum.save_json(os.path.join(self.pasta, "INDEX.json"), idx)
        self.instrucoes()
        tot = sum(x["chars"] for x in idx if x["modo"] != "secao")
        print(f"\n{len(idx)} pacote(s) em {self.dir_p} · {tot} chars a traduzir/adaptar · instruções: INSTRUCOES.md")

    def instrucoes(self):
        t = self.t
        gl = "\n".join(f"- {a} → {b}" for a, b in (t.get("glossario") or {}).items())
        lk = "\n".join(f"- {a} → {b}" for a, b in (t.get("mapa_links") or {}).items())
        extra = "\n".join(f"- {x}" for x in t.get("instrucoes_extra") or [])
        md = f"""# Instruções de tradução — {self.pj.suf}

Você recebe um pacote JSON por Doc (campo `conteudo_origem`, markdown do ClickUp) e grava **só o corpo
traduzido** em markdown no caminho do campo `saida`. Não escreva cabeçalho (Briefing/Referência): o
script de gravação acrescenta.

## Idioma e tom
- Idioma: {t.get('idioma')}. Tratamento: **{t.get('tratamento')}** (como as páginas no ar).
- Tom de copy de resposta direta, natural para o leitor nativo; nada de tradução palavra por palavra.
- Traduza TUDO, inclusive orientações internas e notas para o designer/editor.

## Oferta (adaptar)
{t.get('oferta', '')}

## Notas para o revisor
Quando algo não tiver equivalente no destino ou precisar de decisão, mantenha o trecho traduzido e
acrescente a nota EXATAMENTE neste formato, em português, sem "]" dentro:
`[⚠️ REVISAR (LatAm): explicação curta]`

## Preservar (o gate confere)
- Estrutura markdown: mesmos títulos (#), listas, negritos, separadores, emojis, tabelas e blocos de código.
- Toda URL da origem, byte a byte — exceto as do mapa de links abaixo, que viram a do destino.
- Imagens/anexos (`clickup-attachments`) exatamente como estão.
- Placeholders e variáveis (`{{{{...}}}}`, `[LINK ...]`, tags entre crases) sem traduzir.
- Nomes próprios e marcas (Elen Tolentino, Hotmart, WhatsApp, Instagram, Anhanguera).

## Glossário
{gl}

## Mapa de links (origem → destino)
{lk}

## Regras extras
{extra}

## Modos
- `traduzir`: traduza `conteudo_origem`.
- `base_existente`: já existe versão no idioma (`texto_existente`, é o que está no ar). Use esse texto
  **verbatim** onde ele cobre a origem (mesmos identificadores técnicos, links e variáveis) e traduza só
  o que a origem tiver a mais (orientações etc.), na ordem da origem.
- Docs com `fora_da_oferta`: traduza inteiro, como referência; o aviso vai no cabeçalho.
"""
        with open(os.path.join(self.pasta, "INSTRUCOES.md"), "w", encoding="utf-8") as f:
            f.write(md)

    # ------------------------------------------------------------ aplicar
    def carregar(self, only):
        out = []
        for fn in sorted(os.listdir(self.dir_p)):
            if fn.endswith(".json") and (not only or fn[:2] in only):
                out.append(comum.load_json(os.path.join(self.dir_p, fn)))
        return out

    def religa(self, txt, tmap, dmap):
        ws = self.pj.ws
        txt = RX_TASK.sub(lambda m: comum.t_url(tmap[m.group(1)]) if m.group(1) in tmap else m.group(0), txt)

        def fd(m):
            d = dmap.get(m.group(1))
            return f"https://app.clickup.com/{ws}/docs/{d['did']}/{d['pid']}" if d else m.group(0)
        return RX_DOC.sub(fd, txt)

    def secao(self, pac):
        cfg = self.t["copiar_secao"][pac["src_did"]]
        did = cfg.get("de_origem") or pac["src_did"]
        txt = "\n\n".join(p["content"] for p in self.conteudo(did))
        linhas = txt.split("\n")
        ini = next((i for i, l in enumerate(linhas) if cfg["titulo"].lower() in l.lower() and l.lstrip().startswith("#")), None)
        if ini is None:
            sys.exit(f"!! seção '{cfg['titulo']}' não encontrada em {did}")
        nivel = len(linhas[ini]) - len(linhas[ini].lstrip("#"))
        fim = len(linhas)
        for j in range(ini + 1, len(linhas)):
            l = linhas[j].lstrip()
            if l.startswith("#") and len(l) - len(l.lstrip("#")) <= nivel:
                fim = j
                break
        return "\n".join(linhas[ini:fim]).strip()

    def cabecalho(self, pac, atual):
        linhas = []
        pl = next((l.strip() for l in (atual or "").split("\n") if l.strip().lower().startswith("planejamento estratégico:")), None)
        if pl:
            linhas.append(pl)
        brief = ((self.t.get("copiar_secao") or {}).get(pac["src_did"]) or {}).get("briefing") or self.t["briefing"]
        linhas.append(f"**Briefing:** {brief}")
        linhas.append(f"**Referência:** [{pac['src_url']}]({pac['src_url']})")
        if pac.get("versao_no_ar"):
            linhas.append(f"**Versão no ar:** {pac['versao_no_ar']}")
        if pac.get("fora_da_oferta"):
            linhas.append(pac["fora_da_oferta"])
        return "\n\n".join(linhas)

    def gates(self, pac, corpo, tmap, dmap):
        g = dict(self.t.get("gates") or {})
        g.update((self.t.get("gates_por_doc") or {}).get(pac["src_did"]) or {})
        erros, avisos = [], []
        if not corpo.strip():
            return ["corpo vazio"], avisos
        if pac["modo"] == "secao":
            faltam = urls(self.religa(self.secao(pac), tmap, dmap)) - urls(corpo)
            if faltam:
                erros.append(f"seção copiada perdeu URLs: {sorted(faltam)[:3]}")
            return erros, avisos
        src = pac["conteudo_origem"]
        mapa = {**(self.t.get("mapa_links") or {})}
        c_urls = urls(corpo)
        for u in sorted(urls(src)):
            alvo = mapa.get(u)
            alvo = self.religa(alvo or u, tmap, dmap) if (alvo or RX_TASK.match(u) or RX_DOC.match(u)) else None
            if u in c_urls or (alvo and alvo in c_urls):
                continue
            if u in (self.t.get("links_podem_sair") or []):
                continue
            erros.append(f"URL da origem sumiu: {u[:90]}")
        if pac["modo"] == "base_existente":
            ex = pac["texto_existente"]
            # blocos de código inteiros primeiro: senão `[^`]+` casa o trecho ENTRE dois blocos
            for tok in set(re.findall(r"```.*?```|\{\{[^}]+\}\}|`[^`]+`", ex, re.S)) | urls(ex):
                if tok not in corpo and tok.rstrip(".,") not in c_urls:
                    erros.append(f"identificador do texto existente alterado/ausente: {tok[:80]}")
        ts, tc = len(RX_TIT.findall(src)), len(RX_TIT.findall(corpo))
        tol = g.get("titulos_tol", 0.1)
        if abs(ts - tc) > max(1, round(ts * tol)):
            erros.append(f"títulos: origem {ts} × tradução {tc}")
        r = len(corpo) / max(1, len(src))
        lo, hi = g.get("razao", [0.85, 1.45])
        if not (lo <= r <= hi):
            erros.append(f"razão de tamanho {r:.2f} fora de [{lo}, {hi}]")
        limpo = RX_NOTA.sub(" ", corpo)
        limpo = RX_URL.sub(" ", limpo)
        limpo = re.sub(r"```.*?```|`[^`]*`", " ", limpo, flags=re.S)
        limpo = re.sub(r"[\w-]+(\.[\w-]+)*\.(com|br|link|net|org|io|app)(\.[a-z]{2})?\b(/\S*)?", " ", limpo)
        for p in self.t.get("pt_permitidos") or []:
            limpo = limpo.replace(p, " ")
        pt = [m.group(0) for m in PT_PALAVRAS.finditer(limpo)]
        ptc = [m.group(0) for m in RX_PT_CHAR.finditer(limpo)]
        if ptc or len(pt) >= g.get("pt_max", 3):
            erros.append(f"sobra de português: {sorted(set(ptc + pt))[:12]}")
        elif pt:
            avisos.append(f"palavras que parecem PT: {sorted(set(pt))}")
        for termo in g.get("proibidos", self.t.get("proibidos") or []):
            if re.search(rf"(?<![\wÀ-ÿ]){re.escape(termo)}(?![\wÀ-ÿ])", limpo, re.I) or (not termo[-1].isalnum() and termo in limpo):
                erros.append(f"termo proibido fora das notas: {termo}")
        for termo in self.t.get("evitar") or []:
            if re.search(rf"(?<![\wÀ-ÿ]){re.escape(termo)}(?![\wÀ-ÿ])", limpo, re.I):
                avisos.append(f"termo a evitar: {termo}")
        sobra = [i for i in list(tmap) + list(dmap) if i in corpo]
        if sobra:
            erros.append(f"ids do projeto de origem no corpo: {sobra[:5]}")
        notas = len(RX_NOTA.findall(corpo))
        if notas:
            avisos.append(f"{notas} nota(s) ⚠️ para o revisor")
        return erros, avisos

    def eh_cabecalho_engine(self, atual):
        s = comum.unesc(atual or "")
        s = re.sub(r"\[(https?://[^\]\s]+)\]\(\1\)", r"\1", s)
        s = re.sub(r"\s+", " ", s.replace("**", "")).strip()
        return s == "" or bool(re.fullmatch(r"(Planejamento estratégico: \S+ )?Briefing: Referência: \S+", s))

    def gravar(self, did, pid, conteudo):
        base = f"/api/v3/workspaces/{self.pj.ws}/docs/{did}/pages/{pid}"
        if not conteudo.strip():
            raise RuntimeError("conteúdo vazio — nunca gravar vazio")
        c, b = api("PUT", base, {"content": conteudo, "content_format": "text/md", "content_edit_mode": "replace"})
        if c != 200:
            return False, f"PUT {c} {str(b)[:120]}"
        time.sleep(1.0)
        back = must_get(f"{base}?content_format=text%2Fmd").get("content") or ""
        if tokens(back) == tokens(conteudo) and urls(conteudo) <= urls(back):
            return True, "ok"
        # fallback: em partes, cortando nos "## "
        partes, atual = [], ""
        for bloco in re.split(r"(?=\n## )", conteudo):
            if atual and len(atual) + len(bloco) > 12000:
                partes.append(atual)
                atual = ""
            atual += bloco
        partes.append(atual)
        c, b = api("PUT", base, {"content": partes[0], "content_format": "text/md", "content_edit_mode": "replace"})
        for p in partes[1:]:
            time.sleep(0.8)
            api("PUT", base, {"content": p, "content_format": "text/md", "content_edit_mode": "append"})
        time.sleep(1.0)
        back = must_get(f"{base}?content_format=text%2Fmd").get("content") or ""
        if tokens(back) == tokens(conteudo) and urls(conteudo) <= urls(back):
            return True, f"ok em {len(partes)} partes"
        return False, f"releitura diverge ({len(tokens(back))} × {len(tokens(conteudo))} palavras)"

    def aplicar(self, only, apply, force):
        ents, erros = self.pj.resolver()
        if erros:
            print("!! RESOLVEDOR COM ERROS — ABORTADO")
            [print("   " + x) for x in erros]
            sys.exit(2)
        tmap = self.pj.tmap(ents)
        dmap, _, erros = self.pj.mapa_docs(ents)
        if erros:
            print("!! DOCS DUPLICADOS/SEM PAR — ABORTADO")
            [print("   " + x) for x in erros]
            sys.exit(2)
        marca = self.t.get("marcador") or self.t["briefing"][:40]
        rel, st = [], {"gravado": 0, "ja_ok": 0, "pendente": 0, "reprovado": 0, "pulado": 0, "erro": 0}
        for pac in self.carregar(only):
            d = dmap.get(pac["src_did"])
            nome = f"{pac['nn']} {pac['dst_nome'][:62]}"
            if not d:
                print(f"  ! {nome}: Doc de destino não encontrado")
                st["erro"] += 1
                continue
            if pac["modo"] == "secao":
                corpo = self.secao(pac)
            elif os.path.exists(pac["saida"]):
                corpo = open(pac["saida"], encoding="utf-8").read().strip()
            else:
                print(f"  … {nome}: tradução pendente ({os.path.basename(pac['saida'])})")
                st["pendente"] += 1
                continue
            corpo = self.religa(corpo, tmap, dmap)
            erros_g, avisos = self.gates(pac, corpo, tmap, dmap)
            base = f"/api/v3/workspaces/{self.pj.ws}/docs/{d['did']}/pages/{d['pid']}"
            atual = must_get(f"{base}?content_format=text%2Fmd").get("content") or ""
            final = self.cabecalho(pac, atual) + "\n\n---\n\n" + corpo
            r = {"nn": pac["nn"], "doc": pac["dst_nome"], "did": d["did"], "erros": erros_g, "avisos": avisos}
            if erros_g:
                print(f"  ✗ {nome}")
                for x in erros_g:
                    print(f"      - {x}")
                st["reprovado"] += 1
                rel.append(r)
                continue
            if tokens(atual) == tokens(final):
                st["ja_ok"] += 1
                r["resultado"] = "já gravado"
                rel.append(r)
                continue
            if not self.eh_cabecalho_engine(atual):
                if norm_ascii(marca) in norm_ascii(comum.unesc(atual)) and force:
                    pass
                else:
                    print(f"  ! {nome}: página já tem conteúdo que não é o cabeçalho do engine — não sobrescrevo"
                          f"{' (use --force se for desta tradução)' if norm_ascii(marca) in norm_ascii(comum.unesc(atual)) else ''}")
                    st["pulado"] += 1
                    r["resultado"] = "pulado (página editada)"
                    rel.append(r)
                    continue
            print(f"  ✓ {nome}  ({len(final)} chars){'  · ' + '; '.join(avisos) if avisos else ''}")
            if apply:
                ok, msg = self.gravar(d["did"], d["pid"], final)
                r["resultado"] = msg
                if ok:
                    st["gravado"] += 1
                else:
                    st["erro"] += 1
                    print(f"      ! {msg}")
            rel.append(r)
        comum.save_json(os.path.join(self.pasta, "relatorio_aplicar.json"), rel)
        print("\n==== RESUMO ====")
        print(json.dumps(st, ensure_ascii=False))
        if not apply:
            print("[DRY-RUN] rode com --apply para gravar")

    def checar(self, only):
        """Gates locais (sem ClickUp): para o tradutor conferir o próprio arquivo antes de entregar."""
        ruins = 0
        for pac in self.carregar(only):
            if pac["modo"] == "secao":
                continue
            if not os.path.exists(pac["saida"]):
                print(f"  … {pac['nn']} pendente")
                continue
            corpo = open(pac["saida"], encoding="utf-8").read().strip()
            erros, avisos = self.gates(pac, corpo, {}, {})
            print(f"  {'✓' if not erros else '✗'} {pac['nn']} {pac['dst_nome'][:60]}  ({len(corpo)} chars, razão "
                  f"{len(corpo) / max(1, len(pac['conteudo_origem'])):.2f})")
            for x in erros:
                print(f"      - {x}")
            for x in avisos:
                print(f"      · {x}")
            ruins += bool(erros)
        sys.exit(1 if ruins else 0)

    def verificar(self):
        ents, erros = self.pj.resolver()
        if erros:
            sys.exit("!! resolvedor com erros: " + "; ".join(erros))
        dmap, _, erros = self.pj.mapa_docs(ents)
        tmap = self.pj.tmap(ents)
        marca = self.t.get("marcador") or self.t["briefing"][:40]
        ruins = 0
        for pac in self.carregar(None):
            d = dmap.get(pac["src_did"])
            if not d:
                print(f"  ✗ {pac['nn']} sem Doc de destino")
                ruins += 1
                continue
            atual = must_get(f"/api/v3/workspaces/{self.pj.ws}/docs/{d['did']}/pages/{d['pid']}?content_format=text%2Fmd").get("content") or ""
            probs = []
            if pac["modo"] != "secao" and norm_ascii(marca) not in norm_ascii(comum.unesc(atual)):
                probs.append("sem marcador")
            if pac["src_url"] not in comum.unesc(atual):
                probs.append("sem Referência")
            corpo = self.secao(pac) if pac["modo"] == "secao" else (
                open(pac["saida"], encoding="utf-8").read().strip() if os.path.exists(pac["saida"]) else None)
            if corpo is None:
                probs.append("tradução local ausente")
            else:
                final = self.cabecalho(pac, atual) + "\n\n---\n\n" + self.religa(corpo, tmap, dmap)
                if tokens(final) != tokens(atual):
                    probs.append("página diferente do esperado (cabeçalho + tradução local)")
            print(f"  {'✓' if not probs else '✗'} {pac['nn']} {pac['dst_nome'][:64]} {'; '.join(probs)}")
            ruins += bool(probs)
        print(f"\nDocs com problema: {ruins}")
        sys.exit(1 if ruins else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("modo", choices=["pacotes", "checar", "aplicar", "verificar"])
    comum.args_comuns(ap)
    ap.add_argument("--only", help="NN separados por vírgula")
    ap.add_argument("--force", action="store_true", help="regrava página que já tem esta tradução")
    a = ap.parse_args()
    pj = comum.Projeto(a.config, a.plan or comum.plano_padrao(a.config))
    tr = Trad(pj)
    if a.modo == "pacotes":
        tr.pacotes()
    elif a.modo == "checar":
        tr.checar(set(a.only.split(",")) if a.only else None)
    elif a.modo == "aplicar":
        tr.aplicar(set(a.only.split(",")) if a.only else None, a.apply, a.force)
    else:
        tr.verificar()


if __name__ == "__main__":
    main()
