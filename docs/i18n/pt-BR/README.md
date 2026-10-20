<div align="center">

<!-- i18n:languages:start -->
[English](../../../README.md) | [Español](../es/README.md) | [简体中文](../zh-CN/README.md) | [Français](../fr/README.md) | [日本語](../ja/README.md) | [Deutsch](../de/README.md) | [Português (Brasil)](../pt-BR/README.md)
<!-- i18n:languages:end -->

<a href="https://openrootdev.github.io/vipermesh-blender/"><img src="../../../site/assets/brand-mark.png" alt="Logo do ViperMesh" width="104" height="104"></a>

<h1>ViperMesh for Blender</h1>
<p>Servidor MCP e addon open-source do Blender para agentes de IA.</p>

[![CI](https://github.com/OpenRootdev/vipermesh-blender/actions/workflows/ci.yml/badge.svg)](https://github.com/OpenRootdev/vipermesh-blender/actions/workflows/ci.yml)
[![GitHub release](https://img.shields.io/github/v/release/Ker102/vipermesh-blender?display_name=tag)](https://github.com/OpenRootdev/vipermesh-blender/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](../../../LICENSE)
[![MCP](https://img.shields.io/badge/Model_Context_Protocol-server-1f6feb)](https://modelcontextprotocol.io/)

**Assistência de IA para Blender, com menos código e menos espera.**

Projetado para edições de cena mais rápidas, menos tokens de IA e resultados
melhor verificados.

<p>
<a href="https://github.com/OpenRootdev/vipermesh-blender/releases/latest"><img src="../../../site/assets/readme-download.svg" alt="Baixar addon do Blender" width="240" height="44"></a>
<a href="docs/client-setup.md"><img src="../../../site/assets/readme-setup.svg" alt="Guia de configuração" width="160" height="44"></a>
</p>

[Visão geral e configuração do projeto](https://openrootdev.github.io/vipermesh-blender/)
| [Lista de espera do ViperMesh Studio](https://vipermesh-studio.vercel.app/waitlist)

</div>

---

ViperMesh for Blender é um **servidor MCP e addon do Blender** gratuito e
open-source que permite que um assistente de IA compatível trabalhe dentro da sua
cena do Blender. Ele é para artistas do Blender, hobbistas e criadores de jogos
que querem ajuda para criar e editar cenas 3D, não outro projeto de código.

**O objetivo: trabalho assistido por IA mais rápido, menos tokens de IA e
resultados melhor verificados.** Seu assistente recebe ações do Blender prontas
para uso em vez de precisar escrever novo código Python para muitas edições
comuns. Você continua trabalhando no Blender e decide com o que quer que o
assistente ajude.

<a id="watch-the-overview"></a>
## Assista À Visão Geral

[![Assista à visão geral do ViperMesh for Blender](../../../site/assets/connector-overview-poster.png)](https://openrootdev.github.io/vipermesh-blender/#overview)

[Assista ao vídeo de 72 segundos](https://openrootdev.github.io/vipermesh-blender/#overview)
ou [baixe o MP4](https://openrootdev.github.io/vipermesh-blender/assets/connector-overview.mp4).
Veja como seu cliente de IA usa ações prontas do Blender, por que menos código
gerado pode ajudar e como começar. Esta é uma visão geral ilustrada e silenciosa,
não uma gravação cronometrada de benchmark. Os links do README no GitHub apontam
para o vídeo reproduzível.

<a id="why-vipermesh-for-blender"></a>
## Por Que ViperMesh for Blender?

| O que importa para você | Como o ViperMesh ajuda |
| --- | --- |
| Menos uso de IA | Ações reutilizáveis reduzem o código do Blender que o assistente precisa gerar para tarefas cobertas. |
| Menos espera | A conexão permanece aberta, e ações relacionadas podem rodar juntas em vez de repetir a configuração a cada etapa. |
| Cenas melhor verificadas | Verificações integradas ajudam a identificar objetos flutuantes, orientações erradas e problemas de folga; o assistente pode inspecionar imagens e reparar erros. |
| Mais fácil para seu assistente | Ferramentas descobríveis e orientação concisa explicam quais ações estão disponíveis e como usá-las. |
| Espaço para trabalho personalizado | O assistente ainda pode escrever Python quando sua solicitação precisa de algo que as ferramentas prontas não cobrem. |

Tokens de IA são as unidades de texto que um modelo lê e escreve. Gerar menos
código pode reduzir o uso de IA, mas tokens totais, custo e tempo também dependem
do seu modelo e da tarefa. Verificações de cena ajudam na correção; elas não
garantem um resultado bonito ou livre de erros.

<a id="one-reference-two-blender-workflows"></a>
## Uma Referência, Dois Fluxos Do Blender

<p align="center">
<a href="../../../site/assets/scandinavian-entryway-comparison.png"><img src="../../../site/assets/scandinavian-entryway-comparison.png" alt="Comparação histórica de cena: imagem de referência à esquerda, viewport do ViperMesh MCP Blender no centro e viewport original do BlenderMCP à direita" width="960"></a>
</p>

Um teste histórico de reconstrução de imagem usando o harness ViperMesh Blender
MCP e assets disponíveis. Apenas o título central foi renomeado; a referência e
ambas as capturas de cena permanecem inalteradas. Este é um exemplo, não uma
garantia de todo resultado. O addon público não empacota bibliotecas privadas de
assets do Studio.

[Leia o estudo de caso Blender MCP, Parte Um](https://kristoferjussmann.me/case-studies/vipermesh/)
| [Abra a comparação em tamanho completo](../../../site/assets/scandinavian-entryway-comparison.png)
| [Registro de integridade da imagem](../../../site/assets/scandinavian-entryway-comparison.provenance.json)

<a id="what-can-it-help-with"></a>
## Com O Que Ele Pode Ajudar?

- Construir, mover, duplicar e organizar objetos em uma cena.
- Suavizar arestas, ajustar materiais, definir câmeras e alterar iluminação.
- Verificar se objetos estão apoiados em seus suportes ou deixam espaço suficiente.
- Ajudar com limpeza de malha, retopologia, preparação de UV, rigging e pesos.
- Trabalhar com configurações de animação, preparar exportações e inspecionar resultados.

Por exemplo, você poderia pedir ao seu assistente:

> Mova a cesta para baixo do lado direito da mesa, sem intersectar as pernas.

> Suavize as arestas afiadas deste móvel, mantendo sua forma geral.

> Verifique esta cena em busca de objetos sem suporte, então mostre o que precisa ser corrigido.

Estes são exemplos de solicitações, não templates de cena pré-construídos. Você
não precisa escrever Python para Blender por conta própria para as operações que
as ferramentas cobrem.

<a id="how-is-it-different-from-the-original-blendermcp"></a>
## Como Ele É Diferente Do BlenderMCP Original?

ViperMesh se baseia no
[projeto BlenderMCP original de Siddharth Ahuja](https://github.com/ahujasid/mcp-for-blender),
agora chamado MCP for Blender. A principal diferença é sua ênfase em um conjunto
amplo de ações prontas de edição, fluxos de trabalho reutilizáveis e verificações
de cena, em vez de depender de Python recém-gerado para edições comuns.

Ambos os projetos podem inspecionar cenas e executar Python personalizado. O
projeto original também oferece integrações de assets e geração. O objetivo do
ViperMesh é tornar operações cotidianas de cena mais eficientes em tokens, mais
rápidas, mais simples para assistentes usarem e mais fáceis de validar. Esta não
é uma alegação de que ele vence toda tarefa ou de que o conector público inclui
todos os recursos do ViperMesh Studio.

[Guia de instalação do site](https://openrootdev.github.io/vipermesh-blender/setup/) · [Listagem da Harness Library](https://openrootdev.github.io/harness-library/harnesses/vipermesh-blender/)

<a id="requirements"></a>
## Requisitos

- Blender 5.2 para o alvo de release atualmente testado
- Node.js 20 ou mais recente
- Um cliente compatível com MCP que ofereça suporte a servidores stdio

MCP, abreviação de Model Context Protocol, é um padrão de conexão que permite que
um assistente de IA use ferramentas em outra aplicação. Você precisa de um app de
IA que ofereça suporte a essas conexões; instalar o addon sozinho não adiciona um
modelo de IA ao Blender.

<a id="install"></a>
## Instalação

<a id="1-install-the-blender-addon"></a>
### 1. Instale O Addon Do Blender

Baixe o addon versionado `.py` ou o addon `.zip` da
[release mais recente](https://github.com/OpenRootdev/vipermesh-blender/releases/latest).
No Blender:

1. Abra **Edit > Preferences > Add-ons**.
2. Escolha **Install from Disk** e selecione o arquivo Python baixado.
3. Habilite **ViperMesh for Blender**.
4. Abra a barra lateral do 3D Viewport, selecione **ViperMesh** e clique em
   **Start Local Bridge**.

Mantenha a ponte em execução pela sessão completa do agente.

<a id="2-install-the-mcp-server"></a>
### 2. Instale O Servidor MCP

**Opção empacotada:** Baixe o
[`v1.3.0` bundle MCPB](https://github.com/OpenRootdev/vipermesh-blender/releases/download/v1.3.0/vipermesh-blender-1.3.0.mcpb)
e importe-o para um cliente que ofereça suporte a extensões MCPB locais. Ele
contém o servidor Node e suas dependências, então você não precisa clonar nem
construir o repositório. Node.js e o addon do Blender habilitado separadamente
ainda são necessários.

O conector também está listado na
[Smithery](https://smithery.ai/servers/ker102/vipermesh-blender) e no
[Registro MCP oficial](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.Ker102/vipermesh-blender).
Essas listagens distribuem o conector local, não um serviço Blender hospedado.
Consulte [configuração de distribuição e bundle](docs/mcp-distribution.md) para
o checksum, opção de extração manual e limites atuais de validação.

**Opção de código-fonte:** Até que o pacote npm seja publicado, clone e construa:

```bash
git clone https://github.com/OpenRootdev/vipermesh-blender.git
cd vipermesh-blender
npm install
npm run build
```

<a id="3-connect-your-ai-assistant"></a>
### 3. Conecte Seu Assistente De IA

Ao usar a importação MCPB, o cliente lê sua configuração de inicialização a partir
do bundle. Para a opção de código-fonte, use o ponto de entrada construído a
partir de um caminho absoluto:

```json
{
  "mcpServers": {
    "vipermesh-blender": {
      "command": "node",
      "args": [
        "C:/absolute/path/to/vipermesh-blender/dist/public-portable-blender-mcp.js"
      ]
    }
  }
}
```

Inicie este comando uma vez por meio do cliente MCP. Não invoque `npm`, `npx` ou
`tsx` novamente para cada operação do Blender. Consulte [configuração de cliente MCP](docs/client-setup.md)
para Codex, clientes configurados por JSON, compatibilidade e a rota opcional do
Docker MCP Toolkit.

<a id="technical-details"></a>
## Detalhes Técnicos

As seções abaixo são para configurar ou desenvolver uma conexão de IA. Usuários
do Blender podem começar pelas etapas de instalação e pelos exemplos de
solicitações acima.

<a id="connection-model"></a>
### Modelo De Conexão

```text
MCP-compatible AI assistant
        |
        | stdio, one long-lived process
        v
ViperMesh MCP server
        |
        | serialized loopback connection
        v
ViperMesh Blender addon (127.0.0.1:9876)
        |
        v
Blender scene
```

O servidor MCP não abre nenhum listener de rede. O addon do Blender escuta em
loopback por padrão e relata **Stopped**, **Ready**, **Agent connected** ou
**Error** na barra lateral ViperMesh.

<a id="first-agent-calls"></a>
### Primeiras Chamadas Do Agente

1. Chame `bootstrap_vipermesh_session`.
2. Inspecione a cena com `call_blender_tool(name="get_scene_info")`.
3. Busque orientação da tarefa com `search_3d_guidance`.
4. Descubra apenas as capacidades relevantes com `list_blender_tools`.
5. Construa, inspecione e repare, então finalize e salve.

A superfície MCP pública inclui:

- `bootstrap_vipermesh_session`
- `check_blender_connection`
- `list_blender_tools`
- `call_blender_tool`
- `call_blender_tool_batch`
- `run_blender_scene_stage`
- `get_blender_agent_context`
- `search_3d_guidance`
- `get_3d_guidance_document`

Leia o [manual completo do conector](docs/portable-blender-mcp.md) para formatos
de solicitação, regras de batching, fluxos de trabalho em estágios, skills locais
de ferramentas e solução de problemas. O repositório também envia uma
[skill de agente `using-vipermesh-blender`](skills/using-vipermesh-blender/SKILL.md)
instalável.

<a id="security"></a>
## Segurança

Este conector se destina a uma estação de trabalho local confiável. `execute_code`
pode executar Python arbitrário no Blender. Conecte apenas clientes MCP
confiáveis, mantenha a ponte em loopback e revise operações de alto impacto ou
destrutivas.

Consulte [SECURITY.md](SECURITY.md) para o limite de confiança e o processo de
relato privado de vulnerabilidades.

<a id="public-connector-scope"></a>
## Escopo Do Conector Público

Este repositório contém o addon open-source do Blender, o servidor MCP portátil,
as skills públicas portáteis de ferramentas e testes do conector. Ele não inclui
a aplicação ViperMesh, autenticação, cobrança, prompts privados, dados RAG
privados, roteamento de modelo em nuvem, assets privados, traces brutos de
benchmark ou datasets privados de avaliação. A comparação ilustrada é evidência
pública fornecida separadamente, não uma biblioteca de assets empacotada.

O conector não empacota um provedor comercial de geração 3D. Geração neural pode
ser adicionada depois por meio de serviços autenticados neutros em relação a
provedor, sem incorporar credenciais de terceiros no Blender.

<a id="frequently-asked-questions"></a>
## Perguntas Frequentes

<a id="do-i-need-a-paid-vipermesh-account"></a>
### Preciso De Uma Conta Paga Do ViperMesh?

Não. O addon público e a conexão local são gratuitos para uso sem uma conta
ViperMesh. Seu app de IA ou provedor de modelo pode cobrar separadamente. O addon
não inclui acesso gratuito a modelos de IA.

<a id="do-i-need-to-be-a-programmer"></a>
### Preciso Ser Programador?

Você não precisa escrever Python para as edições cobertas do Blender. A
configuração inicial ainda envolve instalar o addon e conectar um app de IA
compatível. Use o bundle MCPB em clientes que o suportam ou construa a partir do
código-fonte usando os comandos fornecidos. A ponte do Blender habilitada
separadamente e a configuração do cliente significam que isto não é uma
instalação one-click para todo ambiente.

<a id="does-vipermesh-replace-execute_code"></a>
### O ViperMesh Substitui `execute_code`?

Não. Ele reduz Python gerado desnecessariamente para Blender ao fornecer operações
estruturadas, mas mantém `execute_code` para geometria personalizada, efeitos
procedurais, grafos de nós incomuns e fluxos de trabalho não cobertos.

<a id="why-must-the-mcp-process-stay-running"></a>
### Por Que O Processo MCP Precisa Continuar Em Execução?

O processo retém uma conexão serializada com o Blender. Reiniciá-lo para cada
chamada adiciona overhead evitável de inicialização, transporte e agente-ferramenta.

<a id="does-it-require-docker"></a>
### Ele Exige Docker?

Não. Clientes MCP locais capazes de stdio iniciam o servidor Node diretamente.
Docker MCP Toolkit é uma rota opcional de empacotamento e gateway, e ainda não é
um caminho de instalação ViperMesh com suporte porque a conectividade loopback
host-para-Blender ainda exige validação multiplataforma.

<a id="does-the-public-connector-require-vipermesh-cloud-authentication"></a>
### O Conector Público Exige Autenticação Na Nuvem ViperMesh?

Não. O addon público e o servidor MCP local funcionam sem autenticação ViperMesh.
Modelos hospedados futuros e orquestração proprietária são capacidades separadas
do produto.

<a id="can-it-use-installed-blender-addons"></a>
### Ele Pode Usar Addons Instalados Do Blender?

O conector consegue inspecionar addons instalados e oferece suporte a automação
local confiável. Operações de addons desconhecidos devem ser revisadas antes de
serem expostas como capacidades chamáveis por agentes.

<a id="development"></a>
## Desenvolvimento

```bash
npm install
npm run check
python -m py_compile addon/vipermesh-addon.py
```

Consulte [CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir um pull request.

<a id="license-and-attribution"></a>
## Licença E Atribuição

ViperMesh for Blender é lançado sob a [Licença MIT](../../../LICENSE). Ele inclui
trabalho derivado de [BlenderMCP](https://github.com/ahujasid/mcp-for-blender) por
Siddharth Ahuja. Consulte [NOTICE.md](NOTICE.md) para atribuição e avisos de
marca registrada.

Prévia para desenvolvedores: a operação sem interface, os esquemas de ações e a atualização do catálogo estão descritos na [referência de execução](../../../docs/runtime-operations.md) (somente em inglês; ainda não lançado).
