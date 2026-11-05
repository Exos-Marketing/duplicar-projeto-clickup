# TRAFEGO — Planejamento de Tráfego e nomenclatura das campanhas (Exos)

Padrão organizado pelo **Gabriel Gouvêa** (revisão de 23/10/26, comentário no marco
`Planejamento de Trafego [ET][BF][POS][NOV][26]`, task `17tqamemrqn`) e consolidado na página
**dash.exosmkt.com/convencoes** (precisa do login do dash; "na dúvida, é ela que vale").

**Por que importa:** o dash de tráfego **não tem cadastro manual — ele lê os nomes**. A tag do projeto
`[SIGLA][TIPO][PRODUTO][MÊS][ANO]` dentro do nome da campanha liga o gasto ao lançamento (é a mesma tag do
ClickUp, do SendFlow e da GrowAI, e é o nome do projeto no dash); o **marcador de fase** separa a verba por
fase e alimenta o CPL. Nome fora do padrão vira "(não atribuído)"/"Outros" ou **cria um projeto novo e vazio**
no dash. Na Black da ET o CPL apareceu em R$ 24,28 quando o das campanhas de cadastro era R$ 15,40, só por
nomes fora do padrão (teste de criativo sem `[CADASTROS]`, antecipação fora de colchete).

## 1. Anatomia do nome da campanha (Meta Ads)

`[PGL][SIGLA][TIPO][PRODUTO][MÊS][ANO][FASE] Texto livre [VARIANTE]`

| Bloco | O que é | Exemplo |
|---|---|---|
| `[PGL]` | Prefixo da operação de tráfego (PGL Comunicação, do Pedro Lopes, gestor de tráfego). Sempre o 1º bloco. Se o gestor mudar, confirmar o prefixo com o Gabriel. | `[PGL]` |
| `[SIGLA][TIPO][PRODUTO][MÊS][ANO]` | Tag do projeto, **idêntica** à do ClickUp e **contígua** — nada entre o código da expert e o ano | `[ET][BF][POS][NOV][26]` |
| `[FASE]` | **Um** marcador de fase, **logo depois do ano** (tabela §2) | `[CADASTROS]` |
| Sub-marcador | Só `[TESTE]`, colado ao `[CADASTROS]`, nas campanhas de teste de criativo | `[CADASTROS][TESTE]` |
| Texto livre | O que a campanha é. Traz a **temperatura** (`Frio` / `Quente`) e, se houver, a fase do lançamento por extenso (`Fase 2 - Alcance`) — nunca como colchete | `Captação Pública - Frio` |
| `[VARIANTE]` | Opcional, no fim: divisão por formato de criativo | `[ESTÁTICOS]` · `[VIDEO]` |

Exemplos reais (ET BF NOV/26, aprovados pelo Gabriel):
```
[PGL][ET][BF][POS][NOV][26][ANTECIPAÇÃO] Fase 2 - Alcance
[PGL][ET][BF][POS][NOV][26][CADASTROS][TESTE] Teste de Criativo - Frio [ESTÁTICOS]
[PGL][ET][BF][POS][NOV][26][CADASTROS][TESTE] Teste de Criativo - Quente [VIDEO]
[PGL][ET][BF][POS][NOV][26][CADASTROS] Captação Pública - Frio
[PGL][ET][BF][POS][NOV][26][CADASTROS] Captação Pública - Quente
[PGL][ET][BF][POS][NOV][26][RECONHECIMENTO] CONTAGEM REGRESSIVA
[PGL][ET][BF][POS][NOV][26][VENDAS] Vagas Abertas - Black Friday
[PGL][ET][BF][POS][NOV][26][VENDAS] Frio (condicional)
```

> O dash também aceita o marcador **antes** do código do cliente (`[PGL] [CADASTROS] [DM][LB][POS][AGO][26] Texto`,
> formato antigo que ainda roda em produção). **Em projeto novo use sempre o formato acima** (marcador depois do ano).

## 2. Marcadores de fase (um por campanha, logo após o ano)

| Fase do lançamento | Marcador obrigatório | Exemplo |
|---|---|---|
| Antecipação (alcance, sem captura) | `[ANTECIPAÇÃO]` | `…[NOV][26][ANTECIPAÇÃO] Fase 2 - Alcance` |
| Captação de leads, **inclusive teste de criativo** | `[CADASTROS]` (o `[TESTE]` pode vir junto) | `…[NOV][26][CADASTROS] Captação Pública - Frio` |
| Contagem regressiva | `[RECONHECIMENTO]` **+ a frase `CONTAGEM REGRESSIVA`** | `…[NOV][26][RECONHECIMENTO] CONTAGEM REGRESSIVA - HOJE` |
| Evento ao vivo | `[EVENTO]` ou `[AULA]` | `…[NOV][26][EVENTO] Lembrete da aula` |
| Vendas, **inclusive remarketing de vendas** | `[VENDAS]` | `…[NOV][26][VENDAS] Remarketing` |
| Carrinho aberto | `[CARRINHO]` | `…[NOV][26][CARRINHO] Última chamada` |
| Downsell | `[DOWNSELL]` | `…[NOV][26][DOWNSELL] Públicos Quentes` |
| Pesquisa pós-evento | `[PESQUISA]` | `…[NOV][26][PESQUISA] Pós-evento` |
| Reabertura / recuperação | `[REABERTURA]` ou `[RECUPERACAO]` | `…[NOV][26][REABERTURA] Última chance` |

Sinônimos que o dash ainda lê (legado — **não usar em projeto novo**): `[CADASTRO]` · `[CAPTACAO]` · `[CAP]` ·
`[VENDAS DO EVENTO]` · `[OFERTA]` · `[AO VIVO]` · a frase "carrinho aberto".

### Regras que fazem o padrão funcionar
1. **Um marcador de fase por campanha.** Dois marcadores de fases diferentes (`[CADASTROS]` e `[VENDAS]`) anulam a
   leitura e o gasto vai para "não atribuído".
2. **Posição: depois do ano** (`…[NOV][26][CADASTROS] Texto livre`). **Nunca entre o código da expert e o ano** —
   `[ET][BF][CADASTROS][POS][NOV][26]` cria um projeto novo e vazio no dash. Vale também para `[FASE 1]`/`[FASE 2]`:
   no nome da **campanha** a fase do lançamento vai no texto livre (`Fase 2 - Alcance`); colchete só na task do ClickUp.
3. **`[RECONHECIMENTO]` sozinho não é fase** — é objetivo de mídia. A contagem regressiva precisa da frase
   `CONTAGEM REGRESSIVA` no nome.
4. **Remarketing da fase de vendas leva `[VENDAS]`.** A task do ClickUp chama-se `[REMARKETING]`, mas a campanha
   precisa do marcador de vendas para o gasto entrar na verba certa.
5. **Teste de criativo é captação:** `[CADASTROS][TESTE]`. `[TESTE]` sozinho (como saiu nas Blacks da LL e da DM)
   deixa o gasto do teste fora da barra de Captura e distorce o CPL.
6. **Sem marcador composto** (`[ANTECIPAÇÃO-ELEN]`, `[VENDAS-ELEN]`): marcador puro + descrição no texto livre
   (`[ANTECIPAÇÃO] Base Alunas Elen`).
7. **Temperatura no texto livre.** O recorte quente × frio da aba Tráfego também é lido do nome: quente = `Quente`,
   `Remarketing`, `rmkt`, `retarget` (e `[RECONHECIMENTO]` com contagem regressiva); frio = `Frio`, `Lookalike`, `LAL`,
   `interesses`, `advantage`, `aberto` (exceto "carrinho aberto"). **"Frio e Quente" no mesmo nome = indefinido** —
   o dash nunca chuta. Uma campanha por temperatura.
8. **Errou o nome? Renomeia no Gerenciador** — só o nome; o dash acompanha sozinho na próxima sincronização.
   Nunca pedir mapeamento manual.

## 3. Conjuntos de anúncio (públicos)

`NN - [PLATAFORMA] [GÊNERO] [IDADE] Descrição do público`

- `NN` = ordem das camadas do público quente (`00`, `01`, `02`…). Os lookalikes (frio) vão sem número.
- `[PLATAFORMA]` = `[IG/FB]` (quente) ou `[IG]` (lookalike) · `[GÊNERO]` = `[M/H]` · `[IDADE]` = `[25-65+]`.
- Descrição = composição do público com a janela: `Visitantes do site 180D + Lista de Leads + Leads 180D`,
  `Engajamento 60D + Thruplay Reels`, `Lookalike Compradoras da Pós (ET + LL)`,
  `Leads 30D + Lista dos inscritos [ET][BF][POS][NOV][26]`, `Thruplay Ads [ET][BF][POS][NOV][26] (vencedores do teste)`.
- Exclusões numa linha própria, acima dos conjuntos: `Compradoras da Pós (histórico) --→ Negativar`.
- Estratégia de orçamento no cabeçalho da campanha: `CBO — 70% | Diária R$ …` ou `ABO (70% Leads/Inscritos / 30% Envolvimento)`.

## 4. Parâmetros de URL (UTM) — macros da conta, nunca valor fixo

Taxonomia canônica em `exosmkt.com.br/padronizacao-utm` (skill `utm-links`). No campo de parâmetros de URL:
```
utm_source=meta_ads&utm_medium={{adset.name}}&utm_campaign={{campaign.name}}&utm_content={{ad.name}}&utm_term={{placement}}
```
- `utm_content={{ad.name}}` é **obrigatório**: é o que liga cada lead ao criativo no ranking do dash.
- Valores minúsculos, sem acento; `meta_ads` unificado (o comentário do Gabriel escreveu `metaads`; a taxonomia é `meta_ads`).
- A tag de colchetes do lançamento **nunca** vai em UTM — ela é do SendFlow/GrowAI.
- Encurtador (`exosgo.link`) **não entra em anúncio**: escapa as macros e pode reprovar na revisão.
- Lead chegando com `{{adset.name}}` literal na aba Origem = anúncio com o parâmetro colado errado; conferir no Gerenciador.
- As regras de "minúsculo, sem acento, sem tag" valem para **valores digitados** (links de e-mail, WhatsApp, orgânico —
  skill `utm-links`). Nos anúncios as macros expandem para o nome da campanha/conjunto/anúncio (com a tag e tudo) —
  é exatamente isso que o dash cruza na aba Origem. Não "corrija" a macro para um valor fixo.

## 5. O marco `Planejamento de Trafego [SUFIXO]` (lista Concepção)

Fluxo: o Cleber abre → **o gestor de tráfego preenche** (Pedro Lopes) e comenta "Planejamento pronto para revisão"
→ **o Gabriel aprova** no comentário. A duplicação entrega o **esqueleto no padrão**; verba, datas, expert e
públicos são do projeto novo. Modelo real: `Planejamento de Trafego [ET][BF][POS][NOV][26]` (`17tqamemrqn`).

Estrutura da descrição:
```
Briefing:
Realizar a programação de como será executada, em cada etapa, cada campanha de tráfego do lançamento.

Planejamento Estratégico: Planejamento Estratégico [SUFIXO] (https://app.clickup.com/t/<marco>)

ESTRUTURA DE TRÁFEGO PAGO
[SUFIXO] — <Nome do lançamento>
Expert: <Prof./Dra. Nome>
Investimento total em mídia: R$ <s/imposto> (R$ <c/imposto> c/imposto)
Período: <DD/MM a DD/MM/AA>
<EXCLUSÃO OBRIGATÓRIA EM TODAS AS CAMPANHAS: …, se houver>

═══════════════════════════════
<FASE EM CAIXA ALTA: ANTECIPAÇÃO · TESTE DE CRIATIVOS · CAPTAÇÃO PÚBLICA · CONTAGEM REGRESSIVA · VENDAS …>
Objetivo: <Alcance/Engajamento | Cadastro | Reconhecimento | Conversão>
Período: <DD/MM a DD/MM (n dias)>
Verba total: R$ … (R$ … c/imposto)
Verba diária: R$ …/dia (R$ … c/imposto)
<Divisão: 70% frio / 30% quente, se houver>

[PGL][SUFIXO][FASE] <Texto livre>              ← uma linha por campanha, no padrão da §1
<CBO — 70% | Diária R$ …  ou  ABO (…)>
<Exclusões --→ Negativar>
00 - [IG/FB] [M/H] [25-65+] <público>            ← conjuntos, no padrão da §3
01 - …
(Contagem regressiva: verba por dia — "Verba DIA 30/10 (sex) — R$ 150,00 (R$ 170,75 c/imposto)")

═══════════════════════════════
RESUMO GERAL DE VERBAS
<Fase> | <período> | R$ <s/imposto> | R$ <c/imposto>    ← uma linha por fase
TOTAL MÍDIA | <período> | R$ … | R$ …

**Atividades**                                   ← o engine escreve (links das tasks de campanha)
```

## 6. Tasks de campanha (lista `Gestão de Campanhas` `901301657760`, tipo **Campanha**)

Uma task por campanha/etapa, **linkada ao marco** de Planejamento de Tráfego. Nome:
`[ETAPA][SIGLA][TIPO][PRODUTO][MÊS][ANO][<id da própria task>]` — o bloco final é o **id cru** da própria task, ex.
`[LEADS][ET][BF][POS][NOV][26][17tqamemrqt]` (no SKILL.md isso aparece como `[ID<taskid>]`, é só notação; o engine troca
o id da origem pelo novo ao criar). Canal: Meta é o padrão (sem marcador); Google leva `[GG]` depois da etapa.
A **fase do lançamento** pode ir em colchete na task, **antes da tag e sem quebrá-la**
(`[CONT REGRESSIVA][FASE 2][LL][BF][POS][OUT][26][<id>]`; o histórico tem `[LL][FASE 2][BF]…`, que quebra a busca por
sufixo) — só na task, nunca no nome da campanha.
- As duas `[LEADS]` (teste de criativos × captação pública) são **homônimas por convenção**: só o id e o bloco da
  descrição diferem. É por isso que elas duplicam em re-run do engine (memória `reference-duplicar-campanha-id-rerun-dup`).
- **Não use a palavra "Criativo" no nome da task de campanha** (ex.: `[TESTE CRIATIVOS]`): a normalização por nome do
  engine (`task_type_rules`) trocaria o tipo **Campanha** por **Criativo**.

| Task (ClickUp) | Campanha(s) no Gerenciador — marcador | Descrição da task |
|---|---|---|
| `Campanha de Antecipação [Meta][SIGLA]…` ou `[Antecipação]…` | `[ANTECIPAÇÃO]` | bloco ANTECIPAÇÃO do marco |
| `[LEADS]…` (teste de criativos) | `[CADASTROS][TESTE] … - Frio/Quente [ESTÁTICOS]`/`[VIDEO]` | bloco TESTE DE CRIATIVOS |
| `[LEADS]…` (captação pública) | `[CADASTROS] … - Frio` / `… - Quente` | bloco CAPTAÇÃO PÚBLICA |
| `[CONT REGRESSIVA]…` | `[RECONHECIMENTO] CONTAGEM REGRESSIVA` | bloco CONTAGEM REGRESSIVA (verba por dia) |
| `[LIVE OFERTA]…` | `[EVENTO]` ou `[AULA]` | lembrete do evento ao vivo |
| `[REMARKETING]…` / `[Venda do Produto]…` | `[VENDAS]` | bloco VENDAS |
| `[REMARKETING][GG]…` | Google Ads | remarketing no Google |
| `Downsell …` | `[DOWNSELL]` | bloco DOWNSELL |

Cada task de campanha carrega na descrição **o bloco da sua fase** copiado do marco (campanhas já no padrão, verba,
período, públicos) + a linha `Planejamento de Tráfego: https://app.clickup.com/t/<marco>`.

> O marco-modelo `[X°Sigla Nome do Evento] Planejamento de Trafego` (`86a52wxgk`, 2024) ainda traz o formato antigo
> `[Nome Cliente]_[X°Sigla Evento]_[CAPTAÇÃO LEADS …]_[ANO]_[FB/IG] [ID]` — **obsoleto, não usar**.

## 7. Na duplicação — o que o engine faz e o que falta

1. **Origem:** prefira um projeto cujo Planejamento de Tráfego já esteja no padrão (ET BF NOV/26, `17tqamemrqn`).
2. **`name_swaps` com o par de tags** no config — obrigatório quando a origem tem a estrutura de tráfego:
   ```json
   "name_swaps": [["[ET][BF][POS][NOV][26]", "[DM][BF][POS][NOV][26]"]]
   ```
   O engine troca o sufixo **nos nomes** (`swap_suffix`); nas **descrições** aplica só `name_swaps` + `expert_swap`.
   Sem o par, as campanhas dentro da descrição do marco e das tasks de campanha ficam com a tag da **origem** — e o
   dash ligaria o gasto ao projeto errado. Com `name_swaps` presente, ele vale também para os nomes (inclua as
   variantes de sufixo da origem, como no `config_km_apb.json`).
3. **`[ID]` das tasks de campanha:** o engine troca o id da origem pelo da task nova (nome e descrição). Em re-run as
   homônimas duplicam — ver memória `reference-duplicar-campanha-id-rerun-dup`.
4. **Depois do `--apply`, rode o conferidor** (read-only; lê o marco e, com `--campanhas`, as tasks linkadas):
   ```
   SK=~/.claude/skills/duplicar-projeto-clickup/scripts
   CLICKUP_TOKEN=$TOKEN python3 $SK/checar_trafego.py --marco <id do marco> --campanhas
   CLICKUP_TOKEN=$TOKEN python3 $SK/checar_trafego.py --sufixo "[DM][BF][POS][NOV][26]"     # acha o marco na Concepção
   python3 $SK/checar_trafego.py --texto plano.txt --sufixo "[DM][BF][POS][NOV][26]"         # texto local, sem API
   ```
   `ERRO` = o dash lê errado (sem marcador, dois marcadores, `[TESTE]` solto, marcador composto, tag quebrada,
   Frio e Quente juntos, `[RECONHECIMENTO]` sem a frase). `AVISO` = funciona, mas fora do padrão novo (marcador antes
   do código, sinônimo legado, sem temperatura, conjunto fora do padrão). Sai com código 1 se houver ERRO.
5. **Números, datas, expert e públicos são do projeto novo:** o gestor de tráfego reescreve mantendo os nomes no
   padrão; o Gabriel aprova. Antes de pedir o preenchimento, confirme que o esqueleto passou no conferidor.
6. **No Gerenciador, a campanha nasce com o nome igual ao do marco** (copiar e colar). O dash lê o Gerenciador, então
   a conferência vale lá também — se divergir, renomear no Gerenciador (regra 8 da §2).
