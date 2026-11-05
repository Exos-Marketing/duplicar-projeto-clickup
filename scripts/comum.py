#!/usr/bin/env python3
"""
comum.py — base dos scripts pós-duplicação da skill duplicar-projeto-clickup
(acabamento, recriar_dependencias, remapear_descricoes, traduzir_docs, duplicar_seguro).

- Token: CLICKUP_TOKEN do ambiente ou Keychain (serviço clickup-exos-api). Nunca é impresso.
- api(): pausa curta entre chamadas, retry em 429 (respeita X-RateLimit-Reset) e em erro de rede.
  POST de CRIAÇÃO usa create=True: em 429/timeout NÃO repete às cegas — devolve (429|0,
  "retry-needed") para quem chamou rechecar pelo nome antes de tentar de novo (o POST pode ter
  dado certo no servidor; repetir duplicaria task/Doc, e Doc não se apaga pela API).
- Projeto: carrega config + plano do engine e resolve ORIGEM -> DESTINO (card, marcos e
  atividades) pelo new_name na lista destino. Duplicata vira erro, nunca uma escolha calada.
"""
import json, os, re, subprocess, sys, time, unicodedata, importlib.util, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BRT = timezone(timedelta(hours=-3))
WS_PADRAO = "9013012202"
PAUSA = 0.25

_TOKEN = None


def token():
    global _TOKEN
    if _TOKEN:
        return _TOKEN
    t = os.environ.get("CLICKUP_TOKEN", "").strip()
    if not t:
        t = subprocess.run(["security", "find-generic-password", "-s", "clickup-exos-api", "-w"],
                           capture_output=True, text=True).stdout.strip()
    if not t:
        sys.exit("ERRO: token do ClickUp ausente (CLICKUP_TOKEN ou Keychain clickup-exos-api)")
    _TOKEN = t
    return t


def _safe(s):
    try:
        return json.loads(s)
    except Exception:
        return s


def api(method, path, body=None, tries=8, create=False):
    """-> (status, corpo). create=True: 429/timeout devolvem 'retry-needed' sem repetir."""
    data = json.dumps(body).encode() if body is not None else None
    for a in range(tries):
        req = urllib.request.Request("https://api.clickup.com" + path, data=data, method=method)
        req.add_header("Authorization", token())
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                t = r.read().decode()
                if method != "GET":
                    time.sleep(PAUSA)
                return r.status, (json.loads(t) if t.strip() else {})
        except urllib.error.HTTPError as e:
            if e.code == 429:
                if create:
                    return 429, "retry-needed"
                reset = e.headers.get("X-RateLimit-Reset")
                wait = (int(reset) - int(time.time()) + 1) if (reset or "").isdigit() else 5 * (a + 1)
                time.sleep(max(2, min(65, wait)))
                continue
            if e.code in (500, 502, 503, 504) and not create and a < tries - 1:
                time.sleep(3 * (a + 1))
                continue
            return e.code, _safe(e.read().decode())
        except Exception:
            if create:
                return 0, "retry-needed"
            time.sleep(3)
            continue
    return 0, "retry"


def get(path):
    c, b = api("GET", path)
    return b if c == 200 and isinstance(b, (dict, list)) else None


def must_get(path):
    b = get(path)
    if b is None:
        raise RuntimeError(f"GET falhou: {path}")
    return b


def get_task(tid, md=False):
    return must_get(f"/api/v2/task/{tid}" + ("?include_markdown_description=true" if md else ""))


# ---------------------------------------------------------------- texto / datas
def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def clean(n):
    """Nome comparável: NFC + espaços colapsados (o ClickUp guarda 'á' composto; o plano pode
    vir decomposto)."""
    return re.sub(r"\s+", " ", nfc(n).strip())


def norm_ascii(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def due_ms(d):
    """'AAAA-MM-DD' -> ms ao meio-dia BRT (o ClickUp regrava só-data às 04:00 BRT; comparar o dia)."""
    y, m, dd = map(int, d.split("-"))
    return int(datetime(y, m, dd, 12, 0, tzinfo=BRT).timestamp() * 1000)


def day_of(ms):
    return datetime.fromtimestamp(int(ms) / 1000, BRT).strftime("%Y-%m-%d") if ms else None


def t_url(tid):
    return f"https://app.clickup.com/t/{tid}"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


ESC_RE = re.compile(r"\\([\[\]_.*~`>#+\-!|(){}])")


def unesc(s):
    return ESC_RE.sub(r"\1", s or "")


def esc_colchetes(s):
    return s.replace("[", "\\[").replace("]", "\\]")


# ---------------------------------------------------------------- engine (funções puras reaproveitadas)
def engine():
    spec = importlib.util.spec_from_file_location("duplicar_projeto", os.path.join(HERE, "duplicar_projeto.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.TOKEN = token()
    return mod


_tipos = {}


def tipo_id(ws, nome):
    """custom_item_id pelo NOME do tipo no workspace (ex.: 'Copy' -> 1041)."""
    if ws not in _tipos:
        b = must_get(f"/api/v2/team/{ws}/custom_item")
        _tipos[ws] = {(it.get("name") or "").strip().lower(): it["id"] for it in b.get("custom_items") or []}
    return _tipos[ws].get((nome or "").strip().lower())


# ---------------------------------------------------------------- projeto (config + plano + resolvedor)
class Projeto:
    def __init__(self, config_path, plan_path):
        self.cfg = load_json(config_path)
        self.plan = load_json(plan_path)
        pc = self.plan.get("config") or {}
        # o plano carrega a config usada no discover; o arquivo de config manda nos blocos novos
        self.ws = str((self.cfg.get("target") or {}).get("workspace") or self.cfg.get("workspace") or WS_PADRAO)
        self.src_ws = str((self.cfg.get("source") or {}).get("workspace") or self.cfg.get("workspace") or WS_PADRAO)
        self.suf = self.cfg["target"]["suffix"]
        self.src_suf = self.cfg["source"]["suffix"]
        self.swaps = self.cfg.get("name_swaps") or pc.get("name_swaps") or []
        self.exp = self.cfg.get("expert_swap") or {}
        self.card_dst = self.cfg["target"]["card_id"]
        self.card_src = (self.cfg.get("source") or {}).get("card_id")
        self.acab = self.cfg.get("acabamento") or {}
        self.reaproveitados = set(self.acab.get("reaproveitados") or [])
        self.desde = self.acab.get("indice_desde")
        self._idx = {}
        self.eng = engine()

    # -- índice das listas destino (só nomes com o sufixo do destino; GET falhou -> exceção)
    def index_list(self, lid, force=False):
        if lid in self._idx and not force:
            return self._idx[lid]
        corte = int(datetime.fromisoformat(self.desde).replace(tzinfo=BRT).timestamp() * 1000) if self.desde else 0
        found, page, rev = {}, 0, ""
        while True:
            b = must_get(f"/api/v2/list/{lid}/task?archived=false&include_closed=true&subtasks=true"
                         f"&order_by=created{rev}&page={page}")
            tasks = b.get("tasks", [])
            if page == 0 and len(tasks) > 1 and not rev and \
                    int(tasks[0]["date_created"]) < int(tasks[-1]["date_created"]):
                rev = "&reverse=true"
                continue
            for t in tasks:
                if self.suf in nfc(t.get("name")):
                    found.setdefault(clean(t["name"]), []).append(t["id"])
            oldest = min([int(t.get("date_created") or 0) for t in tasks] or [0])
            if b.get("last_page", True) or not tasks or page > 60 or (corte and oldest < corte):
                break
            page += 1
        self._idx[lid] = found
        return found

    def find(self, lid, name, force=False):
        return list(self.index_list(lid, force).get(clean(name), []))

    def resolver(self, incluir_card=True):
        """-> (entradas, erros). entrada: {kind, src_id, dst_id, name, list, obj, marco_src, reap}."""
        ents, erros = [], []
        if incluir_card and self.card_src:
            ents.append({"kind": "card", "src_id": self.card_src, "dst_id": self.card_dst, "name": "(card)",
                         "list": None, "obj": {}, "marco_src": None, "reap": self.card_dst in self.reaproveitados})
        for m in self.plan["marcos"]:
            ids = self.find(m["dst_list"], m["new_name"])
            if len(ids) != 1:
                erros.append(f"marco {m['new_name']}: {ids or 'não encontrado'}")
                mid = None
            else:
                mid = ids[0]
                ents.append({"kind": "marco", "src_id": m["src_id"], "dst_id": mid, "name": clean(m["new_name"]),
                             "list": m["dst_list"], "obj": m, "marco_src": None, "reap": mid in self.reaproveitados})
            for a in m["activities"]:
                lid = a.get("dst_list") or a.get("src_list")
                ids = self.find(lid, a["new_name"])
                if len(ids) != 1:
                    erros.append(f"ativ {a['new_name']}: {ids or 'não encontrada'}")
                    continue
                ents.append({"kind": "ativ", "src_id": a["src_id"], "dst_id": ids[0], "name": clean(a["new_name"]),
                             "list": lid, "obj": a, "marco_src": m["src_id"], "marco_dst": mid,
                             "reap": ids[0] in self.reaproveitados})
        return ents, erros

    def tmap(self, ents):
        return {e["src_id"]: e["dst_id"] for e in ents}

    # -- Docs
    def docs_de(self, tid, ws=None):
        b = must_get(f"/api/v3/workspaces/{ws or self.ws}/docs?parent_id={tid}&parent_type=1")
        out = []
        for d in b.get("docs") or []:
            if d.get("deleted"):
                continue
            pg = must_get(f"/api/v3/workspaces/{ws or self.ws}/docs/{d['id']}/pages")
            pid = pg[0]["id"] if isinstance(pg, list) and pg else None
            out.append({"did": d["id"], "pid": pid, "name": clean(d.get("name")),
                        "url": f"https://app.clickup.com/{ws or self.ws}/docs/{d['id']}/{pid}"})
        return out

    def doc_alvo(self, nome_origem):
        return clean(self.eng.doc_ref_name(nome_origem or "", self.src_suf, self.suf, self.exp, self.swaps))

    def mapa_docs(self, ents):
        """-> (dmap {did_origem: doc_destino+meta}, por_task {dst_id: [docs]}, erros)."""
        dmap, por_task, erros = {}, {}, []
        for e in ents:
            if e["kind"] == "card":
                continue
            ds = self.docs_de(e["dst_id"])
            por_task[e["dst_id"]] = ds
            nomes = [d["name"] for d in ds]
            dups = sorted({n for n in nomes if nomes.count(n) > 1})
            if dups:
                erros.append(f"Doc duplicado em {e['name']}: {dups}")
            for rd in e["obj"].get("ref_docs") or []:
                did_src = rd["url"].split("/docs/")[1].split("/")[0]
                alvo = self.doc_alvo(rd.get("name"))
                par = [d for d in ds if d["name"] == alvo]
                if len(par) != 1:
                    erros.append(f"Doc sem par em {e['name']}: {alvo} -> {len(par)}")
                    continue
                dmap[did_src] = dict(par[0], src_did=did_src, src_url=rd["url"], src_name=clean(rd.get("name")),
                                     task_src=e["src_id"], task_dst=e["dst_id"], task_name=e["name"], kind=e["kind"])
        return dmap, por_task, erros


def plano_padrao(cfg_path):
    return cfg_path.replace("config_", "plano_")


def args_comuns(ap):
    ap.add_argument("--config", required=True, help="config_<projeto>.json")
    ap.add_argument("--plan", help="plano_<projeto>.json (default: troca config_ por plano_)")
    ap.add_argument("--apply", action="store_true", help="escreve (sem isso: dry-run)")
    return ap
