# プロセススケジューラ

## 前提知識: 経過時間とCPU使用時間

`time` コマンドで、プログラムの実行時間を確認した。

```bash
time ./load.py
```

`load.py`:

```python
#!/usr/bin/python3

NLOOP=100000000

for _ in range(NLOOP):
    pass
```

結果:

```text
real    0m3.458s
user    0m3.454s
sys     0m0.005s
```

意味:

- `real`: コマンド開始から終了までの実際の経過時間
- `user`: ユーザー空間でCPUを使った時間
- `sys`: カーネル空間でCPUを使った時間

`load.py` はCPUを使い続ける処理なので、`real` と `user` がほぼ同じになった。

## sleepとの比較

```bash
time sleep 3
```

結果:

```text
real    0m3.008s
user    0m0.001s
sys     0m0.006s
```

`sleep 3` は3秒経過するが、その間CPUを使い続けているわけではない。

大事なこと:

```text
real が長い = CPUを使った
```

とは限らない。

CPUをどれだけ使ったかを見るには、`user` と `sys` を見る。

## 複数プロセスでCPUを分け合う

`multiload.sh` で、CPU負荷をかける `load.py` を複数同時に起動した。

`-m` を付けない場合、`taskset` によりCPU 0だけで動かす。

```bash
taskset -p -c 0 $$
```

意味:

- 現在のシェルをCPU 0に固定する
- 子プロセスも基本的にCPU割り当てを引き継ぐ
- 複数プロセスが1つのCPUを取り合う状態を作れる

## 実行結果

1プロセス:

```bash
./multiload.sh 1
```

```text
real    0m3.119s
user    0m3.119s
sys     0m0.000s
```

2プロセス:

```bash
./multiload.sh 2
```

```text
real    約6.3s
user    約3.1s
```

3プロセス:

```bash
./multiload.sh 3
```

```text
real    約9.4s
user    約3.1s
```

## わかったこと

1つのCPU上でCPU負荷プロセスを複数動かすと、各プロセスはCPU時間を分け合う。

```text
1プロセス: real 約3秒
2プロセス: real 約6秒
3プロセス: real 約9秒
```

各プロセスが必要とするCPU時間 `user` は約3秒のまま。

しかし、CPUを待つ時間が増えるため、経過時間 `real` が伸びる。

## 今日のポイント

```text
user時間:
  そのプロセスが実際にCPUを使った時間

real時間:
  開始から終了までの壁時計時間

1つのCPUに複数のCPU負荷プロセスを置くと、
スケジューラがCPU時間を分配するため、
各プロセスのreal時間は長くなる。
```

