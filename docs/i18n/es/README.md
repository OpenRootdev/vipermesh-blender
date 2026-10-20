<div align="center">

<!-- i18n:languages:start -->
[English](../../../README.md) | [Español](../es/README.md) | [简体中文](../zh-CN/README.md) | [Français](../fr/README.md) | [日本語](../ja/README.md) | [Deutsch](../de/README.md) | [Português (Brasil)](../pt-BR/README.md)
<!-- i18n:languages:end -->

<a href="https://openrootdev.github.io/vipermesh-blender/"><img src="../../../site/assets/brand-mark.png" alt="Logotipo de ViperMesh" width="104" height="104"></a>

<h1>ViperMesh for Blender</h1>
<p>Servidor MCP y addon de Blender de código abierto para agentes de IA.</p>

[![CI](https://github.com/OpenRootdev/vipermesh-blender/actions/workflows/ci.yml/badge.svg)](https://github.com/OpenRootdev/vipermesh-blender/actions/workflows/ci.yml)
[![GitHub release](https://img.shields.io/github/v/release/Ker102/vipermesh-blender?display_name=tag)](https://github.com/OpenRootdev/vipermesh-blender/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](../../../LICENSE)
[![MCP](https://img.shields.io/badge/Model_Context_Protocol-server-1f6feb)](https://modelcontextprotocol.io/)

**Asistencia de IA para Blender, con menos código y menos espera.**

Diseñado para ediciones de escena más rápidas, menos tokens de IA y resultados mejor comprobados.

<p>
<a href="https://github.com/OpenRootdev/vipermesh-blender/releases/latest"><img src="../../../site/assets/readme-download.svg" alt="Descargar addon de Blender" width="240" height="44"></a>
<a href="docs/client-setup.md"><img src="../../../site/assets/readme-setup.svg" alt="Guía de configuración" width="160" height="44"></a>
</p>

[Descripción general y configuración del proyecto](https://openrootdev.github.io/vipermesh-blender/)
| [Lista de espera de ViperMesh Studio](https://vipermesh-studio.vercel.app/waitlist)

</div>

---

ViperMesh for Blender es un **servidor MCP y addon de Blender** gratuito y de código abierto
que permite a un asistente de IA compatible trabajar dentro de tu escena de Blender. Es para
artistas de Blender, aficionados y creadores de juegos que quieren ayuda para crear y editar
escenas 3D, no otro proyecto de programación.

**El objetivo: trabajo asistido por IA más rápido, menos tokens de IA y resultados mejor comprobados.**
Tu asistente recibe acciones de Blender listas para usar en lugar de tener que escribir nuevo
código Python para muchas ediciones comunes. Tú sigues trabajando en Blender y decides con qué
quieres que el asistente te ayude.

<a id="watch-the-overview"></a>
## Ver la descripción general

[![Ver la descripción general de ViperMesh for Blender](../../../site/assets/connector-overview-poster.png)](https://openrootdev.github.io/vipermesh-blender/#overview)

[Ve el video de 72 segundos](https://openrootdev.github.io/vipermesh-blender/#overview)
o [descarga el MP4](https://openrootdev.github.io/vipermesh-blender/assets/connector-overview.mp4).
Muestra cómo tu cliente de IA usa acciones de Blender ya preparadas, por qué generar menos código
puede ayudar y cómo empezar. Es una descripción general ilustrada y silenciosa, no una
grabación cronometrada de benchmark. Los enlaces del README de GitHub llevan al video reproducible.

<a id="why-vipermesh-for-blender"></a>
## ¿Por qué ViperMesh for Blender?

| Lo que te importa | Cómo ayuda ViperMesh |
| --- | --- |
| Menos uso de IA | Las acciones reutilizables reducen el código de Blender que el asistente necesita generar para tareas cubiertas. |
| Menos espera | La conexión permanece abierta, y las acciones relacionadas pueden ejecutarse juntas en lugar de repetir la configuración en cada paso. |
| Escenas mejor comprobadas | Las comprobaciones integradas ayudan a identificar objetos flotantes, orientaciones incorrectas y problemas de holgura; el asistente puede inspeccionar imágenes y reparar errores. |
| Más fácil para tu asistente | Herramientas descubribles y guía concisa explican qué acciones están disponibles y cómo usarlas. |
| Espacio para trabajo personalizado | El asistente todavía puede escribir Python cuando tu solicitud necesita algo que las herramientas listas para usar no cubren. |

Los tokens de IA son las unidades de texto que un modelo lee y escribe. Generar menos código
puede reducir el uso de IA, pero los tokens totales, el costo y el tiempo también dependen de tu modelo
y de la tarea. Las comprobaciones de escena ayudan con la corrección; no garantizan un
resultado bonito ni libre de errores.

<a id="one-reference-two-blender-workflows"></a>
## Una referencia, dos flujos de trabajo de Blender

<p align="center">
<a href="../../../site/assets/scandinavian-entryway-comparison.png"><img src="../../../site/assets/scandinavian-entryway-comparison.png" alt="Comparación histórica de escena: imagen de referencia a la izquierda, viewport de ViperMesh MCP Blender en el centro y viewport original de BlenderMCP a la derecha" width="960"></a>
</p>

Una prueba histórica de reconstrucción de imagen usando el harness ViperMesh Blender MCP
y recursos disponibles. Solo se cambió la etiqueta del encabezado central; la
referencia y ambas capturas de escena permanecen sin cambios. Es un ejemplo,
no una garantía de todos los resultados. El addon público no incluye bibliotecas privadas
de recursos de Studio.

[Lee el caso de estudio de Blender MCP, parte uno](https://kristoferjussmann.me/case-studies/vipermesh/)
| [Abre la comparación a tamaño completo](../../../site/assets/scandinavian-entryway-comparison.png)
| [Registro de integridad de imagen](../../../site/assets/scandinavian-entryway-comparison.provenance.json)

<a id="what-can-it-help-with"></a>
## ¿Con qué puede ayudar?

- Construir, mover, duplicar y organizar objetos en una escena.
- Suavizar bordes, ajustar materiales, configurar cámaras y cambiar iluminación.
- Comprobar si los objetos se apoyan en sus soportes o dejan suficiente espacio.
- Ayudar con limpieza de malla, retopología, preparación de UV, rigging y pesos.
- Trabajar con ajustes de animación, preparar exportaciones e inspeccionar resultados.

Por ejemplo, podrías pedirle a tu asistente:

> Mueve la cesta debajo del lado derecho de la mesa, sin intersectar sus patas.

> Suaviza los bordes afilados de este mueble, manteniendo su forma general.

> Comprueba esta escena en busca de objetos sin soporte y luego muéstrame qué hay que arreglar.

Estos son ejemplos de solicitudes, no plantillas de escena preconstruidas. No necesitas
escribir Python de Blender tú mismo para las operaciones que cubren las herramientas.

<a id="how-is-it-different-from-the-original-blendermcp"></a>
## ¿En qué se diferencia del BlenderMCP original?

ViperMesh se basa en el proyecto original
[BlenderMCP de Siddharth Ahuja](https://github.com/ahujasid/mcp-for-blender),
ahora llamado MCP for Blender. La diferencia principal es su énfasis en un conjunto amplio
de acciones de edición listas para usar, flujos de trabajo reutilizables y comprobaciones de escena,
en lugar de depender de Python recién generado para ediciones comunes.

Ambos proyectos pueden inspeccionar escenas y ejecutar Python personalizado. El proyecto original
también ofrece integraciones de recursos y generación. El objetivo de ViperMesh es hacer que
las operaciones cotidianas de escena sean más eficientes en tokens, más rápidas, más simples para los asistentes
y más fáciles de validar. Esto no afirma que gane en todas las tareas ni que
el conector público incluya todas las funciones de ViperMesh Studio.

[Guía de instalación del sitio web](https://openrootdev.github.io/vipermesh-blender/setup/) · [Listado de Harness Library](https://openrootdev.github.io/harness-library/harnesses/vipermesh-blender/)

<a id="requirements"></a>
## Requisitos

- Blender 5.2 para el objetivo de versión actualmente probado
- Node.js 20 o posterior
- Un cliente compatible con MCP que admita servidores stdio

MCP, abreviatura de Model Context Protocol, es un estándar de conexión que permite a un asistente de IA
usar herramientas en otra aplicación. Necesitas una app de IA compatible con
estas conexiones; instalar solo el addon no agrega un modelo de IA a Blender.

<a id="install"></a>
## Instalar

<a id="1-install-the-blender-addon"></a>
### 1. Instala el addon de Blender

Descarga el addon `.py` versionado o el addon `.zip` desde la
[última release](https://github.com/OpenRootdev/vipermesh-blender/releases/latest).
En Blender:

1. Abre **Edit > Preferences > Add-ons**.
2. Elige **Install from Disk** y selecciona el archivo Python descargado.
3. Activa **ViperMesh for Blender**.
4. Abre la barra lateral del 3D Viewport, selecciona **ViperMesh** y haz clic en
   **Start Local Bridge**.

Mantén el puente en ejecución durante toda la sesión del agente.

<a id="2-install-the-mcp-server"></a>
### 2. Instala el servidor MCP

**Opción empaquetada:** Descarga el
[`v1.3.0` MCPB bundle](https://github.com/OpenRootdev/vipermesh-blender/releases/download/v1.3.0/vipermesh-blender-1.3.0.mcpb)
e impórtalo en un cliente que admita extensiones MCPB locales. Contiene
el servidor Node y sus dependencias, así que no necesitas clonar ni compilar el
repositorio. Node.js y el addon de Blender habilitado por separado siguen siendo necesarios.

El conector también aparece en
[Smithery](https://smithery.ai/servers/ker102/vipermesh-blender) y en el
[MCP Registry oficial](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.Ker102/vipermesh-blender).
Estos listados distribuyen el conector local, no un servicio de Blender alojado.
Consulta [configuración de distribución y bundle](docs/mcp-distribution.md) para el checksum,
la opción de extracción manual y los límites actuales de validación.

**Opción de código fuente:** Hasta que se publique el paquete npm, clónalo y compílalo:

```bash
git clone https://github.com/OpenRootdev/vipermesh-blender.git
cd vipermesh-blender
npm install
npm run build
```

<a id="3-connect-your-ai-assistant"></a>
### 3. Conecta tu asistente de IA

Al usar la importación MCPB, el cliente lee su configuración de lanzamiento desde el
bundle. Para la opción de código fuente, usa el punto de entrada compilado desde una ruta absoluta:

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

Inicia este comando una vez mediante el cliente MCP. No invoques `npm`, `npx` ni
`tsx` de nuevo para cada operación de Blender. Consulta [configuración de cliente MCP](docs/client-setup.md)
para Codex, clientes configurados por JSON, compatibilidad y la ruta opcional de Docker MCP
Toolkit.

<a id="technical-details"></a>
## Detalles técnicos

Las secciones siguientes son para configurar o desarrollar una conexión de IA. Los usuarios de Blender
pueden empezar con los pasos de instalación y las solicitudes de ejemplo anteriores.

<a id="connection-model"></a>
### Modelo de conexión

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

El servidor MCP no abre ningún listener de red. El addon de Blender escucha en
loopback de forma predeterminada e informa **Stopped**, **Ready**, **Agent connected** o
**Error** en la barra lateral de ViperMesh.

<a id="first-agent-calls"></a>
### Primeras llamadas del agente

1. Llama a `bootstrap_vipermesh_session`.
2. Inspecciona la escena con `call_blender_tool(name="get_scene_info")`.
3. Busca guía de tareas con `search_3d_guidance`.
4. Descubre solo las capacidades relevantes con `list_blender_tools`.
5. Construye, inspecciona y repara, luego finaliza y guarda.

La superficie MCP pública incluye:

- `bootstrap_vipermesh_session`
- `check_blender_connection`
- `list_blender_tools`
- `call_blender_tool`
- `call_blender_tool_batch`
- `run_blender_scene_stage`
- `get_blender_agent_context`
- `search_3d_guidance`
- `get_3d_guidance_document`

Lee el [manual completo del conector](docs/portable-blender-mcp.md) para formas de solicitud,
reglas de batching, flujos por etapas, skills de herramientas locales y
solución de problemas. El repositorio también distribuye una skill instalable de agente
[`using-vipermesh-blender`](skills/using-vipermesh-blender/SKILL.md).

<a id="security"></a>
## Seguridad

Este conector está pensado para una estación de trabajo local de confianza. `execute_code`
puede ejecutar Python arbitrario en Blender. Conecta solo clientes MCP de confianza, mantén el
puente en loopback y revisa operaciones de alto impacto o destructivas.

Consulta [SECURITY.md](SECURITY.md) para el límite de confianza y el proceso de informe privado
de vulnerabilidades.

<a id="public-connector-scope"></a>
## Alcance del conector público

Este repositorio contiene el addon de Blender de código abierto, servidor MCP portable,
skills de herramientas públicas portables y pruebas del conector. No incluye la
aplicación ViperMesh, autenticación, facturación, prompts privados, datos RAG privados,
enrutamiento de modelos en la nube, recursos privados, trazas brutas de benchmarks ni datasets
privados de evaluación. La comparación ilustrada se proporciona por separado como evidencia pública,
no como una biblioteca de recursos incluida.

El conector no incluye un proveedor comercial de generación 3D. La generación neuronal
puede agregarse más adelante mediante servicios autenticados neutrales respecto al proveedor
sin incrustar credenciales de terceros en Blender.

<a id="frequently-asked-questions"></a>
## Preguntas frecuentes

<a id="do-i-need-a-paid-vipermesh-account"></a>
### ¿Necesito una cuenta paga de ViperMesh?

No. El addon público y la conexión local son gratuitos sin una cuenta de ViperMesh.
Tu app de IA o proveedor de modelo puede cobrar por separado. El addon no
incluye acceso gratuito a modelos de IA.

<a id="do-i-need-to-be-a-programmer"></a>
### ¿Necesito ser programador?

No necesitas escribir Python para las ediciones de Blender cubiertas. La configuración inicial
todavía implica instalar el addon y conectar una app de IA compatible.
Usa el MCPB bundle en clientes que lo admitan, o compila desde el código fuente con los
comandos proporcionados. El puente de Blender habilitado por separado y la configuración del cliente hacen que
esto no sea una instalación de un clic para todos los entornos.

<a id="does-vipermesh-replace-execute_code"></a>
### ¿ViperMesh reemplaza `execute_code`?

No. Reduce Python de Blender generado innecesariamente al proporcionar operaciones
estructuradas, pero conserva `execute_code` para geometría personalizada, efectos procedurales,
grafos de nodos inusuales y flujos de trabajo no cubiertos.

<a id="why-must-the-mcp-process-stay-running"></a>
### ¿Por qué debe permanecer en ejecución el proceso MCP?

El proceso conserva una conexión serializada con Blender. Relanzarlo en
cada llamada agrega sobrecarga evitable de arranque, transporte y agente-herramienta.

<a id="does-it-require-docker"></a>
### ¿Requiere Docker?

No. Los clientes MCP locales con capacidad stdio lanzan el servidor Node directamente. Docker MCP
Toolkit es una ruta opcional de empaquetado y gateway, y todavía no es una ruta de instalación
compatible con ViperMesh porque la conectividad loopback host-a-Blender aún
requiere validación multiplataforma.

<a id="does-the-public-connector-require-vipermesh-cloud-authentication"></a>
### ¿El conector público requiere autenticación en la nube de ViperMesh?

No. El addon público y el servidor MCP local funcionan sin autenticación de ViperMesh.
Los modelos alojados futuros y la orquestación propietaria son capacidades de producto
separadas.

<a id="can-it-use-installed-blender-addons"></a>
### ¿Puede usar addons instalados de Blender?

El conector puede inspeccionar addons instalados y admite automatización local de confianza.
Las operaciones de addons desconocidos deben revisarse antes de exponerlas
como capacidades llamables por agentes.

<a id="development"></a>
## Desarrollo

```bash
npm install
npm run check
python -m py_compile addon/vipermesh-addon.py
```

Consulta [CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir un pull request.

<a id="license-and-attribution"></a>
## Licencia y atribución

ViperMesh for Blender se publica bajo la [MIT License](../../../LICENSE). Incluye
trabajo derivado de [BlenderMCP](https://github.com/ahujasid/mcp-for-blender) por
Siddharth Ahuja. Consulta [NOTICE.md](NOTICE.md) para atribución y avisos de marca.
