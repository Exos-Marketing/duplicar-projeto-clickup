#!/usr/bin/env python3
"""
espelhar_drive.py — espelha a ÁRVORE DE PASTAS de um projeto no Google Drive para um projeto novo
(SÓ pastas, nunca arquivos). Útil quando o projeto de origem já adaptou a estrutura-modelo (ex.: a
pasta 14 do perpétuo com Upsell/Remarketing e Brutos/Editados): o destino nasce igual e os links de
pasta nas descrições do ClickUp remapeiam 1:1 pelo caminho relativo.

- Idempotente por nome (pasta que já existe é reaproveitada; nome repetido no mesmo pai = erro).
- --excluir NOME pula a pasta (e tudo dentro), comparando sem acento/caixa. Repetível.
- Grava --out com o mapa {caminho relativo -> id origem / id destino}, insumo do remapear_descricoes.py.
- Token: OAuth do rclone (remote gdrive, conta drive@exosmkt.com, organizer do Drive compartilhado),
  Drive API v3 (supportsAllDrives). Nunca imprime o token.

Uso:
  python3 espelhar_drive.py --origem <id> --destino-pai <id> --nome "[SIGLA][...]" --excluir "REGRAVAÇÃO" --out mapa.json
  ... --apply        # cria as pastas
  ... --verify       # relê o destino e compara com a origem
"""
import argparse, configparser, json, subprocess, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
from pathlib import Path

API = "https://www.googleapis.com/drive/v3"
FOLDER = "application/vnd.google-apps.folder"
_tok = [None]


def norm(s):
    s = unicodedata.normalize("NFKD", (s or "").strip())
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def nfc(s):
    return unicodedata.normalize("NFC", (s or "").strip())


def token(refresh=False):
    if _tok[0] and not refresh:
        return _tok[0]
    subprocess.run(["rclone", "lsd", "gdrive:", "-q", "--max-depth", "1"], capture_output=True, timeout=90)
    cp = configparser.RawConfigParser()
    cp.read(Path.home() / ".config" / "rclone" / "rclone.conf")
    _tok[0] = json.loads(cp["gdrive"]["token"])["access_token"]
    return _tok[0]


def call(method, path, params=None, body=None, tries=6):
    params = dict(params or {})
    params.setdefault("supportsAllDrives", "true")
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    data = json.dumps(body).encode() if body is not None else None
    for a in range(tries):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", "Bearer " + token())
        if data:
            req.add_header("Content-Type", "application/json; charset=UTF-8")
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            txt = e.read().decode()[:400]
            if e.code == 401 and a == 0:
                token(refresh=True)
                continue
            if (e.code in (429, 500, 502, 503) or (e.code == 403 and ("ateLimit" in txt or "quota" in txt.lower()))) \
                    and a < tries - 1:
                time.sleep(2 ** a + 0.5)
                continue
            raise RuntimeError(f"{method} {path} -> {e.code}: {txt}")
    raise RuntimeError(f"{method} {path}: tentativas esgotadas")


def pastas_filhas(pid):
    out, tok = [], None
    while True:
        p = {"q": f"'{pid}' in parents and mimeType = '{FOLDER}' and trashed = false",
             "fields": "nextPageToken, files(id,name)", "pageSize": 1000,
             "includeItemsFromAllDrives": "true", "corpora": "allDrives"}
        if tok:
            p["pageToken"] = tok
        r = call("GET", "/files", p)
        out += r.get("files", [])
        tok = r.get("nextPageToken")
        if not tok:
            return out


def arvore(pid, excluir, base=""):
    """-> [(caminho_relativo, id)] em pré-ordem (pai antes dos filhos)."""
    out = []
    for f in sorted(pastas_filhas(pid), key=lambda x: nfc(x["name"])):
        if norm(f["name"]) in excluir:
            continue
        cam = f"{base}/{nfc(f['name'])}" if base else nfc(f["name"])
        out.append((cam, f["id"]))
        out += arvore(f["id"], excluir, cam)
    return out


def filho(pid, nome):
    xs = [f for f in pastas_filhas(pid) if nfc(f["name"]) == nfc(nome)]
    if len(xs) > 1:
        raise RuntimeError(f"nome repetido em {pid}: {nome} -> {[x['id'] for x in xs]}")
    return xs[0]["id"] if xs else None


def criar(pid, nome):
    return call("POST", "/files", {"fields": "id,name"}, {"name": nome, "mimeType": FOLDER, "parents": [pid]})["id"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--origem", required=True)
    ap.add_argument("--destino-pai", required=True)
    ap.add_argument("--nome", required=True)
    ap.add_argument("--excluir", action="append", default=[])
    ap.add_argument("--out")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    excluir = {norm(x) for x in a.excluir}
    src = arvore(a.origem, excluir)
    print(f"origem: {len(src)} pasta(s) abaixo da raiz (excluídas: {sorted(a.excluir) or '-'})")

    raiz = filho(a.destino_pai, a.nome)
    if a.verify:
        if not raiz:
            sys.exit(f"!! pasta '{a.nome}' não existe no destino")
        dst = arvore(raiz, set())
        falta = sorted(set(c for c, _ in src) - set(c for c, _ in dst))
        sobra = sorted(set(c for c, _ in dst) - set(c for c, _ in src))
        print(f"destino: {len(dst)} pasta(s) · faltam {len(falta)} · a mais {len(sobra)}")
        for c in falta:
            print("   - falta: " + c)
        for c in sobra:
            print("   + a mais: " + c)
        print(f"url: https://drive.google.com/drive/folders/{raiz}")
        sys.exit(1 if falta else 0)

    criadas = 0
    if not raiz:
        print(f"  + {a.nome}  (raiz, em {a.destino_pai})")
        if a.apply:
            raiz = criar(a.destino_pai, a.nome)
            criadas += 1
    else:
        print(f"  = {a.nome}  ({raiz})")
    ids = {"": raiz}
    mapa = []
    for cam, sid in src:
        pai_cam, _, nome = cam.rpartition("/")
        pai = ids.get(pai_cam)
        did = filho(pai, nome) if pai else None
        if did:
            print(f"  = {cam}")
        else:
            print(f"  + {cam}")
            if a.apply and pai:
                did = criar(pai, nome)
                criadas += 1
        ids[cam] = did
        mapa.append({"caminho": cam, "origem": sid, "destino": did})
    print(f"\npastas criadas: {criadas}{'' if a.apply else ' (DRY-RUN — use --apply)'}")
    if raiz:
        print(f"url: https://drive.google.com/drive/folders/{raiz}")
    if a.out and a.apply:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump({"origem_raiz": a.origem, "destino_raiz": raiz, "nome": a.nome,
                       "url": f"https://drive.google.com/drive/folders/{raiz}", "pastas": mapa},
                      f, ensure_ascii=False, indent=1)
        print(f"mapa -> {a.out}")


if __name__ == "__main__":
    main()
