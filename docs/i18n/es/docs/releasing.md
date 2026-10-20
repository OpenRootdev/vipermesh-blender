<a id="public-connector-release-checklist"></a>
# Checklist de release del conector público

El repositorio público se genera desde
`config/public-blender-connector-files.json`. Nunca hagas fork ni copies el historial del
repositorio privado.

<a id="current-release"></a>
## Release actual

- Repositorio: https://github.com/OpenRootdev/vipermesh-blender
- Objetivo de release: https://github.com/OpenRootdev/vipermesh-blender/releases/tag/v1.3.0
- Objetivo de release fuente: `v1.3.0`
- Objetivo de compatibilidad de Blender: 5.2
- CI: typecheck independiente, pruebas de conformidad, build, validación de paquete, auditoría npm
  y compilación Python del addon
- Validación histórica en vivo (v1.2.0): descubrimiento MCP stdio persistente, llamadas de escena, mutación,
  vista previa/finalización por etapas, guardado, guía local y fallback `execute_code`
- Comprobaciones de lanzamiento actuales: conformidad de paquete aislado, transporte de imagen inline,
  etapas de solo render/presentación preservada, retención ante fallo espacial,
  auditoría de dependencias, compilación Python y revisión del sitio desktop/mobile. El rendimiento completo
  de agente en vivo se evalúa en el siguiente piloto de demo.

<a id="before-export"></a>
## Antes de exportar

- Ejecuta `npm run validate:public-blender-connector`.
- Ejecuta el gateway MCP portable y las pruebas enfocadas de UI del addon.
- Compila el addon con `python -m py_compile`.
- Instala el addon generado en la versión actual de Blender 5.2.
- Verifica los estados de UI Stopped, Ready, Agent connected y Error.
- Verifica bootstrap, inspección de escena, una mutación, inspección de vista previa, render final,
  guardado y apagado mediante un cliente MCP nuevo.

<a id="export-safety"></a>
## Seguridad de exportación

- Exporta solo entradas del manifiesto.
- Rechaza destinos duplicados, archivos faltantes, rutas absolutas, traversal, rutas de aplicaciones
  privadas, secretos, credenciales, evidencia interna de benchmarks y
  código de proveedor específico de competidor.
- Escanea otra vez el directorio generado antes de crear el repositorio de GitHub.
- Crea `Ker102/vipermesh-blender` como un repositorio nuevo sin commits privados
  heredados.

<a id="release"></a>
## Release

1. Instala dependencias y ejecuta `npm run check` en el directorio generado.
2. Empaqueta el addon como artefacto de release.
3. Etiqueta la versión del conector.
4. Publica el paquete MCP solo después de inspeccionar su contenido.
5. Fija el producto privado ViperMesh a la versión del conector publicada.
6. Verifica la ruta de instalación pública de forma independiente.
7. Solo entonces cambia la visibilidad del repositorio del producto ViperMesh.
