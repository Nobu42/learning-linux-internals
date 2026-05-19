#!/usr/bin/python3

# fork() を使うためのモジュール
import os

# エラー出力や終了処理に使うモジュール
import sys


# 親プロセスが持つ通常のPython変数
data = 1000

# fork() 前の値を表示する
print("子プロセス生成前のデータの値: {}".format(data))

# fork() で子プロセスを作る
#
# fork() 後、親プロセスと子プロセスは同じ変数 data を持っているように見える
# しかし実際には、それぞれ別々のプロセス空間を持つ
pid = os.fork()

# fork() に失敗した場合
if pid < 0:
    print("fork()失敗しました", file=sys.stderr)

# pid == 0 は子プロセス側
elif pid == 0:
    # 子プロセス側で data を2倍にする
    #
    # ただし、これは子プロセス側の data が変わるだけ
    # 親プロセス側の data には影響しない
    data *= 2

    # 子プロセスを終了する
    sys.exit(0)

# 親プロセス側
#
# 子プロセスの終了を待つ
os.wait()

# 子プロセスが data を2倍にしても、
# 親プロセスの data は変更されていない
#
# プロセス間では通常の変数は共有されないため
print("子プロセス終了後のデータの値: {}".format(data))

