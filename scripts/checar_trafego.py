#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
checar_trafego.py — confere a nomenclatura das campanhas de tráfego de um projeto Exos
(padrão do Gabriel, 23/10/26 + dash.exosmkt.com/convencoes). READ-ONLY: não escreve no ClickUp.

Uso (token: CLICKUP_TOKEN no ambiente ou Keychain `clickup-exos-api`):
  python3 checar_trafego.py --marco 17tqamemrqn                  # marco "Planejamento de Trafego [..]"
  python3 checar_trafego.py --marco 17tqamemrqn --campanhas      # + as tasks de campanha linkadas ao marco
  python3 checar_trafego.py --sufixo "[DM][BF][POS][NOV][26]"    # acha o marco pelo nome (lista Concepção; --lista p/ outra)
  python3 checar_trafego.py --texto plano.txt --sufixo "[DM][BF][POS][NOV][26]"   # confere um texto local, sem API
Sai com 1 se houver ERRO; AVISO não falha. Regras em ../TRAFEGO.md.
"""
import argparse, json, os, re, subprocess, sys, unicodedata, urllib.parse, urllib.request

API = "https://api.clickup.com/api/v2"
LISTA_CONCEPCAO_LANC = "901302376636"

# marcadores canônicos (Gabriel, 23/10/26) -> fase
CANON = {"ANTECIPACAO": "antecipação", "CADASTROS": "captação", "RECONHECIMENTO": "contagem regressiva",
         "EVENTO": "evento", "AULA": "evento", "VENDAS": "vendas", "CARRINHO": "carrinho", "DOWNSELL": "downsell",
         "PESQUISA": "pesquisa", "REABERTURA": "recuperação", "RECUPERACAO": "recuperação"}
# sinônimos que o dash ainda lê (legado) -> marcador canônico sugerido
LEGADO = {"CADASTRO": "CADASTROS", "CAPTACAO": "CADASTROS", "CAP": "CADASTROS",
          "VENDAS DO EVENTO": "VENDAS", "OFERTA": "VENDAS", "AO VIVO": "EVENTO"}
SUBMARCADOR = {"TESTE"}
VARIANTE = {"ESTATICOS", "ESTATICO", "VIDEO", "VIDEOS", "IMAGENS", "IMAGEM", "CARROSSEL"}
QUENTE = (r"\bquente\b", r"\bremarketing\b", r"\brmkt\b", r"\bretarget\w*")
FRIO = (r"\bfrio\b", r"\blookalike\b", r"\blal\b", r"\binteresses?\b", r"\badvantage\b", r"\baberto\b")
ADSET_RE = re.compile(r"^(\d{2}\s*-\s*)?\[(IG/FB|FB/IG|IG|FB)\]\s*\[[^\]]+\]\s*\[[^\]]+\]\s*\S")
ADSET_LIKE = re.compile(r"^(\d{2}\s*-\s*\[|\[(IG|FB)\b)")
ID_RE = re.compile(r"^[a-z0-9]{7,12}$")


def fold(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").upper().strip()


def token():
    t = os.environ.get("CLICKUP_TOKEN")
    if t:
        return t
    try:
        return subprocess.check_output(["security", "find-generic-password", "-s", "clickup-exos-api", "-w"]).decode().strip()
    except Exception:
        sys.exit("ERRO: defina CLICKUP_TOKEN ou grave o token no Keychain (clickup-exos-api)")


def api(path, params=None):
    url = API + path + ("?" + urllib.parse.urlencode(params, doseq=True) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": token()})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def get_task(tid):
    return api("/task/%s" % tid, {"include_markdown_description": "true"})


def unescape_md(s):
    s = re.sub(r"\\([\[\]_.*#()\-+!|>~`])", r"\1", s or "")
    return s.replace("**", "")


def sufixo_do_nome(nome):
    m = re.search(r"((?:\[[^\[\]]+\])+)\s*$", (nome or "").strip())
    return m.group(1) if m else None


def blocos(s):
    """Blocos [..] do início, texto livre e blocos [..] do fim."""
    s = s.strip()
    m = re.match(r"^((?:\[[^\[\]]+\]\s*)+)(.*)$", s)
    if not m:
        return [], s, []
    lead = re.findall(r"\[([^\[\]]+)\]", m.group(1))
    rest = m.group(2).strip()
    m2 = re.search(r"((?:\s*\[[^\[\]]+\])+)\s*$", rest)
    trail = re.findall(r"\[([^\[\]]+)\]", m2.group(1)) if m2 else []
    free = rest[: m2.start()].strip() if m2 else rest
    return lead, free, trail


def eh_campanha(line, prefixo, sufixo):
    l = line.strip()
    if not l.startswith("[") or ADSET_RE.match(l) or ADSET_LIKE.match(l):
        return False
    if "negativar" in l.lower():
        return False
    ln, sn = l.replace(" ", ""), sufixo.replace(" ", "")
    if fold(l).startswith("[" + fold(prefixo) + "]"):
        return True
    if ln.startswith(sn):                       # linha que COMEÇA pela tag: título do plano ("[TAG] — Nome") ou
        return ln[len(sn):].startswith("[")     # campanha sem o prefixo (vem outro bloco logo depois da tag)
    return sn in ln


def checar_campanha(line, prefixo, sufixo):
    erros, avisos = [], []
    lead, free, trail = blocos(line)
    if not lead:
        return ["linha não começa com blocos [..]"], []
    pref_ok = fold(lead[0]) == fold(prefixo)
    if not pref_ok:
        erros.append("1º bloco deve ser [%s] (prefixo da operação de tráfego); veio [%s]" % (prefixo, lead[0]))
    suf = [fold(x) for x in re.findall(r"\[([^\[\]]+)\]", sufixo)]
    n = len(suf)
    pos = None
    for i in range(len(lead) - n + 1):
        if [fold(x) for x in lead[i:i + n]] == suf:
            pos = i
            break
    if pos is None:
        erros.append("tag do projeto %s não aparece contígua (nada pode ficar entre o código da expert e o ano; "
                     "tag de outro projeto também é erro)" % sufixo)
        return erros, avisos
    antes = lead[(1 if pref_ok else 0):pos]
    depois = lead[pos + n:]
    fases, teste, desconhecidos, legados = [], False, [], []
    for onde, grupo in (("antes", antes), ("depois", depois)):
        for b in grupo:
            f = fold(b)
            if f in CANON:
                fases.append((f, onde, grupo.index(b)))
            elif f in LEGADO:
                fases.append((LEGADO[f], onde, grupo.index(b)))
                legados.append((b, LEGADO[f]))
            elif f in SUBMARCADOR:
                teste = True
            elif f in VARIANTE:
                pass
            else:
                desconhecidos.append(b)
    for b in trail:
        if fold(b) not in VARIANTE:
            avisos.append("bloco final [%s] não é variante conhecida (%s)" % (b, " / ".join(sorted(VARIANTE))))
    for b in desconhecidos:
        erros.append("bloco [%s] não é marcador de fase da tabela (marcador composto/inventado? use o marcador puro "
                     "e descreva no texto livre)" % b)
    for b, sug in legados:
        avisos.append("[%s] é sinônimo legado que o dash ainda lê — padrão novo é [%s]" % (b, sug))
    distintas = sorted({CANON[f] for f, _, _ in fases})
    if not fases:
        if teste:
            erros.append("[TESTE] sozinho não é fase — teste de criativo é captação: use [CADASTROS][TESTE]")
        else:
            erros.append("sem marcador de fase logo após o ano ([ANTECIPAÇÃO] [CADASTROS] [RECONHECIMENTO] [EVENTO]/[AULA] "
                         "[VENDAS] [CARRINHO] [DOWNSELL] [PESQUISA] [REABERTURA])")
    elif len(distintas) > 1:
        erros.append("dois marcadores de fases diferentes (%s) anulam a leitura — um por campanha" % ", ".join(distintas))
    else:
        f, onde, idx = fases[0]
        fase = CANON[f]
        if onde == "antes":
            avisos.append("marcador antes do código do cliente (formato antigo, o dash aceita) — padrão novo: logo depois do ano")
        elif idx != 0:
            avisos.append("marcador de fase deve vir logo depois do ano (veio depois de outro bloco)")
        if fase == "contagem regressiva" and "CONTAGEM REGRESSIVA" not in fold(free):
            erros.append("[RECONHECIMENTO] sozinho não é fase (é objetivo de mídia): a contagem regressiva precisa da frase "
                         "CONTAGEM REGRESSIVA no nome")
        if teste and fase != "captação":
            erros.append("[TESTE] só acompanha [CADASTROS]")
        ff = free.lower()
        q = any(re.search(p, ff) for p in QUENTE) or (fase == "contagem regressiva" and "contagem regressiva" in ff)
        fr = any(re.search(p, ff) for p in FRIO) and "carrinho aberto" not in ff
        if q and fr:
            erros.append("Frio e Quente no mesmo nome = temperatura indefinida no dash — uma campanha por temperatura")
        elif fase in ("captação", "vendas") and not (q or fr):
            avisos.append("sem temperatura no texto livre (Frio / Quente / Lookalike / Remarketing) — o dash não "
                          "classifica quente × frio")
    if not free:
        avisos.append("sem texto livre depois dos marcadores")
    return erros, avisos


def checar_texto(texto, prefixo, sufixo, rotulo):
    """Confere campanhas, conjuntos e UTM de um texto. Devolve (n_camp, n_erro_camp, n_aviso_camp, conj_fora)."""
    texto = unescape_md(texto)
    linhas = []
    for raw in texto.splitlines():
        l = raw.strip()
        if fold(l).startswith("ATIVIDADES"):      # seção escrita pelo engine (links das tasks) — fora da conferência
            break
        linhas.append(l)
    n = ne = na = fora = 0
    for l in linhas:
        if not l:
            continue
        if eh_campanha(l, prefixo, sufixo):
            n += 1
            erros, avisos = checar_campanha(l, prefixo, sufixo)
            tag = "ERRO " if erros else ("AVISO" if avisos else "OK   ")
            print("  %s %s" % (tag, l))
            for e in erros:
                print("        - ERRO: %s" % e)
            for a in avisos:
                print("        - aviso: %s" % a)
            ne += bool(erros)
            na += bool(avisos and not erros)
        elif ADSET_LIKE.match(l) and "negativar" not in l.lower():
            if not ADSET_RE.match(l):
                fora += 1
                print("  AVISO conjunto fora do padrão `NN - [IG/FB] [M/H] [25-65+] Público`: %s" % l)
    if n == 0:
        print("  AVISO nenhuma linha de campanha [%s]%s… em %s%s" % (prefixo, sufixo, rotulo,
              " — cole o bloco da fase do marco na descrição (TRAFEGO.md §6)" if rotulo == "task" else ""))
    if "utm_" in texto:
        if "utm_content={{ad.name}}" not in texto:
            print("  AVISO parâmetros de URL sem utm_content={{ad.name}} (obrigatório p/ o ranking de criativos)")
        if re.search(r"utm_source=metaads\b", texto):
            print("  AVISO utm_source=metaads — a taxonomia é meta_ads (minúsculo, com underscore)")
        if re.search(r"utm_\w+=[^&\s]*\[", texto):
            print("  ERRO  tag de colchetes do lançamento dentro de UTM — ela é do SendFlow/GrowAI, nunca de UTM")
            ne += 1
    return n, ne, na, fora


def checar_nome_campanha_task(nome, tid, sufixo):
    """Nome da task de campanha: [ETAPA][SUFIXO][<id da própria task>] (ou 'Campanha de Antecipação [Meta]…')."""
    probs = []
    if sufixo.replace(" ", "") not in nome.replace(" ", ""):
        blocos_suf = [fold(x) for x in re.findall(r"\[([^\[\]]+)\]", sufixo)]
        blocos_nome = [fold(x) for x in re.findall(r"\[([^\[\]]+)\]", nome)]
        if all(b in blocos_nome for b in blocos_suf):
            probs.append("aviso: tag do projeto %s não contígua no nome da task (legado [Meta][ET][Fase 2][BF]…; não afeta o "
                         "dash, mas quebra busca por sufixo) — padrão: [ETAPA]%s[<id>]" % (sufixo, sufixo))
        else:
            probs.append("ERRO: nome da task sem a tag do projeto %s" % sufixo)
    m = re.search(r"\[([^\[\]]+)\]\s*$", nome)
    ult = m.group(1) if m else ""
    if ID_RE.match(ult) and ult != tid:
        probs.append("ERRO: o [ID] final (%s) não é o id da própria task (%s) — sobrou o id da origem" % (ult, tid))
    elif not ID_RE.match(ult) and not fold(nome).startswith("CAMPANHA DE"):
        probs.append("aviso: nome sem [<id da própria task>] no fim")
    return probs


def achar_marco(sufixo, lista):
    page, achados = 0, []
    while True:
        d = api("/list/%s/task" % lista, {"page": page, "include_closed": "true"})
        ts = d.get("tasks", [])
        for t in ts:
            nm = t.get("name", "")
            if "PLANEJAMENTO DE TR" in fold(nm) and sufixo.replace(" ", "") in nm.replace(" ", ""):
                achados.append(t)
        if d.get("last_page", True) or not ts:
            break
        page += 1
    if not achados:
        sys.exit("ERRO: nenhum marco 'Planejamento de Tráfego %s' na lista %s" % (sufixo, lista))
    exato = [t for t in achados if fold(t["name"]).replace("TRAFEGO", "") .strip() == ("PLANEJAMENTO DE " + fold(sufixo)).strip()]
    t = (exato or achados)[0]
    if len(achados) > 1:
        print("! %d marcos casam; usando %s (%s)" % (len(achados), t["name"], t["id"]))
    return t["id"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--marco", help="id do marco Planejamento de Tráfego")
    ap.add_argument("--sufixo", help='tag do projeto, ex. "[DM][BF][POS][NOV][26]" (obrigatório com --texto)')
    ap.add_argument("--lista", default=LISTA_CONCEPCAO_LANC, help="lista onde procurar o marco com --sufixo (default: Concepção de lançamentos)")
    ap.add_argument("--campanhas", action="store_true", help="confere também as tasks de campanha linkadas ao marco")
    ap.add_argument("--texto", help="arquivo de texto local para conferir (sem API)")
    ap.add_argument("--prefixo", default="PGL", help="prefixo da operação de tráfego (default PGL)")
    a = ap.parse_args()
    tot = {"camp": 0, "erro": 0, "aviso": 0, "conj": 0, "tasks_erro": 0}

    if a.texto:
        if not a.sufixo:
            sys.exit("ERRO: --texto exige --sufixo")
        print("== Texto local %s — tag %s" % (a.texto, a.sufixo))
        n, ne, na, fora = checar_texto(open(a.texto, encoding="utf-8").read(), a.prefixo, a.sufixo, a.texto)
        tot.update(camp=n, erro=ne, aviso=na, conj=fora)
    else:
        mid = a.marco or achar_marco(a.sufixo, a.lista)
        t = get_task(mid)
        sufixo = a.sufixo or sufixo_do_nome(t["name"])
        if not sufixo:
            sys.exit("ERRO: não achei a tag [..] no nome do marco; passe --sufixo")
        print("== Marco: %s (%s) — tag %s" % (t["name"], mid, sufixo))
        n, ne, na, fora = checar_texto(t.get("markdown_description") or t.get("description") or "", a.prefixo, sufixo, "marco")
        tot["camp"] += n; tot["erro"] += ne; tot["aviso"] += na; tot["conj"] += fora
        if a.campanhas:
            ids = [l["link_id"] if l.get("task_id") == mid else l.get("task_id") for l in t.get("linked_tasks") or []]
            for cid in ids:
                c = get_task(cid)
                print("\n== Campanha: %s (%s) — status %s" % (c["name"], cid, (c.get("status") or {}).get("status")))
                for p in checar_nome_campanha_task(c["name"], cid, sufixo):
                    print("  %s" % p)
                    if p.startswith("ERRO"):
                        tot["tasks_erro"] += 1
                n, ne, na, fora = checar_texto(c.get("markdown_description") or c.get("description") or "", a.prefixo, sufixo, "task")
                tot["camp"] += n; tot["erro"] += ne; tot["aviso"] += na; tot["conj"] += fora
    print("\nRESUMO: %d linhas de campanha · %d OK · %d com ERRO · %d só com aviso · conjuntos fora do padrão: %d · nomes de task com erro: %d"
          % (tot["camp"], tot["camp"] - tot["erro"] - tot["aviso"], tot["erro"], tot["aviso"], tot["conj"], tot["tasks_erro"]))
    sys.exit(1 if (tot["erro"] or tot["tasks_erro"]) else 0)


if __name__ == "__main__":
    main()
