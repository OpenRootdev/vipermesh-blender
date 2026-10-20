<a id="public-connector-release-checklist"></a>
# Checklist De Release Do Conector Público

O repositório público é gerado a partir de
`config/public-blender-connector-files.json`. Nunca faça fork nem copie o
histórico do repositório privado.

<a id="current-release"></a>
## Release Atual

- Repositório: https://github.com/OpenRootdev/vipermesh-blender
- Alvo da release: https://github.com/OpenRootdev/vipermesh-blender/releases/tag/v1.3.0
- Alvo da release de origem: `v1.3.0`
- Alvo de compatibilidade do Blender: 5.2
- CI: typecheck independente, testes de conformidade, build, validação de pacote,
  auditoria npm e compilação Python do addon
- Validação histórica ao vivo (v1.2.0): descoberta MCP stdio persistente, chamadas
  de cena, mutação, prévia/finalização em estágios, salvamento, orientação local
  e fallback `execute_code`
- Verificações atuais de lançamento: conformidade de pacote isolado, transporte
  inline de imagem, estágios render-only/preserved-presentation, retenção por falha
  espacial, auditoria de dependências, compilação Python e revisão do site em
  desktop/mobile. O desempenho completo ao vivo do agente é avaliado no próximo
  piloto de demonstração.

<a id="before-export"></a>
## Antes Da Exportação

- Execute `npm run validate:public-blender-connector`.
- Execute o gateway MCP portátil e os testes focados da UI do addon.
- Compile o addon com `python -m py_compile`.
- Instale o addon gerado na release atual do Blender 5.2.
- Verifique os estados de UI Stopped, Ready, Agent connected e Error.
- Verifique bootstrap, inspeção de cena, uma mutação, inspeção de prévia,
  renderização final, salvamento e desligamento por meio de um cliente MCP novo.

<a id="export-safety"></a>
## Segurança Da Exportação

- Exporte apenas entradas do manifesto.
- Rejeite destinos duplicados, arquivos ausentes, caminhos absolutos, traversal,
  caminhos de aplicação privada, segredos, credenciais, evidência interna de
  benchmark e código de provedor específico de concorrente.
- Varra novamente o diretório gerado antes de criar o repositório GitHub.
- Crie `Ker102/vipermesh-blender` como um novo repositório sem commits privados
  herdados.

<a id="release"></a>
## Release

1. Instale dependências e execute `npm run check` no diretório gerado.
2. Empacote o addon como artefato de release.
3. Marque a versão do conector.
4. Publique o pacote MCP somente depois que o conteúdo do pacote for inspecionado.
5. Fixe o produto ViperMesh privado na versão lançada do conector.
6. Verifique o caminho de instalação público de forma independente.
7. Só então altere a visibilidade do repositório do produto ViperMesh.
