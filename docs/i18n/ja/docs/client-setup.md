<a id="mcp-client-setup"></a>
# MCP クライアントの設定

<a id="what-starts-what"></a>
## 起動と接続の役割

ViperMesh for Blender には、二つのローカル接続があります。

1. MCP クライアントが、長時間動作する stdio 子プロセスとして ViperMesh の Node サーバーを起動します。
2. Node サーバーが、`127.0.0.1:9876` の Blender アドオンへの直列化された TCP 接続を開き、再利用します。

サーバーのライフサイクルは MCP クライアントが管理します。サーバーをクライアントに一度登録し、そのクライアントのセッションで公開される MCP ツールを使用してください。ツールを呼び出すたびに個別の `npm`、`npx`、`tsx` コマンドを実行すると、新しいサーバープロセスが作られ、持続的な接続が破棄されます。

ローカル stdio MCP サーバーに対応するクライアントでは、Docker は不要です。

<a id="native-stdio-setup"></a>
## ネイティブ stdio の設定

リポジトリをクローンし、依存関係をインストールしてビルドします。

```bash
git clone https://github.com/OpenRootdev/vipermesh-blender.git
cd vipermesh-blender
npm install
npm run build
```

ビルドされたエントリーポイントを絶対パスで指定してください。これにより、クライアント固有の作業ディレクトリ設定に依存せずに済みます。

<a id="codex"></a>
### Codex

```bash
codex mcp add vipermesh-blender -- node C:/absolute/path/to/vipermesh-blender/dist/public-portable-blender-mcp.js
```

登録を確認します。

```bash
codex mcp list
```

現在のタスクが MCP の登録情報を再読み込みしない場合は、新しい Codex タスクを開いてください。

<a id="json-configured-clients"></a>
### JSON で設定するクライアント

Claude Desktop などのクライアントやホストは、通常、コマンドと引数の配列を受け付けます。

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

設定ファイル名と最上位のキーはクライアントによって異なります。クライアントの最新の MCP ドキュメントを参照し、コマンド自体は同等に保ってください。

<a id="client-compatibility"></a>
## クライアントの互換性

stdio を使うローカル MCP サーバーに対応し、子プロセスを起動できるクライアントは、このリリースを直接使用できます。MCP 対応というだけでは、次の違いまでは保証されません。

- ローカル stdio とリモート Streamable HTTP の両方に対応するクライアントがあります。
- リモートサーバーの URL だけに対応するクライアントもあります。
- ローカルプロセスの実行を許可するために、プラグイン、拡張機能、管理者ポリシーを必要とするものもあります。

このリリースは stdio 専用です。リモート専用のクライアントには、別途ホストされた MCP 通信経路か互換ゲートウェイが必要であり、Blender アドオンの TCP プロトコルに直接接続することはできません。

<a id="docker-mcp-toolkit"></a>
## Docker MCP Toolkit

Docker MCP Toolkit は、コンテナ化された MCP サーバーを一元管理し、対応するクライアントを stdio ゲートウェイに接続できます。これは任意の配布経路であり、ViperMesh の要件ではありません。

ViperMesh は現在、Docker MCP Catalog の項目を公開していません。Blender アドオンも、ローカルでの安全性のためにループバック限定のままです。コンテナはホストのループバックサービスに確実に到達する必要がありますが、その方法は Docker ホスト、ネットワークモード、クライアント環境によって異なります。

そのため、現在サポートされる設定はネイティブ stdio です。コンテナを接続するためだけに Blender のブリッジを公開インターフェースに露出させないでください。Windows、macOS、Linux での一連の接続テストによって安全な設定を定めた後に、Docker Toolkit の手順をサポート対象にします。

公式の参考資料:

- [MCP の通信方式](https://modelcontextprotocol.io/specification/latest/basic/transports)
- [Docker MCP Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/)

<a id="verify-the-session"></a>
## セッションの確認

1. Blender と ViperMesh のローカルブリッジを起動します。
2. 設定済みの MCP クライアントで新しいセッションを開きます。
3. `bootstrap_vipermesh_session` を呼び出します。
4. `connection.connected` が `true`、`sessionModel` が `persistent` であることを確認します。
5. 軽量な検査を二度呼び出します。新しいシェルコマンドを起動せず、同じ MCP プロセスと Blender クライアントを再利用するはずです。
