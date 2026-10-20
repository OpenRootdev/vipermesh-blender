<a id="vipermesh-blender-mcp-server-and-addon"></a>
# ViperMesh: servidor MCP e addon para Blender

> Assistência local de IA gratuita e open-source para edição, inspeção e operações 3D reutilizáveis em cenas do Blender.

Página canônica: https://openrootdev.github.io/vipermesh-blender/
Repositório: https://github.com/OpenRootdev/vipermesh-blender
Licença: MIT, com atribuição upstream em NOTICE.md.

ViperMesh usa duas partes locais. Um cliente de IA compatível inicia um processo
MCP Node persistente sobre stdio. Esse processo se conecta ao addon do Blender
por meio de uma ponte TCP loopback serializada, por padrão 127.0.0.1:9876.

Ações prontas cobrem arranjo de cenas, materiais, iluminação, câmeras, geometria
e preparação de UV, rigging, pesos, operações de animação, exportação e
diagnósticos. Nove ferramentas MCP de nível superior expõem essas capacidades.
Agentes devem chamar bootstrap_vipermesh_session primeiro. A execução de Python
permanece disponível para trabalho personalizado.

Verificações de cena e inspeção visual ajudam um agente a reparar seu trabalho.
Menos tokens gerados, trabalho mais rápido e melhores resultados são objetivos,
não garantias universais. Os resultados dependem do modelo, da cena e da tarefa.

O conector não é um modelo hospedado de geração. Ele não inclui um modelo de IA,
roteamento em nuvem, bibliotecas privadas de assets do Studio, autenticação ou
cobrança. Docker e uma conta ViperMesh não são necessários; acesso a modelos pode
custar separadamente. Ele é um conector local confiável, não um sandbox.

<a id="install"></a>
## Instalação

Blender 5.2 é o alvo de release atualmente testado. Node.js 20+ e um cliente
capaz de MCP stdio local são necessários. Habilite o addon separado do Blender e
inicie a ponte local. Importe o bundle MCPB em um cliente compatível ou construa
o código-fonte e registre o ponto de entrada construído. Mantenha um processo em
execução durante a sessão.

- [Instalação e solução de problemas](https://openrootdev.github.io/vipermesh-blender/setup/index.md)
- [Configuração de cliente](https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/client-setup.md)
- [Bundles de release](https://github.com/OpenRootdev/vipermesh-blender/releases)
- [Manual do conector](https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/portable-blender-mcp.md)
- [Skill de agente](https://github.com/OpenRootdev/vipermesh-blender/blob/main/skills/using-vipermesh-blender/SKILL.md)
- [Limite de segurança](https://github.com/OpenRootdev/vipermesh-blender/blob/main/SECURITY.md)
- [Visão geral ilustrada](https://openrootdev.github.io/vipermesh-blender/#overview)
- [Harness Library](https://openrootdev.github.io/harness-library/harnesses/vipermesh-blender/)
