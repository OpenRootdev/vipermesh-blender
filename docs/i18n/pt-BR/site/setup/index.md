<a id="install-vipermesh-blender-mcp"></a>
# Instalar ViperMesh Blender MCP

Página canônica: https://openrootdev.github.io/vipermesh-blender/setup/



← Visão geral do ViperMesh

Instale ViperMeshfor Blender.

Conecte um cliente de IA à sua cena local do Blender usando o servidor MCP e o addon.




O que você precisa

Blender 5.2 é o alvo de release atualmente testado.

Node.js 20 ou mais recente.

Um cliente de IA que oferece suporte a servidores MCP locais sobre stdio. Um cliente que aceita apenas URLs de servidores remotos não consegue se conectar diretamente a esta release.

O conector é gratuito e licenciado sob MIT. Seu cliente ou modelo de IA pode cobrar separadamente. Docker e uma conta ViperMesh não são necessários.




1. Habilite o addon do Blender

Baixe o arquivo Python ou ZIP versionado do addon a partir da release mais recente. No Blender, abra Edit → Preferences → Add-ons → Install from Disk, selecione o arquivo e habilite ViperMesh for Blender.

Abra a barra lateral do 3D Viewport, selecione ViperMesh e clique em Start Local Bridge. Deixe o Blender e a ponte em execução. A conexão padrão é 127.0.0.1:9876.




2. Instale o servidor MCP local

Instalação empacotada

Baixe o bundle MCPB v1.3.0 e seu checksum SHA-256. Importe-o para um cliente que oferece suporte a extensões MCPB locais. O bundle inclui o servidor Node e dependências; Node.js e o addon separado do Blender ainda são necessários.

Sem um importador MCPB, extraia o bundle como um ZIP para um diretório permanente. Configure seu cliente para iniciar node com o caminho absoluto para server/index.mjs. Siga o guia de bundle e checksum.

Construir a partir do código-fonte

git clone https://github.com/OpenRootdev/vipermesh-blender.git
cd vipermesh-blender
npm install
npm run build




3. Conecte seu cliente de IA

Para a build de código-fonte, registre o servidor uma vez usando o ponto de entrada construído. Substitua o caminho de exemplo pelo seu próprio caminho absoluto:

{
  "mcpServers": {
    "vipermesh-blender": {
      "command": "node",
      "args": ["C:/absolute/path/to/vipermesh-blender/dist/public-portable-blender-mcp.js"]
    }
  }
}

Locais de configuração e chaves de nível superior dependem do cliente. Consulte o guia de configuração de cliente e a documentação do seu cliente. O cliente deve manter um processo MCP ativo pela sessão completa.




4. Verifique a conexão, então tente uma pequena edição

Peça ao seu agente para chamar bootstrap_vipermesh_session primeiro e inspecione o resultado da conexão. Comece com uma solicitação pequena, como mover um objeto ou verificar se ele está apoiado em seu suporte. Inspecione a cena e as imagens resultantes antes de confiar na edição.

Nove ferramentas MCP de nível superior expõem descoberta, operações de cena, verificações e o fallback Python. Isto não é um modelo hospedado de geração 3D, e o conector público não inclui bibliotecas privadas de assets do Studio.




Problemas comuns de configuração

Meu cliente não consegue ver as ferramentas

Verifique o comando registrado e o caminho absoluto do arquivo. Confirme que seu cliente oferece suporte a servidores MCP stdio locais e consegue iniciar Node. Recarregue a conexão MCP do cliente de acordo com suas próprias instruções.

As ferramentas aparecem, mas o Blender não conecta

Confirme que o Blender está aberto, que o addon está habilitado e que Start Local Bridge está ativo. Mantenha consistentes as portas do servidor e da ponte do addon. Mantenha a ponte em loopback; não a exponha publicamente.

O assistente continua reiniciando o servidor

Configure o cliente para gerenciar um subprocesso persistente. Executar npm, npx ou tsx separadamente para cada chamada de ferramenta descarta a sessão existente.

A conexão é sandboxed?

Não. Este é um conector local confiável. O fallback Python pode executar código dentro do Blender. Use clientes confiáveis e revise operações destrutivas. Leia o limite de segurança.


Relatar um problema de configuração · Documentação para agentes · Listagem da Harness Library

Configuração de cliente: https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/client-setup.md
Bundle e checksums: https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/mcp-distribution.md
Segurança: https://github.com/OpenRootdev/vipermesh-blender/blob/main/SECURITY.md
