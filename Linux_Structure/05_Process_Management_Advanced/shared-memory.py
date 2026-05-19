#!/usr/bin/python3

# fork() を使うためのモジュール
import os

# エラー出力や終了処理に使うモジュール
import sys

# 共有メモリを作るために使うモジュール
import mmap

# 数値をバイト列に変換するときのエンディアンを取得する
# 例: little または big
from sys import byteorder


# 共有メモリとして確保するサイズ
# Linuxの一般的なページサイズに合わせて 4096 bytes にしている
PAGE_SIZE = 4096


# 親プロセスが扱う初期値
data = 1000

# fork() 前の値を表示する
print("子プロセス生成前のデータの値: {}".format(data))


# mmapで共有メモリ領域を作る
#
# -1:
#   ファイルに紐づかない匿名メモリを作る
#
# PAGE_SIZE:
#   4096 bytes の領域を確保する
#
# flags=mmap.MAP_SHARED:
#   親子プロセス間で変更を共有できるマッピングにする
shared_memory = mmap.mmap(-1, PAGE_SIZE, flags=mmap.MAP_SHARED)


# Pythonの整数 data を8バイトのバイト列に変換し、
# 共有メモリの先頭8バイトに書き込む
#
# mmapはバイト列として扱うため、
# 整数をそのまま代入するのではなく bytes に変換する
shared_memory[0:8] = data.to_bytes(8, byteorder)


# fork() で子プロセスを作る
pid = os.fork()

# fork() に失敗した場合
if pid < 0:
    print("fork()に失敗しました", file=sys.stderr)

# pid == 0 は子プロセス側
elif pid == 0:
    # 子プロセス側で、共有メモリの先頭8バイトから値を読み出す
    data = int.from_bytes(shared_memory[0:8], byteorder)

    # 読み出した値を2倍にする
    data *= 2

    # 2倍にした値を再び8バイトのバイト列に変換し、
    # 共有メモリへ書き戻す
    #
    # MAP_SHARED のため、この変更は親プロセスからも見える
    shared_memory[0:8] = data.to_bytes(8, byteorder)

    # 子プロセスを終了する
    sys.exit(0)


# 親プロセス側
#
# 子プロセスの終了を待つ
os.wait()

# 子プロセスが書き換えた共有メモリの値を、親プロセス側で読み出す
data = int.from_bytes(shared_memory[0:8], byteorder)

# MAP_SHARED の共有メモリを使ったため、
# 子プロセスが2倍にした値を親プロセス側でも確認できる
print("子プロセス終了後のデータの値: {}".format(data))

