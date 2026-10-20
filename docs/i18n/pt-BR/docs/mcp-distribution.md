<a id="mcp-distribution"></a>
# Distribuição MCP

ViperMesh for Blender é publicado como um conector stdio local. Ele não hospeda
o Blender, não fornece um modelo de IA e não inclui o ViperMesh Studio privado
nem seu harness completo com benchmark.

<a id="published-listings"></a>
## Listagens Publicadas

- [Smithery: ker102/vipermesh-blender](https://smithery.ai/servers/ker102/vipermesh-blender)
- [Registro MCP Oficial: io.github.Ker102/vipermesh-blender](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.Ker102/vipermesh-blender)
- [Release GitHub v1.3.0](https://github.com/OpenRootdev/vipermesh-blender/releases/tag/v1.3.0)

O registro oficial hospeda metadados. O pacote MCPB é hospedado na release do
GitHub. A listagem da Smithery também contém o mesmo bundle e os nove esquemas
de ferramentas MCP descobertos a partir do servidor empacotado.

<a id="bundle-setup"></a>
## Configuração Do Bundle

1. Instale e habilite o addon do Blender usando o [guia principal de instalação](../README.md#install).
2. Baixe [vipermesh-blender-1.3.0.mcpb](https://github.com/OpenRootdev/vipermesh-blender/releases/download/v1.3.0/vipermesh-blender-1.3.0.mcpb)
   e seu [arquivo SHA-256](https://github.com/OpenRootdev/vipermesh-blender/releases/download/v1.3.0/vipermesh-blender-1.3.0.mcpb.sha256).
3. Importe o bundle em um cliente compatível com MCPB, seguindo as instruções de
   extensão local desse cliente. Node.js é exigido pela configuração de inicialização
   do bundle. Mantenha a porta da ponte em `9876`, a menos que seu addon use uma
   porta diferente.
4. Inicie a ponte local do Blender, então chame `bootstrap_vipermesh_session`
   a partir do cliente de IA e inspecione o resultado da conexão.

Clientes sem importação MCPB podem usar a [instalação a partir do código-fonte](client-setup.md).
Como alternativa, o MCPB é um arquivo ZIP: extraia-o para um diretório permanente
e registre `node` com o caminho absoluto para `server/index.mjs` como argumento.
O pacote extraído contém suas dependências de runtime e orientação local; nenhum
`npm install` é necessário. Inicie-o uma vez como um subprocesso stdio persistente,
não uma vez por operação do Blender.

A ponte permanece em `127.0.0.1`. Clientes somente remotos não conseguem usar
diretamente este conector local. Não exponha publicamente a ponte do Blender para
fazê-los se conectar.

<a id="release-integrity-and-validation"></a>
## Integridade E Validação Da Release

A versão `1.3.0` é construída a partir do commit de origem
`781700be4f0fb32b135d3f5cb7da012ce8fc4abd`.

SHA-256 do bundle:

```text
45f8cee90540e9f906b8e817efb6fa0a1302f8dba515522dc3682d328a90206c
```

Verificações TypeScript e de conformidade do código-fonte, sintaxe Python do
addon, validação de esquema de pacote, inicialização MCP, descoberta de nove
ferramentas e consultas de orientação local foram aprovadas. O download da
release foi conferido contra este checksum antes da publicação no registro.

Essas verificações de pacote não estabelecem compatibilidade ao vivo com o
Blender para todo cliente. Um teste de cena ao vivo e um teste de instalação
MCPB de ponta a ponta permanecem pendentes para este bundle. Teste em uma cena
descartável, revise operações destrutivas e siga a [orientação de segurança](../SECURITY.md).

<a id="maintainer-notes"></a>
## Notas Para Mantenedores

Os metadados publicados no registro são rastreados em [server.json](../../../../server.json).
Para uma nova release, reconstrua e valide o bundle, envie seus bytes exatos e
checksum para a release, então atualize a versão, o commit de origem, a URL de
download e o hash juntos antes de publicar metadados.

O manifesto MCPB lista nomes de ferramentas. A publicação na Smithery também
precisa dos esquemas completos de `tools/list` do servidor empacotado; nomes
sozinhos não satisfazem sua validação de server-card. Mantenha esses esquemas
consistentes com a release em vez de inventar ou remover definições de ferramenta.
