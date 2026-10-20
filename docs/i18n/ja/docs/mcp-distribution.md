<a id="mcp-distribution"></a>
# MCP の配布

ViperMesh for Blender は、ローカル stdio コネクタとして公開されています。Blender をホストしたり AI モデルを提供したりするものではなく、非公開の ViperMesh Studio や、その完全なベンチマーク済み実行・検証フレームワークも含みません。

<a id="published-listings"></a>
## 公開されている掲載先

- [Smithery: ker102/vipermesh-blender](https://smithery.ai/servers/ker102/vipermesh-blender)
- [公式 MCP Registry: io.github.Ker102/vipermesh-blender](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.Ker102/vipermesh-blender)
- [GitHub リリース v1.3.0](https://github.com/OpenRootdev/vipermesh-blender/releases/tag/v1.3.0)

公式レジストリがホストするのはメタデータです。MCPB パッケージは GitHub のリリースでホストされています。Smithery の掲載情報にも、同じバンドルと、パッケージ化されたサーバーから検出した九つの MCP ツールのスキーマが含まれています。

<a id="bundle-setup"></a>
## バンドルの設定

1. [主なインストール手順](../README.md#install)に従って Blender アドオンをインストールし、有効にします。
2. [vipermesh-blender-1.3.0.mcpb](https://github.com/OpenRootdev/vipermesh-blender/releases/download/v1.3.0/vipermesh-blender-1.3.0.mcpb) と、その [SHA-256 ファイル](https://github.com/OpenRootdev/vipermesh-blender/releases/download/v1.3.0/vipermesh-blender-1.3.0.mcpb.sha256) をダウンロードします。
3. クライアントのローカル拡張機能の手順に従い、MCPB 対応クライアントにバンドルをインポートします。バンドルの起動設定には Node.js が必要です。アドオンが別のポートを使わない限り、ブリッジのポートは `9876` のままにしてください。
4. Blender のローカルブリッジを起動し、AI クライアントから `bootstrap_vipermesh_session` を呼び出して接続結果を確認します。

MCPB のインポート機能がないクライアントは、[ソースからのインストール](client-setup.md)を使用できます。また、MCPB は ZIP アーカイブなので、常設のディレクトリに展開し、`node` をコマンド、`server/index.mjs` の絶対パスを引数として登録できます。展開されたパッケージには実行時の依存関係とローカルガイダンスが含まれるため、`npm install` は不要です。Blender 操作ごとではなく、持続的な stdio 子プロセスとして一度だけ起動してください。

ブリッジは `127.0.0.1` のままにします。リモート専用クライアントはこのローカルコネクタを直接使用できません。接続のために Blender のブリッジを公開しないでください。

<a id="release-integrity-and-validation"></a>
## リリースの整合性と検証

バージョン `1.3.0` は、ソースコミット
`781700be4f0fb32b135d3f5cb7da012ce8fc4abd` からビルドされています。

バンドルの SHA-256:

```text
45f8cee90540e9f906b8e817efb6fa0a1302f8dba515522dc3682d328a90206c
```

ソース TypeScript と適合性の検査、アドオンの Python 構文、パッケージスキーマ検証、MCP 初期化、九つのツールの検出、ローカルガイダンスの検索は合格しています。レジストリへの公開前に、リリースのダウンロードをこのチェックサムと照合しました。

これらのパッケージ検査は、すべてのクライアントで実際の Blender との互換性を証明するものではありません。このバンドルの実際のシーンでのテストと、MCPB インストールの一連のテストはまだ未完了です。使い捨てのシーンで試し、破壊的な操作を確認し、[セキュリティ指針](../SECURITY.md)に従ってください。

<a id="maintainer-notes"></a>
## メンテナー向けの注意事項

公開されたレジストリのメタデータは [server.json](../../../../server.json) で管理しています。新しいリリースではバンドルを再ビルドして検証し、その正確なバイト列とチェックサムをリリースにアップロードした後、メタデータを公開する前にバージョン、ソースコミット、ダウンロード URL、ハッシュをまとめて更新してください。

MCPB のマニフェストはツール名を列挙します。Smithery への公開には、パッケージ化されたサーバーの完全な `tools/list` スキーマも必要です。名前だけではサーバーカードの検証を満たせません。ツール定義を勝手に作ったり削除したりせず、リリースと一致させてください。
