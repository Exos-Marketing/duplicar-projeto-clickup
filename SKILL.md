---
name: duplicar-projeto-clickup
description: Duplica/cria projetos no ClickUp da agência Exos a partir de um projeto-origem, de forma API-first com o engine duplicar_projeto.py — recria marcos (milestones), atividades (tasks linkadas), campos personalizados, checklists nativos, Docs de referência e prioridade, com a nomenclatura [SIGLA][TIPO][PRODUTO][MÊS][ANO] e a hierarquia Atividade→Marco→Projeto. Flexível: lê a origem dinamicamente e gera um plano editável (adaptável a novos formatos/eventos). Use quando o usuário pedir para duplicar, replicar ou criar um projeto/lançamento/perpétuo/reunião secreta/evento no ClickUp, ou disser "duplica o projeto de X pra Y", "novo lançamento", "replica o lançamento de fevereiro", "cria o projeto da Daniela", "monta o projeto a partir do modelo". Também replica ENTRE workspaces diferentes (ex.: da Agência EU para o workspace de um cliente) — gatilhos: "replica pra outro workspace", "monta esse projeto no workspace do cliente", "duplica pro workspace da Telesapiens", "leva esse lançamento pro workspace X".
---

# Duplicar / Criar Projeto no ClickUp (Exos)

Recria **marcos + atividades** (com **campos**, **checklists nativos**, **Docs de referência** e
**prioridade**) de um projeto-origem nas **listas de fase que já existem**. **NUNCA cria pasta/lista.**

**Arquitetura API-first (flexível).** A execução pesada é feita pelo engine **`duplicar_projeto.py`**
via **API REST** (rápido, determinístico e completo — inclui checklists e Docs que o MCP não cobre).
O **MCP `clickup`** é usado para **descoberta e confirmação conversacional**. Token no Keychain:
`TOKEN=$(security find-generic-password -s clickup-exos-api -w)` (nunca imprima o valor).

## Hierarquia (regra sagrada)
`Atividade → linkada ao → Marco → vinculado ao → Projeto`
- **Projeto** = card no painel (ex.: `Painel Projeto Perpétuos`/`Lançamentos`).
- **Marco** = task **Milestone** numa lista de fase (ex.: `Páginas [KM][PEP][APB][26]`).
- **Atividade** = task nas **listas de processo do Marketing** (Copy/Design/Tráfego/…), **linkada** ao marco.
- **Doc** = ClickUp Doc nativo na atividade (`parent type 1`), com link pro doc anterior de referência.

## Entradas (aceita 1 linha; pergunte o que faltar)
1. **Origem (SEMPRE indicar ou confirmar — nunca assumir)** — qual projeto replicar. Se não disser,
   proponha o mais completo do mesmo tipo e confirme. Em cross-type (lançamento→perpétuo) é obrigatório.
2. **Cliente** + sigla · **Tipo** (RS/LM/LB/PEP/EP) · **Produto** · **Mês** · **Ano** → sufixo
   `[SIGLA][TIPO][PRODUTO][MÊS][ANO]`. Siglas em [REFERENCE.md](REFERENCE.md).
3. **NÃO** peça datas nem responsáveis no início.

## Fluxo (2 fases: discover → execute)
1. **Descoberta + confirmação** (MCP, conversa): resolver a origem; montar identidade/sufixo.
2. **Config**: criar/editar `config_<projeto>.json` (base: `config_km_apb.json`) com `source` (sufixo
   + listas de fase), `target` (sufixo, card, tag, prioridade), `phase_map` (fase→lista destino + rel
   field), `fields` (Cliente/Produto/Idioma/Empresa + papéis), `expert_swap`, `docs`. IDs em REFERENCE.md.
3. **`discover`** (read-only) → gera `plano.json` (marcos, atividades, docs de referência, checklists).
   **Edite o plano** para adaptar a formatos novos — é o ponto de flexibilidade (modelo-base + ajuste).
4. **Dry-run** `execute --plan plano.json` → **mostre ao usuário** o que será criado. **Confirme.**
5. **`execute --plan plano.json --apply`** → cria card (se faltar), marcos (milestone, campos, vínculo
   ao card, checklist nativo, prioridade), atividades (na mesma lista de processo, campos, vínculo ao
   marco, checklist, prioridade, troca de expert→cliente, fix do `[ID]` no nome/descrição) e **Docs**
   (**TODOS** os docs que a atividade/marco tinha na origem — uma task de copy pode ter vários, ex.:
   Slides + Script + Atendimento —, cada Doc novo **nomeado pelo nome do Doc de origem** com o sufixo
   trocado p/ o destino, com **link pro doc de referência anterior**; doc **e** página já nascem
   **nomeados** — não abrem como "Sem título"). Idempotência dos docs é **por nome** (permite vários
   docs distintos na mesma task).
   Ao final de cada marco, **acrescenta na descrição uma seção `Atividades`** com os links (nome com
   hyperlink, um por linha) das atividades relacionadas — preserva o briefing e é idempotente (linha-marca
   `**Atividades**`, distinta de "Atividades:" do briefing; marcos sem atividades são pulados).
   **Idempotente** (pula o que já existe por nome). `--docs-only` cria só os Docs.
6. **Responsáveis e datas por último** (atribuir notifica a pessoa).
7. **Verificar + relatório.**
8. **Pasta do projeto no Google Drive** (após o projeto estar criado/verificado no ClickUp): criar a
   pasta `[SIGLA][TIPO][PRODUTO][MÊS][ANO]` no Drive compartilhado do cliente (`1. Projetos → <ANO>`)
   com a **estrutura-modelo** de subpastas — onde a equipe sobe os documentos de copy pro expert.
   Via **MCP Google Drive** (não o engine). Procedimento e estrutura em [DRIVE.md](DRIVE.md).
   **Só pastas, nunca documentos.** Idempotente por nome.

### Engine — comandos
```
TOKEN=$(security find-generic-password -s clickup-exos-api -w)
SK=~/.claude/skills/duplicar-projeto-clickup/scripts   # cópia canônica do engine + config exemplo
CLICKUP_TOKEN=$TOKEN python3 $SK/duplicar_projeto.py discover --config config_X.json --out plano.json
CLICKUP_TOKEN=$TOKEN python3 $SK/duplicar_projeto.py execute  --plan plano.json            # dry-run
CLICKUP_TOKEN=$TOKEN python3 $SK/duplicar_projeto.py execute  --plan plano.json --apply    # escreve
```
Capacidades confirmadas: **v2** (criar/editar task, custom fields via `/task/{id}/field/{fid}`, link
`/task/{id}/link/{links_to}`, checklist `/task/{id}/checklist` + items, prioridade); **v3 Docs** (criar
doc na task `parent:{id,type:1}` + página `text/md`; achar doc da origem `?parent_id=&parent_type=1`).
DELETE de doc dá 405 — só criamos; apagar a task remove o doc junto.

## Cross-workspace (replicar para OUTRO workspace)
Por padrão origem e destino ficam no mesmo workspace (Agência EU `9013012202`). Para replicar **de um
workspace para outro** (ex.: Agência EU → workspace de um cliente, como Telesapiens `90171059720`), o
engine aceita 3 chaves extras no config:
- `source.workspace` / `target.workspace` — IDs dos workspaces. O token do Keychain enxerga **todos os
  workspaces** onde o Cleber é membro (`GET /api/v2/team` lista). Ler task/list por ID é global; só a
  **API REST** cruza workspace (o MCP fica preso a 1).
- `activity_map` — `{ "<list_id origem>": "<list_id destino>" }` por lista de processo. **Obrigatório** no
  cross-workspace: sem ele as atividades seriam recriadas de volta na origem.
- `task_type_map` — `{ "<custom_item_id origem>": <id destino> }`. Os **tipos de tarefa diferem entre
  workspaces** (ex.: 1008=Atividade na Agência EU, mas 1008=WhatsApp no Telesapiens). Não mapeado → tarefa padrão.
- A normalização por nome (`task_type_rules`) resolve o tipo **por nome no workspace destino**, então é
  **no-op seguro no cross-workspace**: se o destino não tiver um tipo "Copy"/"Criativo", a regra não se
  aplica e o fluxo cai em `task_type_map`/tipo da origem. Para forçar tipos por nome no destino, ajuste
  `task_type_rules` com nomes que existam lá.

**Antes de rodar, colha os IDs do DESTINO** (todos por-workspace, diferentes da origem):
- Listas de fase e de processo do destino → `phase_map[].dst` e `activity_map`.
- Campo `list_relationship` (marco→card) de cada fase → **lendo um marco existente do destino**
  (`custom_fields` com `type=list_relationship` e `subcategory_id == painel`). O endpoint `/list/{id}/field`
  **não** retorna relationship; leia de uma task. Se a fase não tiver o campo, criar na UI antes (a API não cria custom field).
- IDs de custom field + opções (Produto/Empresa/Idioma…) e user IDs → de um marco/card existente do destino → montar `fields` com os IDs do destino.
- `target.card_id` = card do projeto no painel do destino (pode já existir; crie se faltar).

**Limitações descobertas:** título de Doc é **imutável via API** (`PUT/PATCH/POST/DELETE /docs/{id}` → 405).
Dá pra mudar o **nome da página** (`PUT /v3/.../docs/{docId}/pages/{pageId}` `{name}`), que atualiza o título
visível ao abrir + barra lateral; o `doc.name` (breadcrumb/hub) só muda pela UI.
O `create_doc()` já envia `{name}` no POST do doc **e** no PUT da página (fix jun/26) — docs novos não abrem
"Sem título". **Pegadinha:** se você **renomear as tasks DEPOIS** de criar os docs (ex.: rename JUL→AGO), o
`doc.name` e o **nome da página** continuam com o sufixo antigo (o rename de task não toca em Docs). Re-setar o
nome da página resolve o que se vê ao abrir; o `doc.name`/breadcrumb fica no antigo (só muda na UI). Há um
one-off de referência em `scripts/clickup_fix_doc_titles.py` (ajuste os sufixos `NEW`/`OLD`): renomeia **só**
páginas sem nome → nome da task; **preserva** páginas já nomeadas. Dry-run por padrão; `--apply` escreve.
Exemplo pronto: `scripts/config_tsap_mba.json` (Agência EU → Telesapiens).

## Regras que o engine aplica (a "Personalização" do gestor)
| Atributo | Ação |
|---|---|
| Etiqueta · Tipo (Milestone) · Campos personalizados | **MANTER** (setar Cliente/Produto/Idioma/Empresa/papéis do novo projeto) |
| Tipo da **atividade** (custom_item_id) | **NORMALIZAR por nome** (padrão Exos): "Copy …" → **Copy**, "Criativo(s) …" → **Criativo** (Copy prevalece p/ "Copy Criativos"). A regra por **nome** sobrepõe o tipo herdado da origem (mesmo se a origem está como "Atividade"); quem não casa nenhuma regra mantém o tipo da origem. Tipo resolvido por **nome** no workspace destino. Configurável via `task_type_rules` (`[]` desliga). Com `update_existing`, conserta também o tipo de atividades já existentes (auto-heal em re-run). |
| Status · Responsável · Data · Comentários · Observadores · Recorrência | **RESETAR/REMOVER** (responsável e datas por último) |
| Dependências entre atividades | **NÃO copiadas** (IDs mudam) — recriar manualmente pós-duplicação via MCP se a origem tiver `waiting_on` (ver seção abaixo) |
| Relacionamento (list_relationship) | **NÃO copiar** — revincular ao novo card/marco |
| Prioridade | **`normal`** por padrão (salvo pedido diferente) |
| Idioma | **por cliente** — Kleber Meireles = **Inglês**; demais = Português |
| Expert/cliente nas descrições | **trocar** o da origem pelo cliente atual (ex.: Elen Tolentino → Kleber Meireles) |
| `[ID<taskid>]` no nome (tasks de Campanha) | trocar pelo **ID da nova task** (nome **e** descrição) |
| Checklists | recriar como **checklist NATIVO** (nunca subtarefa — subtarefa polui relatório) |
| Docs | criar **um Doc novo por Doc da origem** (replica TODOS, não só o 1º), nomeado pelo Doc de origem (sufixo trocado), com **link pro doc de referência anterior**; idempotência por nome |
| Seção "Atividades" na descrição do marco | acrescentar links (nome→task, 1 por linha) das atividades relacionadas; preserva briefing, idempotente, pula marco sem atividades |

## Dependências entre atividades (pós-duplicação)

O engine **não copia** dependências: os IDs de task mudam na duplicação, então as referências da
origem apontariam para tasks erradas. Se o projeto-origem tiver `waiting_on` entre atividades,
é necessário recriá-las manualmente **após** o `--apply`.

**Quando aplicar:** projetos perpétuos e lançamentos que têm cadeia Copy → Layout/Arte/Agendamento.
Verifique se a origem tem dependências lendo qualquer atividade com `include=["dependencies"]`.

**Workflow (3 passos via MCP):**

1. **Ler as arestas da origem** — para cada atividade do projeto-origem:
   ```
   clickup_get_task(task_id="<id_origem>", include=["dependencies"])
   ```
   Anote as arestas: `task_id` (dependente) → `depends_on` (pré-requisito), `type` (1 = waiting_on).

2. **Mapear origem → destino** — o nome da task é idêntico, só a sigla do cliente muda
   (ex.: `[LL]` → `[ET]`). Use `clickup_search` ou a lista de tasks já coletadas durante a
   duplicação para obter os IDs destino correspondentes.

3. **Criar as dependências no destino** — para cada aresta (todas independentes; envie em paralelo):
   ```
   clickup_add_task_dependency(
     task_id="<id_destino_dependente>",
     depends_on="<id_destino_prerequisito>",
     type="waiting_on"
   )
   ```

**Verificação:** releia as tasks dependentes com `include=["dependencies"]` e confirme que
`depends_on` aponta para o ID correto no destino. Tasks com 2 pré-requisitos (ex.: "Criar Grupos"
espera "Copy Config. Grupos" e "Arte para Grupos") devem aparecer com 2 entradas.

## Documentos de referência (Docs nativos)
- Uma atividade de copy pode ter **vários** ClickUp Docs (`parent type 1`) — ex.: Aula Magna →
  Slides + Script do Evento + Atendimento Zoom. O engine replica **TODOS** (não só o primeiro).
- O **documento de referência = o Doc correspondente no projeto anterior** (a origem).
- A duplicação cria **um Doc novo por Doc da origem**, cada um **nomeado pelo nome do Doc de origem**
  (com o sufixo trocado p/ o destino; tolera sufixos divergentes/bagunçados via `doc_ref_name`) e com
  um **link pro Doc da origem**. O engine acha os docs da origem (`task_docs`) e cria os novos
  automaticamente (`docs.enabled` no config). Idempotência **por nome do doc**.
- ⚠️ A API **não renomeia nem apaga** Doc nativo (405). Por isso o nome certo é definido **na criação**;
  docs órfãos/duplicados (ex.: de projeto renomeado depois) precisam ser apagados **à mão**.
  Anexos/Canva externos ficam como pendência manual.

## Guardrails
- **Nunca** criar pasta/lista **no ClickUp**. Nunca assumir a origem — sempre confirmar.
  (No **Drive** a criação de pastas é esperada — passo 8/[DRIVE.md](DRIVE.md) —, mas só **pastas**, nunca documentos.)
- Engine é **dry-run por padrão**; `--apply` é explícito. **Sempre** mostrar o dry-run e confirmar antes.
- **Idempotência por nome**: não duplica o que já existe (cuidado com nomes duplicados na origem).
- Nunca mudar `Aprovado → Concluído` sem confirmação.

## Referências
- [REFERENCE.md](REFERENCE.md) — IDs de listas/fases, custom fields (+ opções), papel→pessoa, siglas, vínculos.
- [DRIVE.md](DRIVE.md) — passo 8: pasta do projeto no Google Drive (estrutura-modelo, IDs por cliente, procedimento MCP).
- [transcricoes/](transcricoes/) — áudios do gestor (fonte das regras).
- Engine + configs exemplo: `scripts/duplicar_projeto.py`, `scripts/config_km_apb.json` (mesmo-workspace),
  `scripts/config_tsap_mba.json` (cross-workspace). Crie um `config_<projeto>.json` por projeto e gere
  `plano.json` na pasta de trabalho.
