<a id="install-vipermesh-blender-mcp"></a>
# ViperMesh Blender MCP のインストール

正規ページ: https://openrootdev.github.io/vipermesh-blender/setup/

← ViperMesh の概要

ViperMesh for Blender をインストールします。

MCP サーバーとアドオンを使って、AI クライアントをローカルの Blender シーンに接続します。

必要なもの

現在テスト対象となっているリリースは Blender 5.2 です。

Node.js 20 以降。

stdio 経由のローカル MCP サーバーに対応する AI クライアント。リモートサーバーの URL だけを受け付けるクライアントは、このリリースに直接接続できません。

コネクタは無料で、MIT ライセンスで提供されます。AI クライアントやモデルには別途料金がかかる場合があります。Docker や ViperMesh アカウントは不要です。

1. Blender アドオンを有効にする

最新リリースから、バージョン付きのアドオン Python ファイルまたは ZIP をダウンロードします。Blender で Edit → Preferences → Add-ons → Install from Disk を開き、ファイルを選択して ViperMesh for Blender を有効にしてください。

3D ビューポートのサイドバーで ViperMesh を選択し、Start Local Bridge をクリックします。Blender とブリッジは起動したままにしてください。既定の接続先は 127.0.0.1:9876 です。

2. ローカル MCP サーバーをインストールする

パッケージからのインストール

v1.3.0 の MCPB バンドルと SHA-256 チェックサムをダウンロードします。ローカル MCPB 拡張機能に対応するクライアントにインポートしてください。バンドルには Node サーバーと依存関係が含まれますが、Node.js と別途有効にする Blender アドオンは引き続き必要です。

MCPB のインポート機能がない場合は、バンドルを ZIP として常設のディレクトリに展開します。クライアントが node を起動し、server/index.mjs の絶対パスを引数に渡すように設定してください。バンドルとチェックサムのガイドに従ってください。

ソースからのビルド

git clone https://github.com/OpenRootdev/vipermesh-blender.git
cd vipermesh-blender
npm install
npm run build

3. AI クライアントを接続する

ソースからビルドした場合は、生成されたエントリーポイントを使ってサーバーを一度登録します。例のパスは、ご自身の絶対パスに置き換えてください。

{
  "mcpServers": {
    "vipermesh-blender": {
      "command": "node",
      "args": ["C:/absolute/path/to/vipermesh-blender/dist/public-portable-blender-mcp.js"]
    }
  }
}

設定場所と最上位のキーは、クライアントによって異なります。クライアントの設定ガイドと、ご使用のクライアントのドキュメントを参照してください。セッション全体を通じて、単一の MCP プロセスを動かし続けるようにします。

4. 接続を確認し、小さな編集を試す

エージェントに最初に bootstrap_vipermesh_session を呼び出させ、接続結果を確認してください。オブジェクトを移動する、支持物に載っているか確認するなど、小さな依頼から始めてください。編集を信頼する前に、生成されたシーンと画像を確認してください。

九つの最上位 MCP ツールから、機能の検出、シーン操作、検査、Python によるフォールバックを利用できます。これはホストされた 3D 生成モデルではなく、公開コネクタには非公開の Studio アセットライブラリは含まれません。

よくある設定上の問題

クライアントにツールが表示されない

登録したコマンドとファイルの絶対パスを確認してください。クライアントがローカル stdio MCP サーバーに対応し、Node を起動できることを確認します。クライアント固有の手順に従って、MCP 接続を再読み込みしてください。

ツールは表示されるが、Blender に接続できない

Blender が起動していること、アドオンが有効であること、Start Local Bridge が実行中であることを確認してください。サーバーとアドオンのブリッジポートを一致させます。ブリッジはループバックのままにし、公開しないでください。

アシスタントがサーバーを繰り返し再起動する

クライアントが単一の持続的な子プロセスを管理するように設定してください。ツール呼び出しごとに npm、npx、tsx を個別実行すると、既存のセッションが破棄されます。

接続はサンドボックス化されているか

いいえ。これは信頼できるローカル環境向けのコネクタです。Python のフォールバックは Blender 内でコードを実行できます。信頼できるクライアントを使い、破壊的な操作を確認してください。セキュリティの境界を読んでください。

設定の問題を報告 · エージェント向けドキュメント · Harness Library の掲載情報

クライアントの設定: https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/client-setup.md
バンドルとチェックサム: https://github.com/OpenRootdev/vipermesh-blender/blob/main/docs/mcp-distribution.md
セキュリティ: https://github.com/OpenRootdev/vipermesh-blender/blob/main/SECURITY.md
