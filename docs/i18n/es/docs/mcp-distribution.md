<a id="mcp-distribution"></a>
# Distribución MCP

ViperMesh for Blender se publica como un conector stdio local. No
aloja Blender, proporciona un modelo de IA ni incluye ViperMesh Studio privado y
su harness completo con benchmarks.

<a id="published-listings"></a>
## Listados publicados

- [Smithery: ker102/vipermesh-blender](https://smithery.ai/servers/ker102/vipermesh-blender)
- [MCP Registry oficial: io.github.Ker102/vipermesh-blender](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.Ker102/vipermesh-blender)
- [Release de GitHub v1.3.0](https://github.com/OpenRootdev/vipermesh-blender/releases/tag/v1.3.0)

El registro oficial aloja metadatos. El paquete MCPB se aloja en la
release de GitHub. El listado de Smithery también contiene el mismo bundle y los nueve
esquemas de herramientas MCP descubiertos desde el servidor empaquetado.

<a id="bundle-setup"></a>
## Configuración del bundle

1. Instala y activa el addon de Blender usando la [guía principal de instalación](../README.md#install).
2. Descarga [vipermesh-blender-1.3.0.mcpb](https://github.com/OpenRootdev/vipermesh-blender/releases/download/v1.3.0/vipermesh-blender-1.3.0.mcpb)
   y su [archivo SHA-256](https://github.com/OpenRootdev/vipermesh-blender/releases/download/v1.3.0/vipermesh-blender-1.3.0.mcpb.sha256).
3. Importa el bundle en un cliente compatible con MCPB, siguiendo las instrucciones
   de extensión local de ese cliente. Node.js es requerido por la configuración de lanzamiento
   del bundle. Mantén el puerto del puente en `9876` salvo que tu addon use un
   puerto diferente.
4. Inicia el puente local de Blender, luego llama a `bootstrap_vipermesh_session`
   desde el cliente de IA e inspecciona el resultado de conexión.

Los clientes sin importaciones MCPB pueden usar la [instalación desde código fuente](client-setup.md).
Como alternativa, el MCPB es un archivo ZIP: extráelo en un directorio permanente
y registra `node` con la ruta absoluta a `server/index.mjs` como argumento.
El paquete extraído contiene sus dependencias de runtime y guía local;
no se necesita `npm install`. Inícialo una vez como subproceso stdio persistente,
no una vez por operación de Blender.

El puente permanece en `127.0.0.1`. Los clientes solo remotos no pueden usar directamente este
conector local. No expongas públicamente el puente de Blender para hacer que se conecten.

<a id="release-integrity-and-validation"></a>
## Integridad y validación de la release

La versión `1.3.0` se compila desde el commit fuente
`781700be4f0fb32b135d3f5cb7da012ce8fc4abd`.

Bundle SHA-256:

```text
45f8cee90540e9f906b8e817efb6fa0a1302f8dba515522dc3682d328a90206c
```

Las comprobaciones de TypeScript fuente y conformidad, sintaxis Python del addon, validación
de esquema de paquete, inicialización MCP, descubrimiento de nueve herramientas y búsquedas de guía local
pasaron. La descarga de release se comprobó contra este checksum antes de la
publicación en el registro.

Estas comprobaciones de paquete no establecen compatibilidad en vivo con Blender para cada
cliente. Una prueba de escena en vivo y una prueba integral de instalación MCPB siguen pendientes
para este bundle. Prueba en una escena descartable, revisa las operaciones destructivas
y sigue la [guía de seguridad](../SECURITY.md).

<a id="maintainer-notes"></a>
## Notas para mantenedores

Los metadatos publicados del registro se rastrean en [server.json](../../../../server.json).
Para una nueva release, recompila y valida el bundle, sube sus bytes exactos y
checksum a la release, luego actualiza la versión, commit fuente, URL de descarga
y hash en conjunto antes de publicar metadatos.

El manifiesto MCPB enumera nombres de herramientas. La publicación en Smithery además necesita
los esquemas completos de `tools/list` del servidor empaquetado; los nombres por sí solos no
satisfacen su validación de server-card. Mantén esos esquemas consistentes con la
release en lugar de inventar o eliminar definiciones de herramientas.
