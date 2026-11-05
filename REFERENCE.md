# REFERENCE — Dados do ClickUp para duplicação (Exos)

Workspace ID: `9013012202` · Space `Projetos`: `90130362098`.
Sempre confirme via MCP antes de escrever; estes IDs aceleram, mas a verdade é o workspace.

## 1. Listas de fase FIXAS (destino — nunca criar)

Cada tipo de projeto tem uma pasta fixa com listas de fase. Marcos vivem nelas.

**Lançamento** — folder `Gestão de Lançamentos` `90131242142`:
| Fase | List ID |
|---|---|
| Concepção | `901302376636` |
| Setup | `901302376637` |
| Captação | `901302378944` |
| Aquecimento | `901302378939` |
| Evento | `901302376639` |
| Lançamento | `901302376640` |
| Pós Venda | `901302376641` |
| Downsell | `901310974062` |

Outras pastas de fase (mesma lógica; ler via `clickup_get_workspace_hierarchy` quando precisar):
- **Perpétuo** — `Gestão de Perpétuos` `90133207624` (Concepção→Setup→Geração de Público→Vendas→Recuperação→Pós-Venda→Melhoria Contínua).
- **Reunião Secreta** — `Gestão Reunião Secreta` `90133093576` (listas por entregável: Copy/Expert/Vídeos/Páginas/Design/Infra/Tráfego/Testar/Onboarding/Métricas).
- **Webinário** — `Gestão de Webinario` `90134360578`.
- **Evento Presencial** — `Gestão de Eventos Presenciais` `90137209329`.

## 2. Painéis (cards de projeto)
| Painel | List ID |
|---|---|
| Projeto Lançamentos | `901302496038` |
| Projeto Perpétuos | `901312155462` |
| Projeto Webinários | `901307899002` |
| Eventos Presenciais | `901308065852` |
| Projetos Internos | `901302196962` |
| Projetos Externos | `901302196964` |

Nome do card (convenção recente): `<Cliente> [SIGLA][TIPO][PRODUTO][MÊS][ANO]`
(ex.: `Daniela Moleiro [DM][LB][POS][JUL][26]`, card `86agyd0uj`).
Card-modelo: `Novo Projeto de Lançamento` `86a52wur1` (tags `lançamento` + `modelo`).

## 3. Nomenclatura — `[SIGLA_CLIENTE][TIPO][PRODUTO][MÊS][ANO]`

**Clientes (sigla):** ET=Elen Tolentino · LL=Leticia Lang · LT=Livia Tolentino · KM=Kleber Meireles ·
DM=Daniela Moleiro · DH=Debora Heller · ABP=Ana Beatriz Pimenta. (Confirme/expanda pelo dropdown
`Cliente` — ver §4.)

**Tipo:** RS=Reunião Secreta · LM=Lançamento Meteórico · LB=Lançamento Base · PEP=Perpétuo ·
EP=Evento Presencial. (Variações vistas no histórico: SC=Semana do Consumidor, BF=Black Friday,
LS=Lançamento Semente — use o que o usuário indicar.)

**Produto:** POS=Pós-Graduação · MCE · AAT/APB/EFA (produtos Kleber Meireles) · LIVES · EBOOK · TIC.

**Mês:** JAN FEV MAR ABR MAI JUN JUL AGO SET OUT NOV DEZ · **Ano:** 2 dígitos (26).

**Campanhas de tráfego (Meta/Google):** `[PGL][SIGLA][TIPO][PRODUTO][MÊS][ANO][FASE] Texto livre` — a mesma tag
do projeto, contígua, mais **um** marcador de fase logo após o ano. O dash (`dash.exosmkt.com`) lê projeto e fase
pelo nome. Tabela de marcadores, conjuntos de anúncio, UTM e tasks de campanha em [TRAFEGO.md](TRAFEGO.md).

## 4. Custom fields (IDs fixos)

Setar via `clickup_create_task`/`clickup_update_task` → `custom_fields:[{id, value}]`.

| Campo | ID | Tipo | Observação |
|---|---|---|---|
| Cliente | `4334ea1b-2d90-4974-9ac2-287142e9be5e` | drop_down | **Setar p/ o novo cliente** (ex. Daniela Moleiro = opção `8a2dbdd0-ffb4-4750-8e21-bc4031a945bc`) |
| Produto | `b9d27455-df3d-439b-aa68-1af6c0d08fe1` | drop_down | setar conforme o produto |
| Evento | `81d33710-f6e5-4f11-a48c-49fefe0ad426` | drop_down | nome do evento da turma |
| Idioma | `f45be5a5-a908-453f-bc37-c8300c40e71d` | drop_down | **por cliente**: Kleber Meireles=**Inglês** (`f1d00fc8-26df-4e4d-a95f-575e980a29b5`); demais=Português (`f0817b25-b0b6-4357-bd06-9401d96072b8`); Espanhol=`1f81ad4f-6b1c-4657-a2aa-d44c0b197c42` |
| Empresa | `60a53862-4eaa-49d7-910a-f20fb4352145` | drop_down | EXOS etc. |
| Estrategista | `d0c8fa87-69ee-4130-a8ad-f6058eec11bf` | users | papel |
| Copywriter | `c8a7d8d1-fced-4bbc-8147-d097fe9d61f5` | users | papel |
| Designer | `97d791d0-f777-4081-8b09-45ac6d339e8d` | users | papel |
| Editor de Vídeos | `6519b36d-da24-4312-88e7-e23052fd0c85` | users | papel |
| Gestor Tráfego | `0b61034c-4d5f-4d4b-b21a-e0afa8e489c1` | users | papel |
| Gestor Automações | `17c20951-740d-40fc-8502-218c4c0a1a99` | users | papel |
| Webdesigner | `c49608f9-49e9-4934-ac8a-e7f0d72a177c` | users | papel |
| Gestor Projetos | `23d522ad-218a-400d-90d7-0b3d97d0148d` | users | papel |

> **Resolver opções de dropdown** em runtime: leia um marco de referência com
> `clickup_get_task detail_level:detailed`, ache a opção pelo `name` e use o **`id` (uuid)** dela
> como `value`. ✅ Confirmado em teste: passar o **uuid** da opção funciona.

> **Atividades (space Marketing)** usam os **MESMOS field IDs** acima (Cliente/Produto/Idioma/
> Empresa/papéis) — preencher igual ao marco. Opções: Kleber Meireles=`4d8875f7-a817-4415-b80a-0fcc4c255ff9`,
> APB=`c930970c-f293-4182-b74a-9c703dd434f3`, Português=`f0817b25-b0b6-4357-bd06-9401d96072b8`,
> EXOS=`4098a913-8e9f-4621-b4b9-6aa4e0e93066`. Listas especiais (ex.: "Geração de Público",
> "Processos de Automações") têm subconjunto — pule o campo que não existir.

## 5. Vínculo (list_relationship) — marco → projeto

O marco tem um custom field **por fase** do tipo `list_relationship` apontando p/ o painel
(`subcategory_id`). **Lançamento** → Painel Lançamentos (`901302496038`):
- **"2. Setup"** = `14c95561-080b-43d5-a0cf-8add71590e65` · **"1. Concepção"** = `e233dc34-d7e6-49d4-9c1c-6c9791e99018`.

**Perpétuo** → Painel Perpétuos (`subcategory_id: 901312155462`) — campos por fase (confirmados em uso):
- **"1. Concepção"** = `4b7b6a98-aa25-4e87-837b-c849d8300e18` · **"2. Setup"** = `7d008b1d-e5e0-418a-848b-a2a2ffe17ce8`
- **Geração de Público** = `59514ee3-9eb2-4e68-b953-3a44d3ef7024` · **Vendas** = `4e5e2edd-b339-4341-a2c7-4266769055e8` · **Pós-Venda** = `6654d6bc-24c0-4fe7-b594-5a2389efbc08`
- ⚠️ No folder **Gestão de Perpétuos**, os campos de **papel** (Estrategista/Designer/Editor/Webdesigner/Tráfego/Gestor Projetos/Gestor Automações) só existem nas listas **Concepção** e **Setup**; nas demais fases não há esses campos. E **não há** campo `Copywriter` em perpétuo (usar `Estrategista`).

**Resolver os demais em runtime** (recomendado): ao criar um marco na fase X, leia um marco
existente daquela lista (`clickup_get_task`) e ache o custom field cujo `type` é `list_relationship`
e `subcategory_id` = `901302496038`; use o `id` dele.

Setar o vínculo: `clickup_update_task custom_fields:[{id:"<id_da_fase>", value:{"add":["<id_do_card>"]}}]`.
✅ **Confirmado em teste** o formato `{"add":["<id_do_card>"]}` (a leitura passa a mostrar o card vinculado).

Vínculo **atividade → marco**: atividade é criada como **subtarefa** (`parent:"<id_marco>"`), o que
já a coloca "dentro" do marco. Se o projeto de origem usar links de tarefa em vez de subtarefa,
replicar com a relação equivalente.

## 6. Papel → pessoa (defaults observados — confirme)
| Papel | Pessoa (user_id) |
|---|---|
| Estrategista / Copy | Maurício Magnavita `87901690` |
| Gestor Projetos | Cleber de Lima `54927970` |
| Gestor Automações / Webdesigner | Gabriel Gouvea `55123416` |
| Copywriter | Adrian Schultz `60931770` (varia: Mateus etc.) |
| Designer | Patrick Guilherme `54941517` |
| Editor de Vídeos | Fernando Santana `60428351` |
| Gestor Tráfego | varia (Pedro Lopes `290496564`, Gabriel, Johnny `44326709`) |

Resolver nomes→ids com `clickup_resolve_assignees` / `clickup_find_member_by_name`.
**Atribuir responsáveis só no FINAL** (atribuir notifica a pessoa).

## 7. Origem de referência (o "mais completo") e limitações

- **Reunião Secreta / Lançamento**: o mais completo hoje é **Elen Tolentino [RS][POS][FEV][26]**
  (card `86adzap5y`) — "o de fevereiro foi redondo". A fase de **antecipação/aquecimento** mais
  completa está nos projetos da Elen; algumas copies estão melhores em projetos da Letícia. O
  ideal é compor (Mauri define o padrão). Sempre **confirme a origem** com o usuário.
- **Documento de referência** = sempre o do projeto **anterior** (mês anterior). Trocar/remover na
  duplicação (ver SKILL.md).

**Limitações do MCP (sinalizar como pendência manual no relatório):**
- Não copia **anexos** (manter anexos só em atividades de copy → copiar à mão).
- Não recria **checklists nativas** → ou converter atividades em subtarefas, ou anotar pendência.
- Não copia **automações** nem **dependências** nativas.
- `clickup_get_custom_fields` por **lista** quebra na validação → ler campos via `clickup_get_task`.

## 8. Formatos confirmados (validado em teste descartável — mai/2026)
1. ✅ **Milestone**: `clickup_create_task task_type:"Milestone"` → cria com `task_type:"milestone"`.
2. ✅ **Vínculo `list_relationship`**: `value:{"add":["<id_card>"]}` em create/`update_task`.
3. ✅ **Dropdown** (`Cliente`/`Produto`/`Evento`/`Idioma`/`Empresa`): `value` = **uuid da opção**.
4. ✅ **Status**: ao criar, a tarefa já nasce no **status inicial aberto** da lista (ex. "para fazer");
   não precisa setar e nunca herda "finalizado".
5. ✅ **Subtarefa**: `parent:"<id_marco>"` coloca a atividade dentro do marco.
6. ⚠️ **Tipo padrão da lista = Milestone**: tarefa criada SEM `task_type` sai como *milestone*. Para
   uma **atividade** que não deva ser marco, passe `task_type` explícito da origem (ex.: `"Task"`).

## 9. Status, etiquetas e pessoas (levantado em out/26)

**Status por lista** (nome exato, em minúsculas na API):
- **Processo de Copywriting `901301657744`, Design & Criação `901301657750` e Agendamentos `901301657745`:**
  para fazer → em andamento → **em revisão** → em aprovação → em alteração & ajuste → aguardando informação →
  **descartados** (fechado) → finalizada.
  - O `skip_status` do config precisa do plural `descartados`.
- **Gestão de Campanhas `901301657760`:** para fazer → em andamento → solicitar criativos → em análise →
  em veiculação → em otimização → otimização realizada → pausada → descartado → finalizada.
- **Fases de perpétuo:**
  - Concepção: … em revisão → em aprovação → alteração & ajuste → aguardando informação → declinado → finalizado.
  - Setup: a mesma sequência, com "em alteração & ajuste" e "descartado".
- **Painel Perpétuos `901312155462`:** backlog → iniciação → planejamento → execução → monitoramento →
  encerramento → pausado → descartado → finalizado.

**Idioma:** a opção chama **"Espanhol "**, com espaço no fim. Use sempre o UUID `1f81ad4f-6b1c-4657-a2aa-d44c0b197c42`,
nunca o nome.

**Etiquetas:**
- `latam` existe nos spaces Projetos e Marketing; `internacional` só no Marketing. Todas são minúsculas.
- Etiqueta com acento (`perpétuo`) vai **codificada** na URL de `POST /task/{id}/tag/{nome}`. Crua, falha calada.

**Ex-membros em campo de pessoa:**
- Matheus Dias `49078977` e Adrian Schultz `60931770` não estão mais no workspace. Gravar os dois devolve 200 e deixa o campo vazio.
- No `[ET][PEP][ESP][MCE][26]`, o Cleber decidiu substituir pelo Maurício (`substituir_usuarios` do acabamento).
