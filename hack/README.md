# hack/analysis_go_vendor_packages_size.py
分析计算 go 项目 vendor 内所有包编译后大小，并输出 csv 格式文件
```sh
# 切换目录到 go.mod 同级目录，并确保项目 vendor 目录存在，以 cri-o 为例
cd $GOPATH/src/github.com/cri-o/cri-o

# 按 size 排序
# 前缀匹配合并
# 单位 MiB
./analysis_go_vendor_packages_size.py -sort -sum 3 -m
```