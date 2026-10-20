<a id="vipermesh-blender-mcp-server-and-addon"></a>
# ViperMesh: servidor MCP y addon de Blender

> Asistencia de IA local, gratuita y de código abierto para edición, inspección y operaciones 3D reutilizables en escenas de Blender.

Página canónica: https://openrootdev.github.io/vipermesh-blender/
Repositorio: https://github.com/OpenRootdev/vipermesh-blender
Licencia: MIT, con atribución upstream en NOTICE.md.

ViperMesh usa dos partes locales. Un cliente de IA compatible lanza un proceso MCP Node persistente por stdio. Ese proceso se conecta al addon de Blender mediante un puente TCP loopback serializado, por defecto 127.0.0.1:9876.

Las acciones listas para usar cubren organización de escena, materiales, iluminación, cámaras, preparación de geometría y UV, rigging, pesos, operaciones de animación, exportación y diagnósticos. Nueve herramientas MCP de nivel superior exponen estas capacidades. Los agentes deben llamar primero a bootstrap_vipermesh_session. La ejecución Python sigue disponible para trabajo personalizado.

Las comprobaciones de escena y la inspección visual ayudan a un agente a reparar su trabajo. Menos tokens generados, trabajo más rápido y mejores resultados son objetivos, no garantías universales. Los resultados dependen del modelo, la escena y la tarea.

El conector no es un modelo de generación alojado. No incluye un modelo de IA, enrutamiento en la nube, bibliotecas privadas de recursos de Studio, autenticación ni facturación. Docker y una cuenta de ViperMesh no son necesarios; el acceso al modelo puede costar por separado. Es un conector local de confianza, no un sandbox.

<a id="install"></a>
## Instalar

Blender 5.2 es el objetivo de versión actualmente probado. Se requiere Node.js 20+ y un cliente capaz de MCP stdio local. Habilita el addon separado de Blender e inicia el puente local. Importa el bundle MCPB en un cliente compatible, o compila el código fuente y registra el punto de entrada compilado. Mantén un proceso en ejecución para la sesión.

- [Instalación y solución de problemas](https://openrootdev.github.io/vipermesh-blender/setup/index.md)
- [Configuración de cliente](https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/client-setup.md)
- [Bundles de release](https://github.com/OpenRootdev/vipermesh-blender/releases)
- [Manual del conector](https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/portable-blender-mcp.md)
- [Skill de agente](https://github.com/OpenRootdev/vipermesh-blender/blob/main/skills/using-vipermesh-blender/SKILL.md)
- [Límite de seguridad](https://github.com/OpenRootdev/vipermesh-blender/blob/main/SECURITY.md)
- [Descripción general ilustrada](https://openrootdev.github.io/vipermesh-blender/#overview)
- [Harness Library](https://openrootdev.github.io/harness-library/harnesses/vipermesh-blender/)
