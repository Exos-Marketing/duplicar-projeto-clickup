# duplicar-projeto-clickup

> Skill para [Claude Code](https://claude.com/claude-code) que replica projetos no ClickUp da Exos — recria marcos (milestones), atividades linkadas, campos personalizados, checklists nativos e Docs de referência, do zero ao projeto completo via engine API-first.

[![Skill: Claude Code](https://img.shields.io/badge/Skill-Claude%20Code-cc785c.svg)](https://claude.com/claude-code)
[![Platform: ClickUp](https://img.shields.io/badge/Platform-ClickUp-7B68EE.svg)](https://clickup.com)

## O que faz

Um gestor de projetos sênior especializado na duplicação e criação de lançamentos, perpétuos e reuniões secretas no ClickUp da Exos. A skill:

- **Descobre a origem dinamicamente** — lê a estrutura real do projeto-origem via API e gera um plano editável (sem assumir nada)
- **Recria marcos (milestones)** — nas listas de fase corretas, com campos personalizados, vínculo ao card do painel e prioridade
- **Recria atividades** — nas listas de processo do Marketing (Copy / Design / Tráfego / Automações / Infra), com campos, checklists nativos, prioridade e link pro marco
- **Cria Docs nativos** — um Doc por Doc da origem, nomeado pelo Doc original (sufixo trocado), com link de referência pro Doc anterior
- **Troca expert/cliente** — nas descrições e nos campos personalizados (ex.: Elen Tolentino → Kleber Meireles)
- **Suporta cross-workspace** — replica de um workspace para outro (ex.: Exos → workspace do cliente)
- **Cria a pasta no Google Drive** — estrutura-modelo de subpastas no Drive compartilhado do cliente após o projeto estar no ClickUp, ou espelho da árvore de um projeto que já adaptou o modelo (`espelhar_drive.py`)
- **Normaliza o tipo da atividade pelo nome** — "Copy …" vira tipo Copy e "Criativo(s) …" vira tipo Criativo
- **Faz o acabamento pós-duplicação** — campos da origem task a task, etiquetas, responsáveis e datas por regra, dependências, descrições remontadas e versão em outro idioma dos Docs
- **Padroniza o Planejamento de Tráfego** — nomes de campanha `[PGL][SUFIXO][FASE]`, conjuntos, UTM e tasks de campanha, com o conferidor `checar_trafego.py` (só leitura)
- **É idempotente** — pula o que já existe pelo nome; dry-run por padrão antes de escrever qualquer coisa

## Nomenclatura dos projetos

```
[SIGLA_CLIENTE][TIPO][PRODUTO][MÊS][ANO]
Ex.: [KM][PEP][APB][26] · [LL][RS][POS][MAI][26] · [DM][LB][POS][JUL][26]
```

Tipos: `RS` (Reunião Secreta) · `LM` (Lançamento Meteórico) · `LB` (Lançamento Base) · `PEP` (Perpétuo) · `EP` (Evento Presencial)

## Fluxo de uso

```
1. Informar origem + cliente + tipo + produto + mês + ano
2. Skill monta o config e roda discover (read-only → plano.json)
3. Revisar/editar o plano se necessário
4. Dry-run: skill mostra o que será criado — confirmar
5. Execute --apply: cria tudo no ClickUp
6. Criar pasta no Google Drive (passo final)
7. Acabamento, quando o projeto pede: campos, dependências, descrições e idioma (seção "Versão em outro idioma" do SKILL.md)
```

## Comandos do engine

```bash
TOKEN=$(security find-generic-password -s clickup-exos-api -w)
SK=~/.claude/skills/duplicar-projeto-clickup/scripts

# 1) Descoberta (read-only)
CLICKUP_TOKEN=$TOKEN python3 $SK/duplicar_projeto.py discover \
  --config config_<projeto>.json --out plano_<projeto>.json

# 2) Dry-run (não escreve nada)
CLICKUP_TOKEN=$TOKEN python3 $SK/duplicar_projeto.py execute \
  --plan plano_<projeto>.json

# 3) Aplicar
CLICKUP_TOKEN=$TOKEN python3 $SK/duplicar_projeto.py execute \
  --plan plano_<projeto>.json --apply

# 4) Recriar só os Docs
CLICKUP_TOKEN=$TOKEN python3 $SK/duplicar_projeto.py execute \
  --plan plano_<projeto>.json --apply --docs-only
```

O token vem do **Keychain macOS** (serviço `clickup-exos-api`) — nunca é hard-coded.

`duplicar_seguro.py` aceita os mesmos argumentos do engine e acrescenta duas proteções contra duplicata: para se uma página da lista falhar e, em 429/timeout, confere de novo pelo nome antes de repetir um POST de criação.

## Estrutura do repositório

```
duplicar-projeto-clickup/
├── SKILL.md                        # Ponto de entrada (Claude Code lê este arquivo)
├── README.md                       # Este arquivo
├── REFERENCE.md                    # IDs de listas/fases, painéis, custom fields e siglas
├── DRIVE.md                        # Estrutura de pastas no Google Drive por cliente
├── TRAFEGO.md                      # Planejamento de Tráfego: nomes de campanha, conjuntos, UTM e tasks
├── transcricoes/                   # Áudios do gestor transcritos (fonte das regras)
└── scripts/
    ├── duplicar_projeto.py         # Engine API-first (discover + execute)
    ├── duplicar_seguro.py          # Roda o engine com as duas proteções contra duplicata
    ├── comum.py                    # Base dos scripts pós-duplicação (API e resolvedor origem → destino)
    ├── acabamento.py               # Campos, etiquetas, responsáveis e datas por regra
    ├── recriar_dependencias.py     # Recria no destino as dependências (waiting_on) da origem
    ├── remapear_descricoes.py      # Remonta a descrição das tasks novas a partir da origem
    ├── traduzir_docs.py            # Versão em outro idioma dos Docs do projeto duplicado
    ├── espelhar_drive.py           # Espelha a árvore de pastas do projeto no Drive (só pastas)
    ├── checar_trafego.py           # Confere a nomenclatura das campanhas de tráfego (só leitura)
    ├── clickup_fix_doc_titles.py   # Utilitário: renomeia páginas de Docs após rename de tasks
    ├── config_km_apb.json          # Config exemplo — mesmo workspace (Exos)
    └── config_tsap_mba.json        # Config exemplo — cross-workspace (Exos → Telesapiens)
```

## Instalação

```bash
# Clonar o repositório direto na pasta de skills do Claude Code
git clone https://github.com/Exos-Marketing/duplicar-projeto-clickup.git \
  ~/.claude/skills/duplicar-projeto-clickup
```

Depois mencione qualquer tarefa de duplicação no Claude Code:

```
> Duplica o projeto da Elen Tolentino de março para a Daniela Moleiro em julho
> Replica o lançamento RS POS para o perpétuo do Kleber
> Cria o projeto da Daniela Moleiro — Lançamento Base POS JUL/26
```

A skill ativa automaticamente quando detecta a tarefa, ou pode ser invocada com `/duplicar-projeto-clickup`.

## Capacidades do engine

| Recurso | API usada |
|---|---|
| Criar task / milestone | `POST /v2/list/{id}/task` |
| Setar custom field | `POST /v2/task/{id}/field/{fid}` |
| Linkar tasks | `POST /v2/task/{id}/link/{links_to}` |
| Checklist nativo | `POST /v2/task/{id}/checklist` + items |
| Criar Doc na task | `POST /v3/workspaces/{ws}/docs` (`parent: {id, type:1}`) |
| Criar página no Doc | `POST /v3/.../docs/{docId}/pages` |
| Renomear página | `PUT /v3/.../docs/{docId}/pages/{pageId}` |
| Listar Docs da task | `GET /v3/workspaces/{ws}/docs?parent_id=&parent_type=1` |

## Requisitos

- [Claude Code](https://claude.com/claude-code) (CLI, desktop ou extensão de IDE)
- Token da API do ClickUp guardado no Keychain macOS: `clickup-exos-api`
- Python 3.9+ (os scripts só usam a biblioteca padrão)
- Acesso ao workspace ClickUp da Exos (`9013012202`)
- rclone com o remote `gdrive` (conta `drive@exosmkt.com`), só para `espelhar_drive.py`

Nenhuma credencial mora neste repo.

## Maintainer

Desenvolvida pela [Exos Marketing Digital](https://exosmkt.com.br) para uso interno nas operações de lançamento.
