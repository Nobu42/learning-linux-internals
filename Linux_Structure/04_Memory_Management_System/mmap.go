package main

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"strconv"
	"syscall"
)

const (
	// mmap() で確保するサイズ
	// 1024 * 1024 * 1024 = 1GiB
	ALLOC_SIZE = 1024 * 1024 * 1024
)

func main() {
	// 現在実行中のプロセスIDを取得する
	// /proc/<pid>/maps を見るために使う
	pid := os.Getpid()

	// mmap() で新しいメモリ領域を確保する前のメモリマップを表示する
	fmt.Println("*** 新規メモリ領域獲得前のメモリマップ ***")

	// /proc/<pid>/maps は、そのプロセスの仮想メモリ配置を表すファイル
	// cat /proc/<pid>/maps を実行して、現在のメモリマップを表示する
	command := exec.Command("cat", "/proc/"+strconv.Itoa(pid)+"/maps")
	command.Stdout = os.Stdout

	err := command.Run()
	if err != nil {
		log.Fatal("catの実行に失敗しました")
	}

	// mmap() で匿名メモリ領域を1GiB確保する
	//
	// 第1引数 -1:
	//   ファイルディスクリプタを使わない
	//   MAP_ANON のため、ファイルに対応しない匿名メモリを作る
	//
	// 第2引数 0:
	//   ファイル内オフセット
	//   匿名メモリなので0
	//
	// 第3引数 ALLOC_SIZE:
	//   確保するサイズ
	//
	// syscall.PROT_READ | syscall.PROT_WRITE:
	//   読み取り可能、書き込み可能なメモリ領域にする
	//
	// syscall.MAP_ANON | syscall.MAP_PRIVATE:
	//   ファイルに紐づかない匿名マッピング
	//   他プロセスとは共有しないプライベートマッピング
	data, err := syscall.Mmap(
		-1,
		0,
		ALLOC_SIZE,
		syscall.PROT_READ|syscall.PROT_WRITE,
		syscall.MAP_ANON|syscall.MAP_PRIVATE,
	)
	if err != nil {
		log.Fatal("mmap()に失敗しました")
	}

	// プログラム終了時に mmap() した領域を解放する
	defer syscall.Munmap(data)

	fmt.Println("")

	// mmap() で得た領域の先頭アドレスとサイズを表示する
	//
	// data は []byte
	// &data[0] は、そのスライスが指すメモリ領域の先頭アドレス
	fmt.Printf("*** 新規メモリ領域: アドレス = %p, サイズ = 0x%x ***\n",
		&data[0], ALLOC_SIZE)

	fmt.Println("")

	// mmap() 後のメモリマップを表示する
	// ここで、mapsに新しい匿名メモリ領域が増えていることを確認する
	fmt.Println("*** 新規メモリ領域獲得後のメモリマップ ***")

	command = exec.Command("cat", "/proc/"+strconv.Itoa(pid)+"/maps")
	command.Stdout = os.Stdout

	err = command.Run()
	if err != nil {
		log.Fatal("catの実行に失敗しました")
	}
}

