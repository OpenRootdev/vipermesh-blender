<a id="vipermesh-blender-mcp-server-and-addon"></a>
# ViperMesh: Blender MCP サーバーとアドオン

> Blender のシーン編集、検査、再利用可能な 3D 操作のための、無料でオープンソースのローカル AI 支援。

正規ページ: https://openrootdev.github.io/vipermesh-blender/
リポジトリ: https://github.com/OpenRootdev/vipermesh-blender
ライセンス: MIT。派生元の帰属表示は NOTICE.md に記載しています。

ViperMesh は二つのローカル要素で動作します。対応する AI クライアントが、単一の持続的な Node MCP プロセスを stdio 経由で起動します。そのプロセスは、直列化されたループバック TCP ブリッジで Blender アドオンに接続します。既定の接続先は 127.0.0.1:9876 です。

用意された操作は、シーンの配置、マテリアル、照明、カメラ、ジオメトリと UV の準備、リギング、ウェイト、アニメーション操作、エクスポート、診断をカバーします。九つの最上位 MCP ツールからこれらの機能を利用できます。エージェントは最初に bootstrap_vipermesh_session を呼び出してください。独自の作業には、引き続き Python を実行できます。

シーン検査と視覚的な確認は、エージェントが結果を修正する助けになります。生成トークンの削減、作業の高速化、結果の改善は目標であり、あらゆる場合に保証されるものではありません。結果はモデル、シーン、タスクによって異なります。

このコネクタは、ホストされた生成モデルではありません。AI モデル、クラウドルーティング、非公開の Studio アセットライブラリ、認証、課金機能は含まれません。Docker や ViperMesh アカウントは不要ですが、モデルの利用は別途有料の場合があります。これは信頼できるローカル環境向けのコネクタであり、サンドボックスではありません。

<a id="install"></a>
## インストール

現在テスト対象となっているリリースは Blender 5.2 です。Node.js 20+ と、ローカル stdio MCP を扱えるクライアントが必要です。別途 Blender アドオンを有効にし、ローカルブリッジを起動してください。対応クライアントに MCPB バンドルをインポートするか、ソースをビルドして生成されたエントリーポイントを登録します。セッション中は同じプロセスを動かし続けてください。

- [インストールとトラブルシューティング](https://openrootdev.github.io/vipermesh-blender/setup/index.md)
- [クライアントの設定](https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/client-setup.md)
- [リリースバンドル](https://github.com/OpenRootdev/vipermesh-blender/releases)
- [コネクタのマニュアル](https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/portable-blender-mcp.md)
- [エージェントスキル](https://github.com/OpenRootdev/vipermesh-blender/blob/main/skills/using-vipermesh-blender/SKILL.md)
- [セキュリティの境界](https://github.com/OpenRootdev/vipermesh-blender/blob/main/SECURITY.md)
- [図解による紹介](https://openrootdev.github.io/vipermesh-blender/#overview)
- [Harness Library](https://openrootdev.github.io/harness-library/harnesses/vipermesh-blender/)
