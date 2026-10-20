<a id="changelog"></a>
# Registro De Alterações

Todas as alterações notáveis no ViperMesh for Blender são documentadas aqui.

<a id="unreleased"></a>
## [Não lançado]

<a id="130---2026-10-07"></a>
## [1.3.0] - 2026-10-07

<a id="added"></a>
### Adicionado

- Visão geral no GitHub Pages conectada ao repositório, configuração e limites
  honestos de capacidade.
- Saída PNG/JPEG inline e limitada para clientes MCP com suporte a imagens.
- Diagnósticos de geometria/deformação e operações protegidas do addon já
  presentes na superfície atual de ferramentas do Blender, sincronizados na
  distribuição pública.

<a id="changed"></a>
### Alterado

- A finalização pode preservar câmera/iluminação existentes e renderizar sem
  salvar um arquivo blend. Falhas espaciais nomeadas bloqueiam a saída final e
  retêm detalhes de reparo.
- Contagens fixas de prévias foram removidas; exige revisão visual baseada na
  tarefa e declaração de defeitos não resolvidos em vez de tratar a integridade
  do arquivo como um veredito de qualidade.
- Salvamentos blend são explícitos e recusam destinos existentes na finalização
  em estágios.
- Atualizado o lock público de dependências e o piso do SDK; a auditoria de
  instalação limpa está sem achados.
- A validação de pacote verifica toda referência de skill enviada.
- Corrigidos rollback de retarget após falha de backup ou exportação, limpeza de
  importação parcial, tratamento de operador cancelado, conversão de argumentos
  enum-flag e fingerprints do addon conscientes da implementação. Regressões de
  runtime do Blender foram adicionadas.

<a id="changed-1"></a>
### Alterado

- Substituído o corpus privado exportado de guias de ferramenta por uma skill
  pública concisa e instalável para agentes, com documentos de referência
  adaptáveis.
- Adicionada configuração explícita de cliente stdio nativo e esclarecida a rota
  opcional, ainda sem suporte, do Docker MCP Toolkit.
- Adicionadas verificações de exportação que impedem conteúdo privado de
  `data/tool-guides` de entrar em releases públicos.

<a id="120---2026-07-25"></a>
## [1.2.0] - 2026-07-25

<a id="added-1"></a>
### Adicionado

- Servidor MCP stdio persistente com uma conexão serializada ao Blender por
  sessão de agente.
- Addon do Blender com estados explícitos Stopped, Ready, Agent connected e Error.
- Inspeção determinística de cena, montagem, materiais, iluminação, câmera,
  renderização, animação, rigging, UV, exportação e ferramentas de retopologia.
- Chamadas em lote limitadas e fluxos de trabalho em estágios para construção,
  inspeção de prévia e finalização.
- Bootstrap de sessão, recursos MCP, contexto operacional compacto e orientação
  de tarefas versionada para agentes novos.
- Fallback explícito `execute_code` para trabalho no Blender genuinamente
  personalizado.
- Transporte loopback somente local e validação de release público.

[Não lançado]: https://github.com/OpenRootdev/vipermesh-blender/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/OpenRootdev/vipermesh-blender/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/OpenRootdev/vipermesh-blender/releases/tag/v1.2.0
