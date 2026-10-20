<a id="changelog"></a>
# Registro de cambios

Todos los cambios destacables de ViperMesh for Blender se documentan aquí.

<a id="unreleased"></a>
## [Sin publicar]

<a id="130---2026-10-07"></a>
## [1.3.0] - 2026-10-07

<a id="added"></a>
### Agregado

- Descripción general, configuración y límites honestos de capacidades en GitHub Pages conectado al repositorio.
- Salida PNG/JPEG acotada e inline para clientes MCP con capacidad de imagen.
- Diagnósticos de geometría/deformación y operaciones protegidas del addon ya presentes
  en la superficie actual de herramientas de Blender, sincronizados con la distribución pública.

<a id="changed"></a>
### Cambiado

- La finalización puede preservar cámara/iluminación existentes y renderizar sin guardar un archivo blend.
  Los fallos espaciales nombrados bloquean la salida final y conservan detalles de reparación.
- Se eliminaron los recuentos fijos de vistas previas; se requiere revisión visual basada en la tarea y divulgar
  defectos sin resolver en lugar de tratar la salud del archivo como veredicto de calidad.
- Los guardados Blend son explícitos y rechazan destinos existentes en la finalización por etapas.
- Se actualizó el bloqueo de dependencias público y el piso del SDK; la auditoría de instalación limpia queda clara.
- La validación del paquete comprueba cada referencia de skill enviada.
- Se corrigieron la reversión de retarget tras fallo de copia de seguridad o exportación, la limpieza de importación parcial,
  el manejo de operadores cancelados, la conversión de argumentos enum-flag y
  las huellas del addon conscientes de la implementación. Se agregaron regresiones de runtime de Blender.

<a id="changed-1"></a>
### Cambiado

- Se reemplazó el corpus exportado de guías de herramientas privadas por una skill pública concisa,
  instalable para agentes, y documentos de referencia adaptables.
- Se agregó configuración explícita de cliente stdio nativo y se aclaró la ruta opcional,
  aún no compatible, de Docker MCP Toolkit.
- Se agregaron comprobaciones de exportación que impiden que contenido privado de `data/tool-guides`
  entre en versiones públicas.

<a id="120---2026-07-25"></a>
## [1.2.0] - 2026-07-25

<a id="added-1"></a>
### Agregado

- Servidor MCP stdio persistente con una conexión de Blender serializada por sesión
  de agente.
- Addon de Blender con estados explícitos Stopped, Ready, Agent connected y Error.
- Herramientas deterministas de inspección de escena, ensamblaje, materiales, iluminación, cámara,
  renderizado, animación, rigging, UV, exportación y retopología.
- Llamadas batch acotadas y flujos de trabajo por etapas de construcción, inspección de vista previa y finalización.
- Bootstrap de sesión, recursos MCP, contexto operativo compacto y guía de tareas versionada
  para agentes nuevos.
- Fallback explícito `execute_code` para trabajo de Blender genuinamente personalizado.
- Transporte local-only por loopback y validación de release pública.

[Sin publicar]: https://github.com/OpenRootdev/vipermesh-blender/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/OpenRootdev/vipermesh-blender/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/OpenRootdev/vipermesh-blender/releases/tag/v1.2.0
