#!/bin/bash

# 複数CPUで動かすかどうかを表すフラグ
# 0: 1つのCPUだけで動かす
# 1: 複数CPUで動かせるようにする
MULTICPU=0

# 実行されたスクリプト名を保存する
# usage() で使い方を表示するときに使う
PROGNAME=$0

# このスクリプトが置かれているディレクトリの絶対パスを取得する
SCRIPT_DIR=$(cd $(dirname $0) && pwd)

# 使い方を表示して終了する関数
usage() {
	# 以降の出力を標準エラー出力に向ける
	exec >&2

	echo "使い方: $PROGNAME [-m] <プロセス数>
	所定の時間動作する負荷処理プロセスを<プロセス数>で指定した数だけ動作させて、全ての終了を待ちます。
	各プロセスにかかった時間を出力します。
	デフォルトでは全てのプロセスは1論理CPU上でだけ動作します。

オプションの意味:
	-m: 各プロセスを複数CPU上で動かせるようにします。"

	# 異常終了として終了する
	exit 1
}

# コマンドラインオプションを解析する
# 今回は -m だけを受け付ける
while getopts "m" OPT ; do
	case $OPT in
		m)
			# -m が指定されたら、複数CPUで動かす設定にする
			MULTICPU=1
			;;
		\?)
			# 不明なオプションが指定されたら使い方を表示する
			usage
			;;
	esac
done

# getopts で処理したオプションを引数リストから取り除く
shift $((OPTIND - 1))

# 残りの引数がなければ、プロセス数が指定されていないのでエラー
if [ $# -lt 1 ] ; then
	usage
fi

# 第1引数を、同時に動かすプロセス数として使う
CONCURRENCY=$1

# -m が指定されていない場合は、このシェル自身をCPU 0に固定する
# 子プロセスも基本的にこのCPU割り当てを引き継ぐ
if [ $MULTICPU -eq 0 ] ; then
	taskset -p -c 0 $$ >/dev/null
fi

# 指定された数だけ load.py をバックグラウンドで起動する
# & を付けることで、1つずつ終わるのを待たずに同時に動かす
for ((i=0; i<CONCURRENCY; i++)); do
	time "${SCRIPT_DIR}/load.py" &
done

# 起動したバックグラウンドプロセスが全て終わるまで待つ
# wait は子プロセスの終了を回収する
for ((i=0; i<CONCURRENCY; i++)); do
	wait
done

