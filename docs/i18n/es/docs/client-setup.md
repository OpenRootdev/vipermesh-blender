<a id="mcp-client-setup"></a>
# Configuración de cliente MCP

<a id="what-starts-what"></a>
## Qué inicia qué

ViperMesh for Blender tiene dos conexiones locales:

1. Un cliente MCP inicia el servidor Node de ViperMesh como un subproceso stdio
   de larga duración.
2. El servidor Node abre y reutiliza una conexión TCP serializada al addon de Blender
   en `127.0.0.1:9876`.

El cliente MCP es responsable del ciclo de vida del servidor. Registra el servidor
una vez en el cliente y luego usa las herramientas MCP expuestas en esa sesión de cliente.
Ejecutar un comando `npm`, `npx` o `tsx` separado para cada llamada de herramienta crea un
nuevo proceso de servidor y descarta la conexión persistente.

Docker no es necesario para clientes que admiten servidores MCP stdio locales.

<a id="native-stdio-setup"></a>
## Configuración stdio nativa

Clona, instala y compila el repositorio:

```bash
git clone https://github.com/OpenRootdev/vipermesh-blender.git
cd vipermesh-blender
npm install
npm run build
```

Usa el punto de entrada compilado desde una ruta absoluta. Esto evita depender de una
opción de directorio de trabajo específica del cliente.

<a id="codex"></a>
### Codex

```bash
codex mcp add vipermesh-blender -- node C:/absolute/path/to/vipermesh-blender/dist/public-portable-blender-mcp.js
```

Confirma el registro:

```bash
codex mcp list
```

Abre una nueva tarea de Codex si la tarea actual no recarga registros MCP.

<a id="json-configured-clients"></a>
### Clientes configurados por JSON

Clientes como Claude Desktop y otros hosts suelen aceptar un comando y
un array de argumentos:

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

El nombre del archivo de configuración y la clave de nivel superior varían según el cliente. Usa la
documentación MCP actual del cliente, pero mantén el comando en sí equivalente.

<a id="client-compatibility"></a>
## Compatibilidad de clientes

Un cliente puede usar esta release directamente cuando admite servidores MCP locales por
stdio y puede lanzar un subproceso. El soporte MCP por sí solo no garantiza que:

- algunos clientes admitan stdio local y Streamable HTTP remoto;
- algunos admitan solo URLs de servidores remotos;
- algunos requieran un plugin, extensión o política de administrador antes de permitir la ejecución
  de procesos locales.

Esta release es solo stdio. Un cliente solo remoto necesita un transporte MCP alojado
por separado o un gateway compatible; no puede conectarse directamente al protocolo TCP
del addon de Blender.

<a id="docker-mcp-toolkit"></a>
## Docker MCP Toolkit

Docker MCP Toolkit puede centralizar servidores MCP en contenedores y conectar su
gateway stdio a clientes compatibles. Es una ruta de distribución opcional, no
un requisito para ViperMesh.

ViperMesh no publica actualmente una entrada de Docker MCP Catalog. El addon de Blender
también permanece solo en loopback por seguridad local. Un contenedor debe alcanzar
ese servicio loopback del host de forma fiable, lo que varía según el host Docker,
el modo de red y el entorno del cliente.

Por esa razón, stdio nativo es la configuración compatible hoy. No expongas el
puente de Blender en una interfaz pública solo para permitir que un contenedor se conecte. Las instrucciones de Docker
Toolkit se promoverán a una ruta compatible después de que una prueba integral
de conectividad en Windows, macOS y Linux defina una configuración segura.

Referencias oficiales:

- [Transportes MCP](https://modelcontextprotocol.io/specification/latest/basic/transports)
- [Docker MCP Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/)

<a id="verify-the-session"></a>
## Verificar la sesión

1. Inicia Blender y el puente local de ViperMesh.
2. Abre una nueva sesión en el cliente MCP configurado.
3. Llama a `bootstrap_vipermesh_session`.
4. Confirma que `connection.connected` es `true` y que `sessionModel` es
   `persistent`.
5. Haz dos llamadas ligeras de inspección. Deben reutilizar un proceso MCP y
   un cliente de Blender en lugar de iniciar nuevos comandos de shell.
