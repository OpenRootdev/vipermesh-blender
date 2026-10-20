<a id="install-vipermesh-blender-mcp"></a>
# Instalar ViperMesh Blender MCP

Página canónica: https://openrootdev.github.io/vipermesh-blender/setup/



← Descripción general de ViperMesh

Instala ViperMeshfor Blender.

Conecta un cliente de IA a tu escena local de Blender usando el servidor MCP y el addon.




Qué necesitas

Blender 5.2 es el objetivo de versión actualmente probado.

Node.js 20 o posterior.

Un cliente de IA que admita servidores MCP locales por stdio. Un cliente que acepte solo URLs de servidores remotos no puede conectarse directamente a esta release.

El conector es gratuito y tiene licencia MIT. Tu cliente o modelo de IA puede cobrar por separado. Docker y una cuenta de ViperMesh no son necesarios.




1. Habilita el addon de Blender

Descarga el archivo Python del addon versionado o ZIP desde la última release. En Blender, abre Edit → Preferences → Add-ons → Install from Disk, selecciona el archivo y habilita ViperMesh for Blender.

Abre la barra lateral del 3D Viewport, selecciona ViperMesh y haz clic en Start Local Bridge. Deja Blender y el puente en ejecución. La conexión predeterminada es 127.0.0.1:9876.




2. Instala el servidor MCP local

Instalación empaquetada

Descarga el bundle MCPB v1.3.0 y su checksum SHA-256. Impórtalo en un cliente que admita extensiones MCPB locales. El bundle incluye el servidor Node y dependencias; Node.js y el addon separado de Blender siguen siendo necesarios.

Sin un importador MCPB, extrae el bundle como ZIP en un directorio permanente. Configura tu cliente para lanzar node con la ruta absoluta a server/index.mjs. Sigue la guía de bundle y checksums.

Compilar desde código fuente

git clone https://github.com/OpenRootdev/vipermesh-blender.git
cd vipermesh-blender
npm install
npm run build




3. Conecta tu cliente de IA

Para la compilación desde código fuente, registra el servidor una vez usando el punto de entrada compilado. Reemplaza la ruta de ejemplo por tu propia ruta absoluta:

{
  "mcpServers": {
    "vipermesh-blender": {
      "command": "node",
      "args": ["C:/absolute/path/to/vipermesh-blender/dist/public-portable-blender-mcp.js"]
    }
  }
}

Las ubicaciones de configuración y las claves de nivel superior dependen del cliente. Consulta la guía de configuración de cliente y la documentación de tu cliente. El cliente debe mantener vivo un proceso MCP durante toda la sesión.




4. Comprueba la conexión y luego prueba una edición pequeña

Pide a tu agente que llame primero a bootstrap_vipermesh_session e inspeccione el resultado de conexión. Empieza con una solicitud pequeña, como mover un objeto o comprobar si se apoya sobre su soporte. Inspecciona la escena e imágenes resultantes antes de confiar en la edición.

Nueve herramientas MCP de nivel superior exponen descubrimiento, operaciones de escena, comprobaciones y el fallback Python. Esto no es un modelo de generación 3D alojado, y el conector público no incluye bibliotecas privadas de recursos de Studio.




Problemas comunes de configuración

Mi cliente no puede ver las herramientas

Comprueba el comando registrado y la ruta absoluta del archivo. Confirma que tu cliente admite servidores MCP stdio locales y puede lanzar Node. Recarga la conexión MCP del cliente según sus propias instrucciones.

Las herramientas aparecen, pero Blender no se conecta

Confirma que Blender está abierto, el addon está habilitado y Start Local Bridge está activo. Mantén consistentes los puertos del servidor y del puente del addon. Mantén el puente en loopback; no lo expongas públicamente.

El asistente sigue reiniciando el servidor

Configura el cliente para gestionar un subproceso persistente. Ejecutar npm, npx o tsx por separado para cada llamada de herramienta descarta la sesión existente.

¿La conexión está en sandbox?

No. Es un conector local de confianza. El fallback Python puede ejecutar código dentro de Blender. Usa clientes de confianza y revisa operaciones destructivas. Lee el límite de seguridad.


Informar un problema de configuración · Documentación para agentes · Listado de Harness Library

Configuración de cliente: https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/client-setup.md
Bundle y checksums: https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/mcp-distribution.md
Seguridad: https://github.com/OpenRootdev/vipermesh-blender/blob/main/SECURITY.md
