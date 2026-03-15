"""
Script para adicionar células markdown e comentários inline ao notebook Aula_07_MultiAg.ipynb.
Estilo baseado em Aula_04_Persist_Stream.ipynb (comentado).
"""
import json
import copy

NOTEBOOK_PATH = "notebooks/Aula_07_MultiAg.ipynb"

with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
    nb = json.load(f)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_markdown(cell_id: str, source: str) -> dict:
    return {
        "cell_type": "markdown",
        "id": cell_id,
        "metadata": {},
        "source": [source],
    }

def make_code(original: dict, new_source_lines: list[str]) -> dict:
    """Retorna cópia da célula de código com source substituído."""
    cell = copy.deepcopy(original)
    cell["source"] = new_source_lines
    return cell

# ---------------------------------------------------------------------------
# Lê as células originais indexadas por id
# ---------------------------------------------------------------------------
cells_by_id = {c["id"]: c for c in nb["cells"]}

def orig(cell_id: str) -> dict:
    """Retorna cópia profunda da célula original."""
    return copy.deepcopy(cells_by_id[cell_id])

# ---------------------------------------------------------------------------
# Constrói a nova lista de células
# ---------------------------------------------------------------------------
new_cells: list[dict] = []

# ── CÉLULA DE INTRODUÇÃO ────────────────────────────────────────────────────
new_cells.append(make_markdown("md-intro-aula07", """\
# Aula 07 — Sistema Multi-Agente para Triagem de E-mails

Este notebook implementa um **sistema multi-agente** para automatizar a triagem de e-mails de Sarah, \
uma engenheira de software sênior. O sistema decide de forma autônoma o que fazer com cada e-mail \
recebido, podendo ignorá-lo, notificar o usuário ou redigir e enviar uma resposta usando ferramentas.

## Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                     EMAIL TRIAGE AGENT                          │
│                                                                 │
│   email_input                                                   │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────┐   "ignore"  ──────────────────────► END        │
│  │triage_router│                                                │
│  │  (LLM +     │   "notify"  ──────────────────────► END        │
│  │structured   │                                                │
│  │  output)    │   "respond" ──► ┌────────────────┐             │
│  └─────────────┘                │ response_agent │             │
│                                 │  (ReAct Agent) │             │
│                                 │  ┌──────────┐  │             │
│                                 │  │   LLM    │  │             │
│                                 │  └────┬─────┘  │             │
│                                 │       │        │             │
│                                 │  ┌────▼─────┐  │             │
│                                 │  │  tools   │  │             │
│                                 │  │write_email│ │             │
│                                 │  │schedule_ │  │             │
│                                 │  │ meeting  │  │             │
│                                 │  │check_cal.│  │             │
│                                 │  └──────────┘  │             │
│                                 └────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## Conceitos Abordados

| Conceito | Descrição |
|---|---|
| `with_structured_output` | Força o LLM a retornar um objeto Pydantic tipado (classificação) |
| `Literal` | Restringe os valores possíveis da classificação a `"ignore"`, `"notify"` ou `"respond"` |
| `create_react_agent` | Cria um agente ReAct pré-construído sem precisar definir StateGraph manualmente |
| `Command` | Permite que um nó retorne roteamento + atualização de estado em um único objeto |
| `add_messages` | Reducer que acumula (em vez de substituir) a lista de mensagens no estado |

## Fluxo Geral

1. **Configuração**: carrega chaves de API e define perfil da usuária e regras de triagem
2. **Router**: classifica o e-mail com saída estruturada (Pydantic)
3. **Ferramentas**: define as ações disponíveis ao agente de resposta
4. **Agente ReAct**: usa `create_react_agent` para criar o sub-agente de resposta
5. **Grafo principal**: conecta router + agente num `StateGraph` e demonstra os dois casos\
"""))

# ── SEÇÃO 1: Configuração de Variáveis de Ambiente ─────────────────────────
new_cells.append(make_markdown("md-s1", """\
## 1. Configuração de Variáveis de Ambiente

As chaves de API são carregadas de um arquivo `.env` local (nunca hardcoded no código).

- `GEMINI_API_KEY` → mapeada para `GOOGLE_API_KEY`, que é o nome esperado pelo `langchain-google-genai`
- `TAVILY_API_KEY` → usada pelo `TavilySearch` para buscas na web (disponível ao agente de resposta)\
"""))

cell_4bcd = orig("4bcd3395")
cell_4bcd["source"] = [
    "import google.generativeai as genai\n",
    "import os\n",
    "from dotenv import load_dotenv\n",
    "\n",
    "# Carrega as variáveis do arquivo .env para os.environ\n",
    "load_dotenv()\n",
    "\n",
    "# langchain-google-genai espera a chave em GOOGLE_API_KEY;\n",
    "# fazemos o mapeamento aqui para manter o nome GEMINI_API_KEY no .env\n",
    "os.environ['GOOGLE_API_KEY'] = os.getenv('GEMINI_API_KEY') \n",
    "os.environ['TAVILY_API_KEY'] = os.getenv('TAVILY_API_KEY')",
]
new_cells.append(cell_4bcd)

# ── SEÇÃO 2: Perfil do Usuário ──────────────────────────────────────────────
new_cells.append(make_markdown("md-s2", """\
## 2. Perfil do Usuário

O `profile` centraliza as informações pessoais de Sarah que serão injetadas nos prompts \
do sistema em dois momentos distintos:

1. **Prompt de triagem** (`triage_system_prompt`): personaliza as regras de classificação \
para o contexto profissional de Sarah
2. **Prompt do agente** (`agent_system_prompt`): faz o LLM assumir o papel de assistente \
executivo *de Sarah*, usando seu nome em respostas e comunicações

Ao manter o perfil num dicionário separado, facilita a reutilização e a eventual \
personalização para outros usuários sem alterar os prompts.\
"""))
new_cells.append(orig("68ac7648"))

# ── SEÇÃO 3: Regras de Triagem ──────────────────────────────────────────────
new_cells.append(make_markdown("md-s3", """\
## 3. Regras de Triagem

`prompt_instructions` define as **três categorias de classificação** de e-mail e as \
instruções gerais do agente de resposta:

| Categoria | Critério | Ação do sistema |
|---|---|---|
| `ignore` | Newsletters, spam, comunicados gerais | Descarta silenciosamente (→ END) |
| `notify` | Build quebrado, membro doente, status de projeto | Registra, mas não responde (→ END) |
| `respond` | Pergunta de colega, solicitação de reunião, bug crítico | Aciona o agente de resposta |

Essas regras são injetadas no `triage_system_prompt` como texto plano, tornando o \
comportamento do router configurável sem necessidade de alterar o código.\
"""))
new_cells.append(orig("a1ce4a70"))

# ── SEÇÃO 4: E-mail de Exemplo ──────────────────────────────────────────────
new_cells.append(make_markdown("md-s4", """\
## 4. E-mail de Exemplo

Define um e-mail de amostra para testar o router isoladamente (seção 8). \
O e-mail é de Alice Smith, colega de equipe de Sarah, perguntando sobre endpoints \
ausentes na documentação da API — um caso claro de `"respond"` segundo as regras acima.\
"""))
new_cells.append(orig("ebea9168"))

# ── SEÇÃO 5: Imports ─────────────────────────────────────────────────────────
new_cells.append(make_markdown("md-s5", """\
## 5. Imports

| Import | Papel |
|---|---|
| `BaseModel`, `Field` | Base Pydantic para definir o schema de saída estruturada do router |
| `TypedDict` | Define o schema do estado do grafo como dicionário tipado |
| `Literal` | Restringe `classification` a um conjunto fixo de strings |
| `Annotated` | Permite anexar metadados (como reducers) a campos do estado |
| `init_chat_model` | Factory genérica de modelos LangChain (não usada diretamente aqui) |\
"""))
new_cells.append(orig("25320e58"))

# ── SEÇÃO 6: Modelo de Linguagem ─────────────────────────────────────────────
new_cells.append(make_markdown("md-s6", """\
## 6. Modelo de Linguagem

Instancia o Gemini 1.5 Flash como LLM base. Este modelo será reutilizado tanto no \
**router de triagem** (com `with_structured_output`) quanto no **agente de resposta** \
(com `create_react_agent`).

O Gemini 1.5 Flash foi escolhido por ser rápido e econômico — adequado para tarefas \
de classificação e geração de respostas curtas como e-mails.\
"""))
new_cells.append(orig("fa2485b8"))

# ── SEÇÃO 7: Router com Saída Estruturada ────────────────────────────────────
new_cells.append(make_markdown("md-s7", """\
## 7. Router com Saída Estruturada

### Por que `with_structured_output`?

Sem saída estruturada, o LLM retornaria texto livre — difícil de parsear de forma confiável. \
Usando `with_structured_output(Router)`, o LangChain instrui o modelo a retornar um objeto \
que satisfaça exatamente o schema Pydantic `Router`.

### Por que `Literal["ignore", "respond", "notify"]`?

`Literal` restringe o campo `classification` a exatamente esses três valores. Se o modelo \
tentar gerar qualquer outro valor, o Pydantic lançará um erro de validação. Isso garante \
que o roteamento condicional posterior nunca receba uma classificação inesperada.

```
LLM invocado com prompt
        │
        ▼
  gera JSON estruturado
        │
        ▼
  Pydantic valida e
  instancia Router(
    reasoning="...",
    classification="respond" | "ignore" | "notify"
  )
```\
"""))

cell_c19 = orig("c19912d4")
cell_c19["source"] = [
    "class Router(BaseModel): \n",
    '    """Analisa o e-mail não lido e o roteia de acordo com seu conteúdo."""\n',
    "\n",
    "    # O campo 'reasoning' força o modelo a explicitar o raciocínio antes de classificar,\n",
    "    # o que melhora a qualidade da classificação (chain-of-thought implícito)\n",
    "    reasoning: str = Field(\n",
    '        description="Raciocínio passo a passo por trás da classificação."\n',
    "    )\n",
    "\n",
    "    # Literal restringe os valores possíveis: Pydantic rejeita qualquer outro string\n",
    '    classification: Literal["ignore", "respond", "notify"] = Field(\n',
    "        description=\"A classificação de um e-mail: 'ignore' para e-mails irrelevantes, \"\n",
    "        \"'notify' para informações importantes que não precisam de resposta, \"\n",
    "        \"'respond' para e-mails que precisam de uma resposta\",\n",
    "    )",
]
new_cells.append(cell_c19)

# ── Criando o LLM Router ──────────────────────────────────────────────────────
new_cells.append(make_markdown("md-s7b", """\
### Criando o LLM Router

`llm.with_structured_output(Router)` cria um *runnable* que internamente:
1. Converte o schema Pydantic `Router` em um JSON Schema
2. Passa esse schema ao LLM via `tools` ou `response_format` (dependendo do provider)
3. Parseia a resposta e retorna uma instância validada de `Router`

O resultado é um objeto LangChain que se comporta como um LLM normal (aceita `.invoke()`, \
`.stream()`, etc.), mas sempre retorna uma instância de `Router`.\
"""))

cell_94a = orig("94a568b7")
cell_94a["source"] = [
    "# with_structured_output retorna um Runnable que garante saída do tipo Router\n",
    "# Internamente usa function calling ou response_format JSON do provider\n",
    "llm_router = llm.with_structured_output(Router)",
]
new_cells.append(cell_94a)

# ── SEÇÃO 8: Prompts de Triagem ───────────────────────────────────────────────
new_cells.append(make_markdown("md-s8", """\
## 8. Prompts de Triagem

Os prompts são definidos em um módulo separado (`prompts.py`) e importados aqui. \
Essa separação segue o princípio de **separação de responsabilidades**:

- O código controla a *lógica* de triagem
- O módulo `prompts` controla o *comportamento* do LLM

Os dois prompts têm papéis distintos:

| Prompt | Papel | Placeholders principais |
|---|---|---|
| `triage_system_prompt` | Define o papel do LLM e as regras de triagem | `full_name`, `triage_no`, `triage_notify`, `triage_email` |
| `triage_user_prompt` | Apresenta o e-mail a ser classificado | `author`, `to`, `subject`, `email_thread` |\
"""))
new_cells.append(orig("583c3193"))

# ── Formatando os Prompts ─────────────────────────────────────────────────────
new_cells.append(make_markdown("md-s8b", """\
### Formatando os Prompts

As variáveis do `profile` e de `prompt_instructions` são injetadas nos templates \
via `.format()`. O campo `examples=None` é um placeholder para exemplos \
few-shot — quando `None`, o template omite essa seção, mantendo o prompt conciso.\
"""))

cell_867 = orig("867606c2")
cell_867["source"] = [
    "# Injeta o perfil da usuária e as regras de triagem no prompt de sistema.\n",
    "# Cada placeholder corresponde a uma seção do template em prompts.py\n",
    "system_prompt = triage_system_prompt.format(\n",
    '    full_name=profile["full_name"],\n',
    '    name=profile["name"],\n',
    "    examples=None,  # Sem exemplos few-shot neste caso\n",
    '    user_profile_background=profile["user_profile_background"],\n',
    '    triage_no=prompt_instructions["triage_rules"]["ignore"],\n',
    '    triage_notify=prompt_instructions["triage_rules"]["notify"],\n',
    '    triage_email=prompt_instructions["triage_rules"]["respond"],\n',
    ")",
]
new_cells.append(cell_867)

cell_88c = orig("88c8dd06")
cell_88c["source"] = [
    "# Injeta os campos do e-mail de exemplo no prompt de usuário\n",
    "user_prompt = triage_user_prompt.format(\n",
    '    author=email["from"],\n',
    '    to=email["to"],\n',
    '    subject=email["subject"],\n',
    '    email_thread=email["body"],\n',
    ")",
]
new_cells.append(cell_88c)

# ── Testando o Router ─────────────────────────────────────────────────────────
new_cells.append(make_markdown("md-s8c", """\
### Testando o Router Isoladamente

Antes de integrar o router ao grafo, testamos seu funcionamento direto: \
invocamos o `llm_router` com o par system/user prompt e verificamos se a classificação \
está correta para o e-mail da Alice (esperado: `"respond"`).\
"""))
new_cells.append(orig("8863ddd4"))
new_cells.append(orig("b6ce4ce5"))

# ── SEÇÃO 9: Ferramentas do Assistente ────────────────────────────────────────
new_cells.append(make_markdown("md-s9", """\
## 9. Ferramentas do Assistente

O agente de resposta dispõe de três ferramentas que simulam ações reais de um assistente executivo:

| Ferramenta | Parâmetros | Descrição |
|---|---|---|
| `write_email` | `to`, `subject`, `content` | Redige e envia um e-mail |
| `schedule_meeting` | `attendees`, `subject`, `duration_minutes`, `preferred_day` | Agenda reunião no calendário |
| `check_calendar_availability` | `day` | Consulta horários livres num determinado dia |

O decorator `@tool` transforma cada função Python em um objeto `StructuredTool` do LangChain, \
que expõe o schema JSON dos parâmetros para que o LLM possa gerar `tool_calls` corretamente.\
"""))

new_cells.append(orig("4c4c4d46"))

cell_e5c = orig("e5cfef40")
cell_e5c["source"] = [
    "@tool\n",
    "def write_email(to: str, subject: str, content: str) -> str:\n",
    '    """Escreve e envia um e-mail."""\n',
    "    # Placeholder: em produção, integraria com Gmail API, SendGrid, etc.\n",
    "    return f\"E-mail enviado para {to} com o assunto '{subject}'\"",
]
new_cells.append(cell_e5c)

cell_8a6 = orig("8a650932")
cell_8a6["source"] = [
    "@tool\n",
    "def schedule_meeting(\n",
    "    attendees: list[str], \n",
    "    subject: str, \n",
    "    duration_minutes: int, \n",
    "    preferred_day: str\n",
    ") -> str:\n",
    '    """Agenda uma reunião no calendário."""\n',
    "    # Placeholder: em produção, integraria com Google Calendar API\n",
    "    return f\"Reunião '{subject}' agendada para {preferred_day} com {len(attendees)} participantes\"",
]
new_cells.append(cell_8a6)

cell_1ea = orig("1ea4a642")
cell_1ea["source"] = [
    "@tool\n",
    "def check_calendar_availability(day: str) -> str:\n",
    '    """Verifica a disponibilidade do calendário para um determinado dia."""\n',
    "    # Retorna slots fixos para demonstração; em produção consultaria a API do calendário\n",
    "    return f\"Horários disponíveis em {day}: 9:00 AM, 2:00 PM, 4:00 PM\"",
]
new_cells.append(cell_1ea)

# ── SEÇÃO 10: Prompt do Agente e create_prompt ────────────────────────────────
new_cells.append(make_markdown("md-s10", """\
## 10. Prompt do Agente e Função `create_prompt`

O `agent_system_prompt` define o **papel** do LLM dentro do agente de resposta: \
ele se comporta como assistente executivo de Sarah, utilizando as três ferramentas disponíveis.

### Por que `create_prompt` é uma função?

O `create_react_agent` aceita um `prompt` que pode ser:
- Uma string estática
- Uma **função** que recebe o `state` e retorna a lista de mensagens

Usar uma função permite **injetar o prompt de sistema dinamicamente**, \
mesclando os dados do `profile` e de `prompt_instructions` sem precisar \
repeti-los em cada chamada. Além disso, garante que o system prompt \
sempre aparece no início da lista de mensagens, antes do histórico acumulado.\
"""))

cell_b4b = orig("b4b71cfa")
cell_b4b["source"] = [
    "from prompts import agent_system_prompt\n",
    "\n",
    "def create_prompt(state):\n",
    "    \"\"\"Constrói a lista de mensagens para o agente de resposta.\n",
    "    \n",
    "    Injeta dinamicamente o system prompt com o perfil da usuária e\n",
    "    as instruções do agente, seguido pelo histórico de mensagens do estado.\n",
    "    \"\"\"\n",
    "    return [\n",
    "        {\n",
    '            "role": "system",\n',
    "            # Formata o prompt com o perfil da usuária (**profile expande name, full_name, etc.)\n",
    "            # e as instruções específicas do agente de resposta\n",
    '            "content": agent_system_prompt.format(\n',
    '                instructions=prompt_instructions["agent_instructions"],\n',
    "                **profile  # Expande: name, full_name, user_profile_background\n",
    "            )\n",
    "        }\n",
    "    ] + state['messages']  # Concatena com o histórico acumulado do estado",
]
new_cells.append(cell_b4b)

# Célula que imprime o agent_system_prompt
new_cells.append(orig("31d40007"))

# ── SEÇÃO 11: create_react_agent ──────────────────────────────────────────────
new_cells.append(make_markdown("md-s11", """\
## 11. Criando o Agente ReAct com `create_react_agent`

### `create_react_agent` vs `StateGraph` manual

| Abordagem | Quando usar |
|---|---|
| `create_react_agent` | Agente simples com ciclo LLM→ferramentas; sem lógica de roteamento complexa |
| `StateGraph` manual | Fluxos com múltiplos nós, condicionais customizadas, estado complexo |

`create_react_agent` é uma factory pré-construída do LangGraph que internamente cria \
um `StateGraph` com o padrão ReAct (Reasoning + Acting):

```
  state['messages']
         │
         ▼
   ┌───────────┐   tool_calls?  ┌──────────┐
   │    LLM    │──── SIM ──────►│  tools   │
   └───────────┘                └─────┬────┘
         ▲                            │
         └────────────────────────────┘
         │ NÃO
         ▼
        END
```

O parâmetro `prompt=create_prompt` passa a função de prompt dinâmico, \
garantindo que o system prompt com o perfil de Sarah seja injetado a cada ciclo.\
"""))

new_cells.append(orig("0d4f09b1"))
new_cells.append(orig("4bae9a45"))

cell_5ec = orig("5ece3a34")
cell_5ec["source"] = [
    "from langchain_google_genai import ChatGoogleGenerativeAI\n",
    "from langgraph.prebuilt import create_react_agent\n",
    "\n",
    "# Reinstancia o LLM (garante que o modelo está configurado para este agente)\n",
    "llm = ChatGoogleGenerativeAI(model=\"gemini-1.5-flash\")\n",
    "\n",
    "# create_react_agent cria internamente um StateGraph com ciclo LLM→ferramentas\n",
    "# - model: o LLM que decide quando e quais ferramentas chamar\n",
    "# - tools: lista de ferramentas disponíveis (schemas expostos ao LLM via function calling)\n",
    "# - prompt: função que injeta o system prompt dinamicamente a partir do estado\n",
    "agent = create_react_agent(\n",
    "    model=llm,  \n",
    "    tools=tools,\n",
    "    prompt=create_prompt,\n",
    ")",
]
new_cells.append(cell_5ec)

# ── Testando o Agente Diretamente ─────────────────────────────────────────────
new_cells.append(make_markdown("md-s11b", """\
### Testando o Agente Diretamente

Antes de integrar ao grafo de triagem, validamos o agente de resposta de forma isolada: \
perguntamos sobre disponibilidade no calendário e esperamos que ele chame \
`check_calendar_availability` e retorne os horários.\
"""))

cell_71b = orig("71b2a95a")
cell_71b["source"] = [
    "# Invoca o agente diretamente (fora do grafo de triagem) para validar\n",
    "# que ele consegue usar a ferramenta check_calendar_availability corretamente\n",
    "response = agent.invoke(\n",
    "    {\"messages\": [{\n",
    '        "role": "user",\n',
    '        "content": "qual é minha disponibilidade para terça-feira?"\n',
    "    }]}\n",
    ")",
]
new_cells.append(cell_71b)

cell_6c9 = orig("6c9c912c")
cell_6c9["source"] = [
    "# Exibe apenas a última mensagem (resposta final do agente ao usuário)\n",
    'response["messages"][-1].pretty_print()',
]
new_cells.append(cell_6c9)

# ── SEÇÃO 12: Estado do Grafo de Triagem ──────────────────────────────────────
new_cells.append(make_markdown("md-s12", """\
## 12. Estado do Grafo de Triagem

O `State` combina dois campos com semânticas diferentes:

| Campo | Tipo | Reducer | Comportamento |
|---|---|---|---|
| `email_input` | `dict` | (nenhum — substituição) | Sobrescrito a cada invocação do grafo |
| `messages` | `list` | `add_messages` | **Acumulado**: novas mensagens são adicionadas, nunca substituídas |

### Por que `add_messages` em vez de `operator.add`?

`add_messages` é um reducer especializado do LangGraph que, além de concatenar, \
também lida com **atualizações de mensagens existentes** (ex.: substituir uma mensagem \
pelo seu ID). É a escolha padrão para campos de histórico de chat em grafos LangGraph.\
"""))

cell_4b5 = orig("4b5d6ef7")
cell_4b5["source"] = [
    "from langgraph.graph import add_messages\n",
    "\n",
    "class State(TypedDict):\n",
    "    # email_input: recebe o e-mail a ser processado (substituído a cada invocação)\n",
    "    email_input: dict\n",
    "    \n",
    "    # messages: histórico de mensagens do agente de resposta\n",
    "    # add_messages é um reducer que ACUMULA mensagens (nunca sobrescreve)\n",
    "    # Necessário pois o response_agent retorna múltiplas mensagens (human, ai, tool, ai)\n",
    "    messages: Annotated[list, add_messages]",
]
new_cells.append(cell_4b5)

new_cells.append(orig("87a18633"))

# ── SEÇÃO 13: Nó de Triagem ───────────────────────────────────────────────────
new_cells.append(make_markdown("md-s13", """\
## 13. Nó de Triagem — `triage_router`

Este é o nó central do grafo: recebe o e-mail, classifica-o com `llm_router` e \
decide o próximo nó usando `Command`.

### O que é `Command`?

`Command` é um tipo especial do LangGraph que permite a um nó **simultaneamente**:
1. **Atualizar o estado** (`update`): adiciona mensagens, modifica campos
2. **Rotear para o próximo nó** (`goto`): determina qual nó executar a seguir

Sem `Command`, seria necessário usar uma `add_conditional_edges` separada. \
Com `Command`, o nó encapsula toda a lógica de roteamento internamente.

```python
# Padrão Command:
return Command(
    goto="response_agent",      # ← próximo nó
    update={"messages": [...]}  # ← atualização do estado
)

# Para encerrar sem atualizar:
return Command(goto=END, update=None)
```

### Tipo de retorno anotado

`Command[Literal["response_agent", "__end__"]]` declara explicitamente os destinos \
possíveis, permitindo que o LangGraph valide o roteamento em tempo de compilação.\
"""))

cell_34f = orig("34f7775a")
cell_34f["source"] = [
    "def triage_router(state: State) -> Command[\n",
    '    Literal["response_agent", "__end__"]\n',
    "]:\n",
    "    # Extrai os campos do e-mail do estado\n",
    "    author = state['email_input']['author']\n",
    "    to = state['email_input']['to']\n",
    "    subject = state['email_input']['subject']\n",
    "    email_thread = state['email_input']['email_thread']\n",
    "\n",
    "    # Formata os prompts de triagem com o perfil e as regras da usuária\n",
    "    system_prompt = triage_system_prompt.format(\n",
    "        full_name=profile[\"full_name\"],\n",
    "        name=profile[\"name\"],\n",
    "        user_profile_background=profile[\"user_profile_background\"],\n",
    "        triage_no=prompt_instructions[\"triage_rules\"][\"ignore\"],\n",
    "        triage_notify=prompt_instructions[\"triage_rules\"][\"notify\"],\n",
    "        triage_email=prompt_instructions[\"triage_rules\"][\"respond\"],\n",
    "        examples=None\n",
    "    )\n",
    "    user_prompt = triage_user_prompt.format(\n",
    "        author=author, \n",
    "        to=to, \n",
    "        subject=subject, \n",
    "        email_thread=email_thread\n",
    "    )\n",
    "\n",
    "    # Invoca o LLM router com saída estruturada (retorna instância de Router)\n",
    "    result = llm_router.invoke(\n",
    "        [\n",
    "            {\"role\": \"system\", \"content\": system_prompt},\n",
    "            {\"role\": \"user\", \"content\": user_prompt},\n",
    "        ]\n",
    "    )\n",
    "\n",
    "    if result.classification == \"respond\":\n",
    "        print(\"📧 Classificação: RESPONDER - Este e-mail requer uma resposta\")\n",
    "        goto = \"response_agent\"\n",
    "        # Injeta o e-mail completo como mensagem human para o response_agent processar\n",
    "        update = {\n",
    "            \"messages\": [\n",
    "                {\n",
    "                    \"role\": \"user\",\n",
    "                    \"content\": f\"Responda ao e-mail {state['email_input']}\",\n",
    "                }\n",
    "            ]\n",
    "        }\n",
    "    elif result.classification == \"ignore\":\n",
    "        print(\"🚫 Classificação: IGNORAR - Este e-mail pode ser ignorado com segurança\")\n",
    "        update = None  # Nenhuma atualização de estado necessária\n",
    "        goto = END\n",
    "    elif result.classification == \"notify\":\n",
    "        # Em um cenário real, isso poderia criar uma notificação ou registrar num log\n",
    "        print(\"🔔 Classificação: NOTIFICAR - Este e-mail contém informações importantes\")\n",
    "        update = None\n",
    "        goto = END\n",
    "    else:\n",
    "        raise ValueError(f\"Classificação inválida: {result.classification}\")\n",
    "\n",
    "    # Command encapsula roteamento + atualização de estado num único objeto\n",
    "    return Command(goto=goto, update=update)",
]
new_cells.append(cell_34f)

# ── SEÇÃO 14: Construindo e Compilando o Grafo ────────────────────────────────
new_cells.append(make_markdown("md-s14", """\
## 14. Construindo e Compilando o Grafo

O grafo tem uma estrutura deliberadamente simples:

```
START → triage_router → (via Command) → response_agent | END
```

- `triage_router` usa `Command` para rotear, dispensando `add_conditional_edges`
- `response_agent` é o agente ReAct criado com `create_react_agent` — \
  internamente é um sub-grafo completo (por isso `xray=True` na visualização)
- Não há `checkpointer` neste grafo: o estado não é persistido entre invocações \
  (diferente da Aula 04). Para memória persistente, veja a Aula 08.\
"""))

cell_f56 = orig("f5679abe")
cell_f56["source"] = [
    "email_agent = StateGraph(State)\n",
    "\n",
    "# Adiciona o nó de triagem: classifica o e-mail e roteia via Command\n",
    "email_agent = email_agent.add_node(\"triage_router\", triage_router)\n",
    "\n",
    "# Adiciona o agente de resposta (sub-grafo ReAct criado com create_react_agent)\n",
    "email_agent = email_agent.add_node(\"response_agent\", agent)\n",
    "\n",
    "# O grafo sempre começa pelo nó de triagem\n",
    "email_agent = email_agent.add_edge(START, \"triage_router\")\n",
    "\n",
    "# Compila o grafo (sem checkpointer: sem persistência entre invocações)\n",
    "email_agent = email_agent.compile()",
]
new_cells.append(cell_f56)

# ── SEÇÃO 15: Visualizando o Grafo ────────────────────────────────────────────
new_cells.append(make_markdown("md-s15", """\
## 15. Visualizando o Grafo

`xray=True` expande os sub-grafos internos (como o `response_agent`) na visualização, \
mostrando o ciclo LLM→ferramentas dentro do agente ReAct. Sem `xray=True`, \
`response_agent` apareceria como um único nó opaco.\
"""))

cell_328 = orig("328381f3")
cell_328["source"] = [
    "# xray=True expande os sub-grafos (ex.: response_agent) na visualização\n",
    "display(Image(email_agent.get_graph(xray=True).draw_mermaid_png()))",
]
new_cells.append(cell_328)

# ── SEÇÃO 16: Demonstrações ────────────────────────────────────────────────────
new_cells.append(make_markdown("md-s16", """\
## 16. Demonstrações — Spam e E-mail Legítimo

Testamos o sistema completo com dois casos polares:

### Caso 1: Spam (esperado: `ignore`)
Um e-mail de marketing com linguagem sensacionalista e oferta de desconto. \
O router deve reconhecer que não se enquadra em nenhuma das regras de `notify` ou `respond` \
e encerrar silenciosamente.

### Caso 2: E-mail legítimo da Alice (esperado: `respond`)
A mesma pergunta técnica sobre endpoints da API da seção 4. O router deve classificar \
como `respond` e acionar o `response_agent`, que usará `write_email` para redigir a resposta.\
"""))

# Caso 1: spam
new_cells.append(orig("095d0fe4"))

cell_910 = orig("9109cd1e")
cell_910["source"] = [
    "# Caso 1: e-mail de spam — esperamos classificação 'ignore'\n",
    "response = email_agent.invoke({\"email_input\": email_input})",
]
new_cells.append(cell_910)

# Caso 2: e-mail legítimo
new_cells.append(orig("0e726a43"))

cell_8ee = orig("8ee71852")
cell_8ee["source"] = [
    "# Caso 2: e-mail legítimo de colega — esperamos classificação 'respond'\n",
    "response = email_agent.invoke({\"email_input\": email_input})",
]
new_cells.append(cell_8ee)

cell_ee0 = orig("ee096c15")
cell_ee0["source"] = [
    "# Exibe todas as mensagens do ciclo: human → ai (tool_call) → tool → ai (resposta final)\n",
    "for m in response[\"messages\"]:\n",
    "    m.pretty_print()",
]
new_cells.append(cell_ee0)

# Célula vazia final
new_cells.append(orig("2c430199"))

# ---------------------------------------------------------------------------
# Salva o notebook modificado
# ---------------------------------------------------------------------------
nb["cells"] = new_cells

with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook salvo com {len(new_cells)} células em:")
print(NOTEBOOK_PATH)
