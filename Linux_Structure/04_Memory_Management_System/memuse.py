#!/usr/bin/python3

import subprocess

size = 100000000

print("メモリ獲得前のシステム全体のメモリ使用量を表示します。")
subprocess.run(["free", "-h"])

array = [0]*size

print("メモリ獲得後のシステム全体のメモリ空き容量を表示します。")
subprocess.run(["free", "-h"])
