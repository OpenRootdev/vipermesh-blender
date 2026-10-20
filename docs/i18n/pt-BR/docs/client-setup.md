<a id="mcp-client-setup"></a>
# Configuração De Cliente MCP

<a id="what-starts-what"></a>
## O Que Inicia O Quê

ViperMesh for Blender tem duas conexões locais:

1. Um cliente MCP inicia o servidor Node do ViperMesh como um subprocesso stdio
   de longa duração.
2. O servidor Node abre e reutiliza uma conexão TCP serializada com o addon do
   Blender em `127.0.0.1:9876`.

O cliente MCP é responsável pelo ciclo de vida do servidor. Registre o servidor
uma vez no cliente e então use as ferramentas MCP expostas nessa sessão do
cliente. Executar um comando `npm`, `npx` ou `tsx` separado para cada chamada de
ferramenta cria um novo processo de servidor e descarta a conexão persistente.

Docker não é necessário para clientes que oferecem suporte a servidores MCP
stdio locais.

<a id="native-stdio-setup"></a>
## Configuração Stdio Nativa

Clone, instale e construa o repositório:

```bash
git clone https://github.com/OpenRootdev/vipermesh-blender.git
cd vipermesh-blender
npm install
npm run build
```

Use o ponto de entrada construído a partir de um caminho absoluto. Isso evita
depender de uma opção de diretório de trabalho específica do cliente.

<a id="codex"></a>
### Codex

```bash
codex mcp add vipermesh-blender -- node C:/absolute/path/to/vipermesh-blender/dist/public-portable-blender-mcp.js
```

Confirme o registro:

```bash
codex mcp list
```

Abra uma nova tarefa do Codex se a tarefa atual não recarregar registros MCP.

<a id="json-configured-clients"></a>
### Clientes Configurados Por JSON

Clientes como Claude Desktop e outros hosts geralmente aceitam um comando e um
array de argumentos:

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

O nome do arquivo de configuração e a chave de nível superior variam por cliente.
Use a documentação MCP atual do cliente, mas mantenha o comando em si equivalente.

<a id="client-compatibility"></a>
## Compatibilidade De Clientes

Um cliente pode usar esta release diretamente quando oferece suporte a servidores
MCP locais por stdio e consegue iniciar um subprocesso. O suporte a MCP sozinho
não garante que:

- alguns clientes ofereçam suporte a stdio local e Streamable HTTP remoto;
- alguns ofereçam suporte apenas a URLs de servidores remotos;
- alguns exijam um plugin, extensão ou política de administrador antes que a
  execução de processos locais seja permitida.

Esta release é somente stdio. Um cliente somente remoto precisa de um transporte
MCP hospedado separadamente ou de um gateway compatível; ele não consegue se
conectar diretamente ao protocolo TCP do addon do Blender.

<a id="docker-mcp-toolkit"></a>
## Docker MCP Toolkit

Docker MCP Toolkit pode centralizar servidores MCP conteinerizados e conectar
seu gateway stdio a clientes compatíveis. Ele é uma rota opcional de distribuição,
não um requisito para o ViperMesh.

O ViperMesh atualmente não publica uma entrada no Docker MCP Catalog. O addon do
Blender também permanece somente loopback por segurança local. Um contêiner deve
alcançar esse serviço de loopback do host de forma confiável, o que varia com o
host Docker, o modo de rede e o ambiente do cliente.

Por esse motivo, stdio nativo é a configuração com suporte hoje. Não exponha a
ponte do Blender em uma interface pública apenas para fazer um contêiner se
conectar. As instruções do Docker Toolkit serão promovidas a um caminho com
suporte depois que um teste de conectividade de ponta a ponta no Windows, macOS
e Linux definir uma configuração segura.

Referências oficiais:

- [Transportes MCP](https://modelcontextprotocol.io/specification/latest/basic/transports)
- [Docker MCP Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/)

<a id="verify-the-session"></a>
## Verificar A Sessão

1. Inicie o Blender e a ponte local do ViperMesh.
2. Abra uma nova sessão no cliente MCP configurado.
3. Chame `bootstrap_vipermesh_session`.
4. Confirme que `connection.connected` é `true` e que `sessionModel` é
   `persistent`.
5. Faça duas chamadas leves de inspeção. Elas devem reutilizar um processo MCP e
   um cliente Blender em vez de iniciar novos comandos shell.
