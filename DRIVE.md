# DRIVE — Pasta do projeto no Google Drive (Exos)

Depois que o projeto é criado/verificado no **ClickUp**, cria-se a **pasta do projeto no Drive
compartilhado do cliente**, onde a equipe sobe/organiza os documentos de copy enviados ao expert.
A pasta segue a mesma nomenclatura `[SIGLA][TIPO][PRODUTO][MÊS][ANO]` e nasce com a **estrutura-modelo**
de subpastas (scaffold vazio — **NÃO criar documentos**, só pastas).

Tudo via **MCP Google Drive** (`mcp__claude_ai_Google_Drive__*`). Criar pasta =
`create_file` com `contentMimeType: "application/vnd.google-apps.folder"` + `parentId`.
Funciona em shared drive. **Não** usa o engine Python (que é REST do ClickUp).

## 1. Onde criar — `<Cliente> › 2. Projetos › <ANO>` (o Kleber é `1. Projetos`)

A pasta do projeto fica em **`2. Projetos` → `<ANO>`** dentro da pasta do cliente no shared drive.
É assim para Elen, Letícia e Cristiane. A Daniela não tem a pasta do ano, então os projetos vão direto em
`2. Projetos`. A exceção é o Kleber, com **`1. Projetos`**. Os passos abaixo valem para os dois casos:
descubra sempre o nome real.
Descobrir dinamicamente (não assumir IDs de outro cliente):
1. `search_files` → `title contains '<Cliente>' and mimeType = 'application/vnd.google-apps.folder'`
   (escolher a do shared drive — `parentId` começa com `0A`; conferir `viewUrl`).
2. `search_files parentId = '<cliente_id>'` → achar **`1. Projetos`**.
3. `search_files parentId = '<projetos_id>'` → achar a pasta do **`<ANO>`** (ex.: `2026`).
   Se o ano não existir, **criar** a pasta do ano primeiro.
4. **Idempotência:** `search_files parentId = '<ano_id>'` e checar se já existe pasta com o nome
   `[SIGLA][TIPO][PRODUTO][MÊS][ANO]` — se existir, **não duplicar** (Drive permite nomes repetidos).

### IDs conhecidos (atalho — confirme antes de escrever)
| Cliente | Pasta cliente (shared drive) | `1.`/`2. Projetos` | `2026` |
|---|---|---|---|
| Kleber Meireles | `1urCgQguwZAjbcs1vTpf-gGcTic_Z_l4K` | `1Kj3nJXrtG9XZkBEK2MX1RU4jzuC-yVOX` (1.) | `11R1JQ5ChkjOnKyLhFXo-ZCzfHm9Gy-T5` |
| Elen Tolentino | `1H8cbSInDz33g8GxusknFIaDEsTicd9Rn` | `1sZxJWlujEtVT7iDWm8G5SoRVuZGETQEx` (2.) | `1WVSPbefdhbAWRpDYc4ItQxJz9xPTO7mM` |
| Daniela Moleiro | `1YSHwPkbP9VdckkFXRgFqcTHFXJqkpXog` | `1MUIrqD8v7ImvgADQ8WUuwRt1Jm0Xubdp` (2.) | — (direto em 2. Projetos) |

### Modo "espelhar a árvore da origem" (`scripts/espelhar_drive.py`)
Use quando o projeto de origem já adaptou a estrutura-modelo. Por exemplo, o perpétuo MCE renomeou a pasta 14
para Upsell/Remarketing e criou Brutos/Editados. Assim o destino nasce igual e os links de pasta nas descrições
remapeiam 1:1.
- Só pastas; idempotente por nome; `--excluir` pula pastas como `REGRAVAÇÃO`.
- Grava `--out mapa_drive_<proj>.json`, que o `remapear_descricoes.py` usa.
- Roda pela Drive API v3 com o token do rclone, sem MCP.
- `--verify` compara as duas árvores.

Caso real: `[ET][PEP][ESP][MCE][26]` (`1zgnyT8nETjTKrcUnc7VwqhslqvXGwgI9`, 37 pastas) espelhando `[ET][PEP][MEC][26]`.
O nome da pasta de origem tem um erro de digitação ("MEC").

> Há também uma **"Pasta padrão (COPIAR)"** na `1. Projetos` do Kleber
> (`1NeEBnAtYMDgqMcRiBQEk6KcSVCCn8xD5`) — é o modelo humano. A estrutura canônica abaixo é a fonte
> de verdade da skill (independe dela).

## 2. Estrutura-modelo (scaffold — 0 arquivos)

**Passo A — pasta principal** `[SIGLA][TIPO][PRODUTO][MÊS][ANO]` em `parentId = <ano_id>` → guardar `PROJ_ID`.

**Passo B — 18 subpastas de 1º nível** (`parentId = PROJ_ID`), nomes EXATOS (respeitar grafia/espaços):
```
0.Concepção_ Brainstorming, ideias, etc
1.Copy (Ads, scripts das lives, email, video de upsell...)
2.Disparos_ Emails, Whatsapp, Telegram.._
3. Posts Orgânicos_ Estáticos e em Vídeos (Arquivo Final)
4.Páginas_ Copy das Páginas
5.Pesquisas_ Com alunos, Com leads, etc
6.Recuperação_ Arquivos para time de Recuperação
7.Vídeos e Áudios_ Áudios CPLs, Vídepos de Vendas (Arquivo Final)
8.Listas (Email-Whatsapp)
9.Materiais Complementares_ ID visual, Ebooks, Tabelas, Posts
10.Debriefing
11.Reuniões
12.Custos
13.Depoimentos
14.Arquivo Bruto (ADS e Organico)      ← guardar id (F14_ID)
15.Arquivo Editado (Ads e Organico)    ← guardar id (F15_ID)
16.Trafego
17.Time Comercial
```

**Passo C — 6 subpastas de criativos DENTRO de `14` E de `15`** (criar nas duas: `parentId = F14_ID`
e `parentId = F15_ID`), nomes EXATOS:
```
0. Criativos Orgânico de Venda do Evento
1. Criativos ADS de Venda do Evento
2. Criativos ADS de Antecipação
3. Criativos ADS de Perseguição
4. Criativos ADS de Venda do Produto
5. Imagens da Automação de Manychat [Venda do Evento]
```

Total: **1 + 18 + 6 + 6 = 31 pastas**. Nenhum arquivo/documento.

> Dependência de IDs: B precisa de `PROJ_ID`; C precisa de `F14_ID`/`F15_ID` (vindos das respostas de B).
> As 18 chamadas de B podem ir em paralelo (mesmo parent); idem as 6+6 de C depois.

## 3. Verificação
`search_files parentId = PROJ_ID` (18 subpastas) · `parentId = F14_ID` (6) · `parentId = F15_ID` (6).
Entregar o `viewUrl` da pasta principal.

## Guardrails (Drive)
- **Só pastas, nunca documentos** — o modelo é scaffold vazio.
- **Idempotência por nome** — checar antes de criar (no ano e dentro de cada pasta) p/ não duplicar.
- Replicar a **grafia exata** do modelo (inconsistências propositais: `3. Posts` vs `15.Arquivo`).
- Confirmar a pasta do cliente certa (shared drive, `parentId` começa com `0A`) antes de escrever.
