#!/usr/bin/python3

# コマンドライン引数を読むためのモジュール
import sys

# 時刻を測るためのモジュール
import time

# fork(), wait(), sched_setaffinity() など、OS機能を使うためのモジュール
import os

# 測定結果をグラフ化する自作モジュール
import plot_sched


def usage():
    # 使い方を表示して、異常終了する
    # 本来は print(..., file=sys.stderr) と書くと標準エラー出力に出せる
    print("""使い方: {} <プロセス数>
        * 論理CPU上で<プロセス数>の数だけ同時に100m秒程度CPUリソースを消費する負荷処理プロセスを起動した後に、すべてのプロセスの終了を待つ。
        * "sched-<プロセス数>.jpg"というファイルに実行結果を示したグラフを書き出す。
        *
        グラフのx軸は負荷処理プロセス開始からの経過時間[ミリ秒]、y軸は進捗[%]""".format(progname), file=sys.stderr)
    sys.exit(1)


# 1ミリ秒あたりに何回ループできるかを見積もるため、
# まずこの回数だけ空ループを回して実行時間を測る
NLOOP_FOR_ESTIMATION = 100000000

# 1ミリ秒あたりのループ回数を後で保存する変数
nloop_per_msec = None

# 実行されたプログラム名
# usage() の表示に使う
progname = sys.argv[0]


def estimate_loops_per_msec():
    # 現在時刻を取得する
    # perf_counter() は短い時間の測定に向いた高精度タイマー
    before = time.perf_counter()

    # CPUを使うだけの空ループ
    # この処理に何秒かかるかを測る
    for _ in range(NLOOP_FOR_ESTIMATION):
        pass

    # ループ終了後の時刻を取得する
    after = time.perf_counter()

    # 総ループ回数 ÷ 経過秒数 = 1秒あたりのループ回数
    # さらに1000で割ることで、1ミリ秒あたりのループ回数にする
    return int(NLOOP_FOR_ESTIMATION / (after - before) / 1000)


def child_fn(n):
    # 子プロセスが実行する関数
    # n は負荷処理プロセスの番号
    # 例: 0番目の子なら 0.data に結果を書く

    # 進捗ごとの時刻を保存する配列
    # 100個用意し、0%から99%までの進捗時刻を入れる
    progress = 100 * [None]

    # 100回に分けてCPU負荷をかける
    # 各回で約1ミリ秒ぶんの空ループを実行する想定
    for i in range(100):
        # 約1ミリ秒ぶんCPUを使う
        for j in range(nloop_per_msec):
            pass

        # i番目の進捗に到達した時刻を記録する
        progress[i] = time.perf_counter()

    # 子プロセスごとに別ファイルへ結果を書く
    # 例: n=0 なら 0.data
    f = open("{}.data".format(n), "w")

    # 開始時刻 start からの経過時間をミリ秒に変換して書き出す
    # 形式:
    #   経過時間[ミリ秒]    進捗[%]
    for i in range(100):
        f.write("{}\t{}\n".format((progress[i] - start) * 1000, i))

    f.close()

    # 子プロセスを正常終了する
    exit(0)


# コマンドライン引数が足りない場合は使い方を表示する
if len(sys.argv) < 2:
    usage()

# 第1引数を並列度として受け取る
# 例:
#   ./sched.py 3
# なら、3個の負荷処理プロセスを同時に起動する
concurrency = int(sys.argv[1])

# 並列度は1以上である必要がある
if concurrency < 1:
    print("<並列度>は1以上の整数にしてください: {}".format(concurrency))
    usage()

# このプロセスをCPU 0だけで動くように固定する
#
# 第1引数の 0 は「現在のプロセス」を意味する
# {0} は「CPU 0だけを使う」という意味
#
# fork() で作られる子プロセスも、このCPU affinityを引き継ぐ
# そのため、全ての負荷処理プロセスがCPU 0上で実行される
os.sched_setaffinity(0, {0})

# 1ミリ秒あたりに何回空ループできるかを見積もる
# これにより、子プロセス側で「だいたい1ミリ秒ぶんのCPU負荷」を作れる
nloop_per_msec = estimate_loops_per_msec()

# 全子プロセス共通の開始時刻
# fork() の前に設定しておくことで、各子プロセスが同じ基準時刻を使える
start = time.perf_counter()

# 指定された並列度の数だけ子プロセスを作る
for i in range(concurrency):
    pid = os.fork()

    # fork() に失敗した場合
    # Pythonでは通常例外になることが多いが、念のためチェックしている
    if pid < 0:
        exit(1)

    # pid == 0 は子プロセス側
    elif pid == 0:
        # 子プロセスは負荷処理を実行して、結果を i.data に書く
        child_fn(i)

    # pid > 0 は親プロセス側
    # 親は次の子プロセスを作るため、そのままループを続ける

# 親プロセスは、作成した全ての子プロセスの終了を待つ
# wait() で子プロセスの終了ステータスも回収する
for i in range(concurrency):
    os.wait()

# 全ての子プロセスが終了したら、dataファイルをもとにグラフを作る
# sched-<並列度>.jpg が生成される
plot_sched.plot_sched(concurrency)

