#!/usr/bin/python3

# コマンドライン引数を扱うためのモジュール
import sys

# 時刻計測に使うモジュール
import time

# fork(), wait(), nice(), sched_setaffinity() などOS機能を使うためのモジュール
import os

# 測定結果をグラフ化する自作モジュール
import plot_sched


def usage():
    # 使い方を標準エラー出力に表示して終了する
    print("""使い方: {} <nice値>
    * 論理CPU0上で100ミリ秒程度CPUリソースを消費する負荷処理を2つ起動した後に、両方のプロセスを待つ。
    * 負荷処理0, 1のnice値はそれぞれ0(デフォルト)、<nice値>とする。
    * "sched-2.jpg"というファイルに実行結果を示したグラフを書き出す。
    *
    グラフのX軸はプロセス開始からの経過時間[ミリ秒]、Y軸は進捗[%]""".format(progname), file=sys.stderr)
    sys.exit(1)


# 1ミリ秒あたりに何回ループできるかを見積もるための試行回数
NLOOP_FOR_ESTIMATION = 100000000

# 1ミリ秒あたりのループ回数を後で保存する変数
nloop_per_msec = None

# 実行されたプログラム名
# usage() の表示に使う
progname = sys.argv[0]


def estimate_loops_per_msec():
    # 空ループを一定回数実行し、どれくらい時間がかかるかを測る
    before = time.perf_counter()

    for _ in range(NLOOP_FOR_ESTIMATION):
        pass

    after = time.perf_counter()

    # 1秒あたりのループ回数を求め、1000で割って1ミリ秒あたりに変換する
    return int(NLOOP_FOR_ESTIMATION / (after - before) / 1000)


def child_fn(n):
    # 子プロセスが実行する負荷処理
    # n は子プロセス番号
    # 0なら 0.data、1なら 1.data に結果を書く

    # 進捗ごとの時刻を保存する配列
    progress = 100 * [None]

    # 100段階に分けてCPU負荷をかける
    # 各段階で約1ミリ秒ぶんの空ループを実行する想定
    for i in range(100):
        for _ in range(nloop_per_msec):
            pass

        # その進捗に到達した時刻を記録する
        progress[i] = time.perf_counter()

    # 子プロセスごとの結果ファイルを作る
    f = open("{}.data".format(n), "w")

    # 開始時刻からの経過時間[ミリ秒]と進捗[%]を書き出す
    for i in range(100):
        f.write("{}\t{}\n".format((progress[i] - start) * 1000, i))

    f.close()

    # 子プロセスを終了する
    exit(0)


# nice値が指定されていなければ使い方を表示する
if len(sys.argv) < 2:
    usage()

# 第1引数をnice値として受け取る
# nice値が大きいほど優先度は低くなる
nice = int(sys.argv[1])

# この実験では負荷処理プロセスを2つ起動する
concurrency = 2

# 念のため、並列度が1以上であることを確認する
if concurrency < 1:
    print("<並列度>は1以上の整数にしてください: {}".format(concurrency))
    usage()

# 現在のプロセスをCPU 0だけで動くように固定する
# fork() で作られる子プロセスも、このCPU affinityを引き継ぐ
#
# これにより、2つの負荷処理プロセスがCPU 0を取り合う状態を作る
os.sched_setaffinity(0, {0})

# 1ミリ秒あたりのループ回数を見積もる
nloop_per_msec = estimate_loops_per_msec()

# 全子プロセス共通の開始時刻
# fork() 前に記録することで、両方の子プロセスが同じ基準時刻を使える
start = time.perf_counter()

# 2つの子プロセスを作る
for i in range(concurrency):
    pid = os.fork()

    # fork() 失敗時
    if pid < 0:
        exit(1)

    # 子プロセス側
    elif pid == 0:
        # 最後に作る子プロセスだけnice値を変更する
        #
        # i == 0:
        #   nice値 0 のまま
        #
        # i == 1:
        #   指定されたnice値を加算する
        #
        # nice値が大きいほど、スケジューラ上の優先度は低くなる
        if i == concurrency - 1:
            os.nice(nice)

        # 負荷処理を実行し、結果を i.data に書く
        child_fn(i)

    # 親プロセス側は次のループに進み、次の子プロセスを作る

# 親プロセスは、2つの子プロセスの終了を待つ
# wait() により、子プロセスの終了ステータスも回収する
for i in range(concurrency):
    os.wait()

# 0.data と 1.data を読み込んで、sched-2.jpg を作成する
plot_sched.plot_sched(concurrency)

