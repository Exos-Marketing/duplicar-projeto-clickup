---
name: duplicar-projeto-clickup
description: Duplica/cria projetos no ClickUp da Exos a partir de um projeto-origem, API-first com o engine duplicar_projeto.py — recria marcos, atividades linkadas, campos, checklists nativos, Docs de referência e prioridade, com a nomenclatura [SIGLA][TIPO][PRODUTO][MÊS][ANO] e a hierarquia Atividade→Marco→Projeto; lê a origem e gera um plano editável. Inclui o padrão do Planejamento de Tráfego (nomes de campanha [PGL][SUFIXO][FASE], conjuntos, UTM, tasks de campanha) e o conferidor checar_trafego.py. Use quando o usuário pedir para duplicar, replicar ou criar um projeto/lançamento/perpétuo/reunião secreta/evento no ClickUp ("duplica o projeto de X pra Y", "novo lançamento", "cria o projeto da Daniela", "monta o projeto a partir do modelo"), para replicar ENTRE workspaces ("monta esse projeto no workspace do cliente", "duplica pro workspace da Telesapiens") ou para montar/conferir a nomenclatura das campanhas de tráfego de um projeto ("confere os nomes das campanhas", "planejamento de tráfego no padrão").
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
   **`name_swaps` com o par `[tag origem] → [tag destino]`** sempre que a origem tiver o Planejamento de Tráfego
   no padrão: as campanhas `[PGL][SUFIXO][FASE]` dentro das **descrições** só trocam de tag por `name_swaps`
   (ver [TRAFEGO.md](TRAFEGO.md) §7).
   Opcional: `planejamento_marco` (string p/ casar o marco de planejamento; default `"planejamento
   estratégico"` — só ajuste se o marco tiver outro nome no projeto).
3. **`discover`** (read-only) → gera `plano.json` (marcos, atividades, docs de referência, checklists).
   **Edite o plano** para adaptar a formatos novos — é o ponto de flexibilidade (modelo-base + ajuste).
4. **Dry-run** `execute --plan plano.json` → **mostre ao usuário** o que será criado. **Confirme.**
5. **`execute --plan plano.json --apply`** → cria card (se faltar), marcos (milestone, campos, vínculo
   ao card, checklist nativo, prioridade), atividades (na mesma lista de processo, campos, vínculo ao
   marco, checklist, prioridade, troca de expert→cliente, fix do `[ID]` no nome/descrição) e **Docs**
   (**TODOS** os docs que a atividade/marco tinha na origem — uma task de copy pode ter vários, ex.:
   Slides + Script + Atendimento —, cada Doc novo **nomeado pelo nome do Doc de origem** com o sufixo
   trocado p/ o destino; doc **e** página já nascem **nomeados** — não abrem como "Sem título"). O
   **corpo** de cada Doc novo nasce com `**Briefing:**` (vazio — o Claude preenche depois) +
   `**Referência:** [URL]` apontando pro Doc anterior/origem. Idempotência dos docs é **por nome**
   (permite vários docs distintos na mesma task). Além disso, em cada **task de Copy** o engine escreve
   na **descrição** — abaixo do briefing herdado — linhas **rotuladas** e **por escrito** (URL de texto,
   não embed): `Documento(s) de entrega: {nome do Doc} — {URL canônica}` (uma por Doc, idempotente **por
   URL**) e, no **sweep final**, `Planejamento estratégico: {URL do marco}` (o marco de **Planejamento
   Estratégico** do próprio projeto — casado por nome, **não** o link do Whimsical) em **todas** as
   copies. Não toca a descrição dos marcos.
   Ao final de cada marco, **acrescenta na descrição uma seção `Atividades`** com os links (nome com
   hyperlink, um por linha) das atividades relacionadas — preserva o briefing e é idempotente (linha-marca
   `**Atividades**`, distinta de "Atividades:" do briefing; marcos sem atividades são pulados).
   **Idempotente** (pula o que já existe por nome). `--docs-only` cria só os Docs.
6. **Briefing + validação das copies**: preencher o `Briefing:` de cada Doc de entrega, **tirar o
   briefing herdado da descrição** (task de copy não leva briefing na descrição) e conferir as
   URLs/textos (ver seção **"Briefing + validação das atividades de copy"**).
7. **Responsáveis e datas por último** (atribuir notifica a pessoa).
8. **Verificar + relatório.** Inclui o **Planejamento de Tráfego**: `checar_trafego.py --marco <id> --campanhas`
   confere os nomes de campanha do marco e das tasks de campanha contra o padrão
   `[PGL][SIGLA][TIPO][PRODUTO][MÊS][ANO][FASE] Texto livre` ([TRAFEGO.md](TRAFEGO.md)). Depois o gestor de
   tráfego preenche verba/período/públicos mantendo os nomes, e o Gabriel aprova no comentário do marco.
9. **Pasta do projeto no Google Drive** (após o projeto estar criado/verificado no ClickUp): criar a
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
CLICKUP_TOKEN=$TOKEN python3 $SK/checar_trafego.py --marco <id do marco> --campanhas      # nomes de campanha (read-only)
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
| Campanhas de tráfego (descrição do marco **Planejamento de Tráfego** e das tasks de **Campanha**) | nomes no padrão **`[PGL][SIGLA][TIPO][PRODUTO][MÊS][ANO][FASE] Texto livre`**: tag do projeto **contígua**, **um** marcador de fase **logo após o ano** (`[ANTECIPAÇÃO]` · `[CADASTROS]`(+`[TESTE]`) · `[RECONHECIMENTO]`+"CONTAGEM REGRESSIVA" · `[EVENTO]`/`[AULA]` · `[VENDAS]` · `[CARRINHO]` · `[DOWNSELL]` · `[PESQUISA]` · `[REABERTURA]`), temperatura (Frio/Quente) no texto livre — o dash lê projeto e fase pelo nome. Tag trocada via `name_swaps`; conferir com `checar_trafego.py`. Regras, conjuntos, UTM e modelo do marco em [TRAFEGO.md](TRAFEGO.md) |
| Checklists | recriar como **checklist NATIVO** (nunca subtarefa — subtarefa polui relatório) |
| Docs | criar **um Doc novo por Doc da origem** (replica TODOS, não só o 1º), nomeado pelo Doc de origem (sufixo trocado); **corpo** = `**Briefing:**` (vazio, o Claude preenche) + `**Referência:** [URL]` (Doc anterior/origem); idempotência por nome |
| Doc **"Central de Link(s)"** (casado por nome, acento/caixa-insensível) | nasce com **`Planejamento estratégico: {URL da task}` como PRIMEIRA linha do conteúdo** (antes do Briefing) — link para o próprio marco de Planejamento Estratégico do projeto (a task no ClickUp, não o Whimsical). Esse Doc é **compartilhado com a equipe/expert**, então o planejamento precisa ser o primeiro item visível. Só na criação (doc já existente não é reescrito) |
| Seção "Atividades" na descrição do marco | acrescentar links (nome→task, 1 por linha) das atividades relacionadas; preserva briefing, idempotente, pula marco sem atividades |
| `Documento(s) de entrega:` na descrição da **task de Copy** | acrescentar, ABAIXO do briefing herdado, uma linha `Documento(s) de entrega: {nome do Doc} — {URL canônica}` por Doc nativo (`…/{DST_WS}/docs/{did}/{pid}`); URL **por escrito** (não embed); preserva o briefing, idempotente **por URL**; só em atividades com Doc; **marcos não recebem** |
| `Planejamento estratégico:` na descrição da **task de Copy** | no **sweep final**, acrescentar `Planejamento estratégico: https://app.clickup.com/t/{marco}` em **todas** as copies (`type_for_name == Copy`), apontando pro marco **Planejamento Estratégico** do projeto (casado por nome, override `planejamento_marco`); URL do **marco** no ClickUp, **não** o Whimsical; idempotente **por URL**; se o marco não for achado, loga aviso e pula |
| Briefing na descrição da **task de Copy** | **não leva** (regra de 04/11/26). O engine ainda copia a descrição da origem: o Claude tira o briefing herdado depois do `--apply` e deixa só as linhas `Documento(s) de entrega:` e `Planejamento estratégico:` (ver "Briefing + validação das atividades de copy") |

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
  (com o sufixo trocado p/ o destino; tolera sufixos divergentes/bagunçados via `doc_ref_name`). O
  **corpo** do Doc novo nasce com `**Briefing:**` (vazio — o Claude preenche depois) + `**Referência:**
  [URL]` apontando pro Doc da origem. O engine acha os docs da origem (`task_docs`) e cria os novos
  automaticamente (`docs.enabled` no config). Idempotência **por nome do doc**.
- ⚠️ A API **não renomeia nem apaga** Doc nativo (405). Por isso o nome certo é definido **na criação**;
  docs órfãos/duplicados (ex.: de projeto renomeado depois) precisam ser apagados **à mão**.
  Anexos/Canva externos ficam como pendência manual.
- **Doc "Central de Link(s)"** (casado por nome — "central de link"/"central de links", variação vista
  no histórico, acento/caixa-insensível): esse Doc é **compartilhado com a equipe/expert**, então nasce
  com `Planejamento estratégico: {URL da task}` como **primeira linha**, antes do `**Briefing:**` —
  link clicável (URL crua) para o próprio marco de Planejamento Estratégico do projeto (a task no
  ClickUp, casada por nome via `planejamento_marco`/default `"planejamento estrategico"`; **não** o
  Whimsical). Pra isso funcionar mesmo quando esse marco não é o primeiro na ordem retornada pela API,
  o `execute` **reordena os marcos do plano** pra processar o de Planejamento Estratégico primeiro —
  garantindo que a URL já esteja resolvida antes de qualquer Doc ser criado. Só se aplica **na criação**
  do Doc (idempotência por nome do doc já existente não reescreve o conteúdo); Central de Link(s)
  criados **antes** dessa mudança precisam da linha adicionada manualmente (`clickup_update_document_page`).
- Nas **tasks de Copy**, além de criar o Doc nativo, o engine escreve na **descrição da task** (abaixo do
  briefing herdado), **por escrito** (URL de texto, não embed): `Documento(s) de entrega: {nome do Doc} —
  {URL canônica}` (`https://app.clickup.com/{DST_WS}/docs/{did}/{pid}`, uma linha por Doc) e, no sweep
  final, `Planejamento estratégico: {URL do marco}`. Idempotência **por URL**: cada linha só é escrita se
  a URL ainda não estiver na descrição, então não colide com links de doc-view manuais (`…/v/dc/{shortid}`)
  do briefing e re-run não duplica. **Marcos não recebem** essas linhas.

## Briefing + validação das atividades de copy (pós-`--apply`)
O engine escreve os **rótulos + URLs** (determinístico); o **Briefing** e a **conferência** são do Claude.
Depois do `--apply`, para **cada atividade de Copy** (independentes — pode paralelizar):

1. **Preencher o Briefing** no Doc de entrega (o que fazer, em 1–2 linhas):
   - Ler o **Doc de origem** (`clickup_get_document_pages` na URL de Referência) — **se houver** briefing
     lá, adaptar as 1–2 linhas ao projeto atual; **se não houver**, adaptar o próprio doc de referência ao
     projeto (o Claude já sabe montar). Gravar no Doc novo com `clickup_update_document_page` (substitui o
     `**Briefing:**` vazio; **preserva** a linha `**Referência:**`).
2. **Tirar o briefing da descrição** — regra de 04/11/26: **task de copy não leva briefing na
   descrição**. O engine copia a descrição da origem; se ela trouxer briefing (`**Briefing:**` ou o mesmo
   conteúdo com outro rótulo: o que escrever, resumo do planejamento, regras, alertas), regravar a
   descrição só com as linhas `Documento(s) de entrega:` e `Planejamento estratégico:` do projeto novo
   (`clickup_update_task`). Marcos e atividades que não são de copy mantêm o briefing.
3. **Validar** (conferência final):
   - `clickup_get_task(task_id, detalhado/markdown)` → confirmar que as URLs do(s) **Documento(s) de
     entrega** **e** do **Planejamento estratégico** aparecem na descrição, **sem briefing**.
   - `clickup_get_document_pages(doc)` no Doc de entrega → confirmar que o **Briefing** e a **URL de
     Referência** estão no texto.
   - **Se aparecer só o nome (embed/anexo) em vez da URL → colar a URL no texto** (editar a descrição via
     `clickup_update_task` ou a página via `clickup_update_document_page`).

## Versão em outro idioma (acabamento + tradução)
Use quando o projeto novo for a **versão em outro idioma** de um projeto que já existe. Exemplos:
`[ET][PEP][ESP][MCE][26]` a partir do `[ET][PEP][MCE][26]` (LatAm, espanhol) ou um projeto do KM em inglês.
Também serve para qualquer duplicação que precise de campos **iguais aos da origem task a task**, de
responsável/data por regra ou de status final.

O engine faz a estrutura; os scripts abaixo (em `scripts/`) fazem o resto. Todos:
- leem o mesmo `config_<projeto>.json` (blocos `acabamento`, `remap` e `traducao`);
- são dry-run por padrão, escrevem com `--apply` e são idempotentes;
- pegam o token no Keychain.

Exemplo real: `/Users/cleberdelima/Documents/Exos/config_et_pep_esp_mce.json`.

| Passo | Script | O que faz |
|---|---|---|
| 1 | `duplicar_seguro.py discover/execute` | Engine com 2 proteções: nunca monta índice parcial (página falhou → aborta) e não repete às cegas um POST de criação em 429/timeout (rechecа pelo nome). Use no lugar do engine cru. |
| 2 | `espelhar_drive.py` | Espelha a **árvore de pastas** do projeto de origem no Drive (só pastas, `--excluir`). Grava o mapa origem→destino, que o passo 5 usa. |
| 3 | `acabamento.py` | Campos copiados da origem task a task. Também: troca de usuário, etiquetas (origem + extras), responsáveis/vencimento/prioridade por regra (card/marco/ativ), reparo de vínculos e checklists e sweep de `start_date`. `--only status` roda no fim; `--verify` relê tudo. |
| 4 | `recriar_dependencias.py` | Dependências da origem cujas duas pontas estão no plano. |
| 5 | `remapear_descricoes.py` | Remonta a descrição das tasks **novas** a partir do markdown da origem e religa links de task, Doc e pasta do Drive. |
| 6 | `traduzir_docs.py` | `pacotes` → subagentes traduzem para `es/NN_*.md` → `checar` (gates locais) → `aplicar` (grava com gates e releitura) → `verificar`. |

**Ordem:**
1. discover → ajuste do plano → dry-run → OK do usuário → apply (background);
2. varredura de duplicatas → Drive → acabamento → dependências → remap;
3. aplicar a tradução → `acabamento --only status` → `--verify`.

A tradução (pacotes + subagentes) pode rodar **em paralelo desde o discover**, porque só depende da origem.

**Chaves novas do config:**
- `source.card_id`: card da origem; os campos dele vão para o card do destino.
- `acabamento`:
  - `reaproveitados`: itens criados antes, à mão; só recebem o que está **vazio**.
  - Campos: `copiar_campos_origem`, `campos_override` `{field_id: valor}`, `substituir_usuarios` `{id_antigo: id_novo}`.
  - Etiquetas: `copiar_etiquetas_origem`, `etiquetas_extra`.
  - Regras: `regras` `{card|marco|ativ: {responsaveis, vencimento, prioridade}}`. `null` não mexe; `[]` deixa sem ninguém.
  - Status: `status` `[{tipo|nome_comeca, status}]` e `status_exige_marcador_doc`.
  - Outros: `checklists_nos_reaproveitados`, `indice_desde` (corte de data do índice).
- `remap`: `nunca_escrever`, `linhas_topo` `{src_id: linha}`, `doc_extra`.
- `traducao`:
  - Pasta e idioma: `pasta`, `idioma`, `tratamento`.
  - Cabeçalho do Doc: `briefing`, `marcador`.
  - Conteúdo: `oferta`, `glossario`, `instrucoes_extra`.
  - Links: `mapa_links`, `links_podem_sair`.
  - Termos: `proibidos`, `evitar`, `pt_permitidos`.
  - Docs especiais: `copiar_secao`, `texto_es_existente` (texto já no ar: arquivo ou seção da origem), `versao_no_ar`, `fora_da_oferta`.
  - Gates: `gates`, `gates_por_doc`.

**Gotchas** (out/26):
- **Item reaproveitado com acento diferente da origem** ("Tráfego" × "Trafego"): ajuste o `new_name` no plano, em NFC. Senão, o engine cria uma duplicata.
- **`skip_status`** precisa do plural **`descartados`**, que é o status fechado das listas do Marketing.
- **Etiqueta com acento** (`perpétuo`) vai **codificada** na URL. Crua, falha calada.
- **Ex-membro ou convidado em campo de pessoa:** a API devolve 200 e o campo fica vazio. Use `substituir_usuarios`.
- **list_relationship nunca se copia da origem**: ele aponta para o card da origem.
- **Doc de destino:**
  - grave só se a página estiver vazia ou só com o cabeçalho do engine;
  - use `PUT replace` sem `name`;
  - releia depois;
  - o status "em revisão" só vem **depois** do Doc relido.
- **Não re-rode o engine depois do remap:** ele reescreve a seção Atividades dos marcos.
- **Lista aninhada que começa com `*       *` some ao gravar:** esse padrão vem da exportação do próprio ClickUp. Ao
  gravar, o ClickUp lê como bloco de código e descarta os itens. Reescreva como lista aninhada normal
  (`*   item` + `    *   subitem`). O `aplicar` acusa isso na releitura ("releitura diverge").
- **Domínio solto (`elentolentino.com.br`) vira link na gravação.** Os scripts já tratam isso como igual na comparação.

## Guardrails
- **Nunca** criar pasta/lista **no ClickUp**. Nunca assumir a origem — sempre confirmar.
  (No **Drive** a criação de pastas é esperada — passo 8/[DRIVE.md](DRIVE.md) —, mas só **pastas**, nunca documentos.)
- Engine é **dry-run por padrão**; `--apply` é explícito. **Sempre** mostrar o dry-run e confirmar antes.
- **Idempotência por nome**: não duplica o que já existe (cuidado com nomes duplicados na origem).
- Nunca mudar `Aprovado → Concluído` sem confirmação.

## Referências
- [REFERENCE.md](REFERENCE.md) — IDs de listas/fases, custom fields (+ opções), papel→pessoa, siglas, vínculos.
- [DRIVE.md](DRIVE.md) — passo 8: pasta do projeto no Google Drive (estrutura-modelo, IDs por cliente, procedimento MCP).
- [TRAFEGO.md](TRAFEGO.md) — Planejamento de Tráfego: nomenclatura das campanhas (padrão Gabriel 23/10/26 +
  dash.exosmkt.com/convencoes), conjuntos de anúncio, UTM, tasks de campanha, modelo do marco e o que a duplicação
  precisa (`name_swaps`); conferidor read-only `scripts/checar_trafego.py`.
- [transcricoes/](transcricoes/) — áudios do gestor (fonte das regras).
- Engine + configs exemplo: `scripts/duplicar_projeto.py`, `scripts/config_km_apb.json` (mesmo-workspace),
  `scripts/config_tsap_mba.json` (cross-workspace). Crie um `config_<projeto>.json` por projeto e gere
  `plano.json` na pasta de trabalho.
- Pós-duplicação (seção "Versão em outro idioma"): `scripts/comum.py` (base: API, resolvedor
  origem→destino), `duplicar_seguro.py`, `acabamento.py`, `recriar_dependencias.py`, `espelhar_drive.py`,
  `remapear_descricoes.py`, `traduzir_docs.py`. Exemplo de config completo:
  `/Users/cleberdelima/Documents/Exos/config_et_pep_esp_mce.json`.
