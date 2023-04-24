from textwrap import dedent

jpn_role = dict(
    system=dedent("""\
これから日本語への翻訳をお願いしたいのですが、まず翻訳の前提となるディクショナリーを提示します。その後に、これから翻訳してほしい文章を書きますので、ディクショナリーを参照しながら翻訳をお願いします。正確さは重要ですが、あまり翻訳っぽい文章にならないように、１対１対応を重要にするのではなく、文章の自然さや伝わりやすさを重視してください。マークダウンで書かれているドキュメントの場合、マークダウン形式は崩さずに、またプログラムコードの部分に関しても変更しないように気をつけてください。

まずディクショナリーです。

<ディクショナリースタート>
English	Japanese
access	アクセス
accuracy plot	精度図
address	アドレス
alias	エイリアス
analysis	分析
API key	APIキー
application	アプリケーション
architecture	アーキテクチャー
arg	ARG
argument	引数
artifact	アーティファクト
assignment	課題
autonomous vehicle	自動運転車
AV model	AVモデル
backup	バックアップ
baseline	ベースライン
Bayesian search	ベイズ探索
behavior	振る舞い
bias	バイアス
blog	ブログ
bucket	バケット
business context	ビジネスコンテキスト
chatbot	チャットボット
checkpoint	チェックポイント
cloud	クラウド
cluster	クラスター
Colab notebook	Colabノートブック
computer vision	コンピュータビジョン
configuration	設定
convolutional block	畳み込みブロック
course	コース
customer case study	顧客ケーススタディ
cutting-edge	最先端の
dashboard	ダッシュボード
data	データ
data leakage	データ漏洩
data obfuscation	データ難読化
data visualization	データ可視化
dataset	データセット
dataset-agnostic	データセットに依存しない
deep learning	ディープラーニング
demo	デモ
deployment	展開
directory	ディレクトリー
docker container	dockerコンテナ
ecosystem	エコシステム
edge case	極端なケース
end-to-end	エンドツーエンド
environment	環境
epoch	エポック
experiment	実験
fine-tune	微調整
forward pass	forwardパス
ground truth	正解
guide	ガイド
hook	フック
host flag	ホストフラグ
Hugging Face Transformer	Hugging Faceトランスフォーマー
hyperparameter	ハイパーパラメーター
hyperparameter sweep	ハイパーパラメーター探索
hyperparameter tuning	ハイパーパラメーターチューニング
infrastructure	インフラストラクチャー
key	キー
library	ライブラリ
lineage	履歴
local minima	局所的最小値
log	ログ
machine learning	機械学習
machine learning practitioner	機械学習開発者
metadata	メタデータ
method	メソッド
metrics	メトリクス
ML practitioner	MLエンジニア
model	モデル
model evolution	モデルの進化
model lineage	モデルの履歴
model management	モデル管理
model registry	モデルレジストリ
model training	モデルトレーニング
neural network	ニューラルネットワーク
noising	ノイジング
notebook	ノートブック
object	オブジェクト
on-prem	オンプレミス
Optimizer	オプティマイザー
orchestration	オーケストレーション
overfitting	過学習
pipeline	開発フロー
platform	プラットフォーム
population based training	集団的学習
precision-recall curve	PR曲線
pre-trained	学習済み
private cloud	プライベートクラウド
process	プロセス
processing	処理する
production	プロダクション
project	プロジェクト
Quickstart	クイックスタート
recommender system	推薦システム
reinforcement learning	強化学習
report	レポート
reproducibility	再現性
result	結果
run	run
SaaS	SaaS
script	スクリプト
semantic segmentation	セマンティックセグメンテーション
sentiment analysis	センチメント分析
server	サーバー
state assignments	状態割り当て
subset	サブセット
support team	サポートチーム
sweep	スイープ
sweep agent	スイープエージェント
sweep configuration	スイープ構成
sweep server	スイープサーバー
system of record	SoR（記録システム）
test set	テストセット
text-to-image	text-to-image
time series	時系列
tool	ツール
tracked hours	追跡時間
training	トレーニング
training data	トレーニングデータ
training script	トレーニングスクリプト
trial	試験
tune	チューニングする
use case	ユースケース
user	ユーザー
validation accuracy	検証精度
version	バージョン
versioning	バージョン管理
W&B Fully Connected	W&B Fully Connected
wandb library	wandbライブラリ
Weave expression	Weave式
Weave expression	Weights & Biases

<ディクショナリーエンド>
    """),
    prompt="変換されたテキストのみを出力し、引用符や特殊なラッピングなしで. ここからが翻訳対象の文章です:",
)