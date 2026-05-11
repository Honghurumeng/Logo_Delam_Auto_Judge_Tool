# Logo Delam Auto-Judge Tool

基于力-位移曲线的 Apple Logo 脱胶自动判定工具。

## 功能

- 读取 Excel 力-位移数据，自动计算下压刚度（Loading Slope）和迟滞环面积（Hysteresis Area）
- 根据可自定义的阈值自动判定 PASS / FAIL
- 图形化界面，操作简单

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python hao.py
```

## 打包为 Windows 可执行文件

推送至 `main` 分支后，GitHub Actions 会自动构建 `LogoDelamJudge.exe`，可在 Actions 页面下载。
