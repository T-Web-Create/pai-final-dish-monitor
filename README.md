# Weekend Colony Watch — 嫌気チャンバー内培養ディッシュの遠隔経時観察ロボット

Physical AI 応用1講座 最終課題「AI×ロボティクスによる創造的タスクの実現」の提出物です。
ROS 2 + Gazebo 上で、UR3e アームが培養ディッシュを 6 時間ごとに蓋越しで撮影し、
画像の経時追跡でコロニーの出現を自動判定して研究者に通知し、確定したときだけ蓋を
吸着して持ち上げ、記録用の写真を撮ってすぐ戻します。

- 動画（YouTube、2分57秒、実速と5倍速、速度は画面左上に常時表示）：（後日記載）
- レポート（PDF）：omnicampus に提出
- 本リポジトリ：コード一式と評価結果（画像データと録画は含みません）

## 何を解決するか

嫌気性菌の培養では、播種からコロニーが見えるまで 1〜3 日かかり、週末を挟むと経過が
分かりません。蓋越しの観察は照明の映り込みで見誤りやすく、一方で嫌気チャンバー内は
無菌ではないため蓋を開ける時間は最小限にしたい、という相反する要求があります。

本システムは次の 2 つで解決します。

1. **経時追跡**：固定カメラ・固定位置で撮った画像の t=0 基準の時間差分から候補を検出し、追跡して「成長するもの＝コロニー、成長しないもの＝反射・ゴミ」を見分ける。
2. **適応的開放（第6案）**：疑いは蓋を開けずに通知し、確定したときだけ開けて写真を撮る。開放は 72 時間で 2 回（約 18 秒）。

## 主な結果（合成画像、評価用シード 100〜129、コロニー 557 個）

| 条件 | 検出 | 見逃し | 誤検出 | 検出遅れ（中央値） |
|---|---|---|---|---|
| 蓋なし | 554 | 3 | 0 | 11.5 h |
| 蓋越し | 553 | 4 | 0 | 11.7 h |
| 偏光模擬 | 556 | 1 | 0 | 11.4 h |

開放方針の比較（蓋越し、1 枚・72 時間あたり）：毎回開ける 13.0 回 / 116 秒 →
第6案 2.0 回 / 18 秒。疑いの通知は最初のコロニー出現から中央値 5.1 h、確定は 11.1 h。
空の皿 30 枚で誤報 0。詳細は `results/` とレポートを参照してください。

## リポジトリ構成

| パス | 内容 |
|---|---|
| `docker/` | ROS 2 Jazzy + Gazebo Harmonic 環境のコンテナ構築用ファイル |
| `ros2_ws/src/dish_description/` | ディッシュ・蓋・ラック・固定カメラのモデルとワールド |
| `ros2_ws/src/dish_bringup/scripts/lid_cycle.py` | 蓋操作（HIGH / DOWN / LIFT / RETRACT の 4 姿勢、DetachableJoint で吸着を模擬） |
| `ros2_ws/src/dish_bringup/scripts/patrol.py` | 毎回蓋を開ける巡回（P0、比較用） |
| `ros2_ws/src/dish_bringup/scripts/patrol6.py` | 採用した巡回（第6案：疑いは通知のみ、確定で開放） |
| `ros2_ws/src/dish_bringup/scripts/run_patrol.sh` | 時刻ごとに別プロセスで巡回を実行（タイムアウト・復旧・やり直し付き） |
| `ros2_ws/src/dish_bringup/scripts/recover.py` | 固まったときの復旧（吸着解除 → 待機姿勢） |
| `ros2_ws/src/dish_bringup/scripts/dish_vision.py` | 固定カメラ画像の真上変換と検出器の呼び出し |
| `ros2_ws/src/dish_bringup/scripts/detect_track.py` | 検出器（`tools/eval` と同一内容） |
| `ros2_ws/src/dish_bringup/scripts/save_image.py` | カメラ画像の保存 |
| `scripts/` | 補助スクリプト |
| `tools/synth/` | 合成培地画像の生成（成長モデル、反射・ゴミ・気泡、正解ラベル）。uv 管理 |
| `tools/eval/` | 検出・追跡（`detect_track.py`）、診断、開放方針の比較、空の皿の評価。uv 管理 |
| `tools/gz/` | 退避姿勢の計算（UR3e の DH パラメータ、カメラ視野への投影） |
| `tools/video/` | 動画のパネル生成・合成・録画の写り込み検査 |
| `tools/tts/` | ナレーション生成（Kokoro、ローカル音声合成） |
| `results/` | 評価結果のテキストと巡回ログ（`heldout_100_129.txt`、`policy_sim_lid_100_129.txt` など） |

`data/`（合成画像）と `recordings/`（録画・動画）は `.gitignore` で除外しています。
ROS 2 ノードは colcon、`tools/*` は uv で管理し、Python 環境を分けています。

## 実行方法の概要

実行環境：Ubuntu 24.04（arm64）、Docker、NVIDIA GPU。ROS 2 Jazzy と Gazebo Harmonic は
コンテナ内、合成・評価・動画は各 `tools/*` の uv 環境で動かします。

**1. 合成画像の生成（ホスト）**

~~~
cd tools/synth && uv sync && uv run python synth.py --seed 112
~~~

**2. 検出・追跡の評価（ホスト）**

~~~
cd tools/eval && uv sync && uv run python detect_track.py
~~~

**3. Gazebo の起動（コンテナ内）**

~~~
ros2 launch ur_simulation_gz ur_sim_control.launch.py
~~~

**4. ディッシュの配置（コンテナ内）**

~~~
~/ros2_ws/src/dish_bringup/scripts/spawn_dish.sh
~~~

**5. 巡回の実行（ホストから背景実行）**

~~~
docker exec -d pai-sim bash -c 'PATROL=patrol6.py ~/ros2_ws/src/dish_bringup/scripts/run_patrol.sh 0 6 12 18 24 30 36 42 48 54 60 66 72 > ~/recordings/patrol6_run.log 2>&1'
~~~

各スクリプトの引数と設定値は、ファイル冒頭のコメントと `tools/eval/detect_track.py` の `CFG` を参照してください。

## 模擬の範囲と限界

- 吸着は Gazebo の DetachableJoint による模擬で、物理的な吸引力は模擬していません。
- 偏光は反射を 0.25 倍に弱めた画像による模擬です。
- ディッシュの中身は合成画像で、蓋の上に置いた発光テクスチャの板として表示しています。照明の影響を受けず、映り込みは合成画像に描き込んだものです。
- 合成画像の反射・ゴミは時刻が変わっても動かないため、時間差分の効果と空の皿での誤報 0 は実機より楽観的な可能性があります。
- 評価用シードは調整用と同じ生成器で作っており、実機画像への汎化は未検証です。
- 通知はログファイル（`notify_log.jsonl`）への書き出しのみで、送信手段は未実装です。
- UR3e の当たり判定メッシュは生成できておらず、衝突は計算で確かめただけです。

## 使用ツール

ROS 2 Jazzy、Gazebo Harmonic（ros_gz）、Universal Robots ROS 2 Gazebo Simulation（UR3e）、
MoveIt2、Python / OpenCV / NumPy、uv、Docker、ffmpeg、Kokoro（音声合成）。
講座の参考教材（ROS 2 と Gazebo の連携、UR3 の Pick and Place）は起動構成の参考にし、
タスク設計・検出器・巡回・評価は独自に実装しました。

## ライセンス

MIT License
