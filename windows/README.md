# Windows 打包指南 — 產生 IP Service Checker.exe

> 本資料夾包含所有 Windows 打包所需檔案，照著步驟做就能產生單一 `.exe` 執行檔，可以直接傳給同事使用。

---

## 📁 本資料夾的檔案說明

| 檔案 | 用途 |
|---|---|
| `ip_checker.spec` | PyInstaller 打包設定，不需要修改 |
| `version_info.txt` | exe 右鍵→內容→詳細資料的版本資訊 |
| `icon_windows.ico` | App 圖示（Windows 格式），不需要修改 |

---

## ✅ 事前確認

- [ ] 電腦是 Windows 10 或 Windows 11（64 位元）
- [ ] 已安裝 Python 3.11
  - 確認方式：按 `Win + R`，輸入 `cmd`，按 Enter，輸入 `python --version`
  - **必須是 3.11**，其他版本可能有相容性問題
  - 下載：https://www.python.org/downloads/release/python-3119/
  - ⚠️ 安裝時記得勾選 **「Add Python to PATH」**

---

## 🚀 打包步驟（共 5 步）

### 第 1 步：把主程式複製進來

把 `src\ip-service_check_app.py` 複製到這個 `windows\` 資料夾裡。

```
打包前，windows\ 資料夾內應該要有這些檔案：
  ip-service_check_app.py   ← 從 src\ 複製過來
  ip_checker.spec
  version_info.txt
  icon_windows.ico
```

### 第 2 步：開啟命令提示字元（CMD），進入這個資料夾

按 `Win + R`，輸入 `cmd`，按 Enter。

```cmd
cd 你的路徑\windows

:: 範例（請換成你自己的實際路徑）
cd C:\Users\你的名字\Desktop\ip-service-checker\windows
```

### 第 3 步：安裝必要套件

> 只需要做一次，之後重新打包不用重做。

```cmd
pip install pywebview requests pyinstaller pythonnet
```

> ⏳ 這步驟需要等待約 2-5 分鐘，請耐心等候。

### 第 4 步：打包成單一 .exe

```cmd
:: 清除舊的打包結果（第一次可以跳過）
rmdir /s /q build dist

:: 開始打包
pyinstaller ip_checker.spec
```

> ⏳ 需要等待約 3-8 分鐘，看到 `Building EXE` 完成後就成功了。

打包完確認一下：

```cmd
dir "dist\IP Service Checker\"
:: 應該看到：IP Service Checker.exe
```

### 第 5 步：測試執行

```cmd
"dist\IP Service Checker\IP Service Checker.exe"
```

> ⚠️ **第一次開啟會比較慢（約 5-10 秒）**，這是正常現象。
> 如果跳出「沒有回應」對話框，點「**等待程式回應**」，等幾秒就會正常顯示。

---

## 📦 分發給同事

打包完成的執行檔位置：

```
windows\dist\IP Service Checker\IP Service Checker.exe
```

**傳給同事的方式：**

1. 把整個 `dist\IP Service Checker\` 資料夾壓縮成 ZIP
2. 傳給同事解壓縮後直接執行 `IP Service Checker.exe`

> ✅ Windows 11 內建 WebView2，同事**不需要安裝任何東西**，直接執行即可。
> 
> Windows 10 如果無法開啟，請安裝 WebView2：
> https://developer.microsoft.com/en-us/microsoft-edge/webview2/

---

## ❌ 常見錯誤處理

**錯誤：`pip` 不是可辨識的命令**
→ Python 安裝時沒有勾選「Add Python to PATH」，重新安裝並勾選

**錯誤：`pyinstaller` 不是可辨識的命令**
```cmd
pip install pyinstaller
```

**錯誤：`No module named 'webview'`**
```cmd
pip install pywebview
```

**錯誤：`No module named 'clr'`**
```cmd
pip install pythonnet
```

**防毒軟體攔截 .exe**
→ 正常現象，PyInstaller 打包的 exe 常被誤判。
→ 暫時停用防毒後重新打包，或把 exe 加入防毒白名單。

**開啟後一直顯示「沒有回應」**
→ 點「等待程式回應」，等待 10-15 秒，WebView2 初始化完成後會正常運作。
→ 第二次之後開啟速度會明顯變快。

**exe 開啟後立刻關閉（閃退）**
→ 把 `ip_checker.spec` 裡的 `console=False` 改成 `console=True`，
  重新打包後從 CMD 執行，查看錯誤訊息。
