# macOS 打包指南 — 產生 IP-Service-Checker.dmg

> 本資料夾包含所有 macOS 打包所需檔案，照著步驟做就能產生可以分發給同事的 `.dmg` 安裝檔。

---

## 📁 本資料夾的檔案說明

| 檔案 | 用途 |
|---|---|
| `setup.py` | py2app 打包設定，不需要修改 |
| `dmg_settings.py` | DMG 視窗外觀設定，不需要修改 |
| `icon.icns` | App 圖示（macOS 格式），不需要修改 |
| `icon_1024.png` | 圖示原始圖，備用 |

---

## ✅ 事前確認

- [ ] 電腦是 Mac（Intel 或 Apple Silicon 都可以）
- [ ] 已安裝 Python 3.11 或以上
  - 確認方式：開啟 Terminal，輸入 `python3 --version`
  - 沒有的話到 https://www.python.org/downloads/ 下載

---

## 🚀 打包步驟（共 6 步）

### 第 1 步：把主程式複製進來

把 `src/ip-service_check_app.py` 複製到這個 `macos/` 資料夾裡。

```
打包前，macos/ 資料夾內應該要有這些檔案：
  ip-service_check_app.py   ← 從 src/ 複製過來
  setup.py
  dmg_settings.py
  icon.icns
  icon_1024.png
```

### 第 2 步：開啟 Terminal，進入這個資料夾

```bash
cd 你的路徑/macos

# 範例（請換成你自己的實際路徑）
cd ~/Desktop/ip-service-checker/macos
```

### 第 3 步：建立虛擬環境

> 只需要做一次，之後重新打包不用重做。

```bash
python3 -m venv venv
```

### 第 4 步：啟動虛擬環境並安裝套件

> 每次開新的 Terminal 視窗都要重新執行這行。

```bash
source venv/bin/activate
```

安裝必要套件：

```bash
pip install pywebview requests chardet py2app dmgbuild
```

> ⏳ 這步驟需要等待約 1-3 分鐘，請耐心等候。

### 第 5 步：打包成 .app

```bash
# 清除舊的打包結果（第一次可以跳過）
rm -rf build dist

# 開始打包
python3 setup.py py2app
```

> ⏳ 需要等待約 2-5 分鐘。看到 `Done.` 表示成功。

打包完確認一下：

```bash
ls dist/
# 應該看到：IP Service Checker.app
```

### 第 6 步：打包成 DMG 並移除安全限制

```bash
# 移除 Gatekeeper 隔離屬性（讓同事不需要右鍵才能開啟）
xattr -cr "dist/IP Service Checker.app"

# 打包成 DMG
dmgbuild -s dmg_settings.py "IP Service Checker" "IP-Service-Checker.dmg"
```

完成！`IP-Service-Checker.dmg` 就在目前資料夾裡，傳給同事即可。

---

## 📦 給同事的安裝說明

同事收到 `IP-Service-Checker.dmg` 後：

1. 雙擊 `IP-Service-Checker.dmg` 掛載
2. 把 `IP Service Checker` 圖示拖到 `Applications` 資料夾
3. **第一次開啟**：在 Applications 找到 App → **右鍵** → **開啟** → 彈出警告視窗 → 點「**開啟**」
4. 之後直接雙擊即可正常開啟

> ⚠️ 如果同事出現「無法驗證開發者」錯誤，請他開啟 Terminal 執行：
> ```bash
> xattr -cr /Applications/IP\ Service\ Checker.app
> ```

---

## ❌ 常見錯誤處理

**錯誤：`command not found: python3`**
→ 到 https://www.python.org/downloads/ 安裝 Python

**錯誤：`ModuleNotFoundError: No module named 'webview'`**
```bash
pip install pywebview
```

**錯誤：`command not found: dmgbuild`**
```bash
pip install dmgbuild
# 或
python3 -m dmgbuild -s dmg_settings.py "IP Service Checker" "IP-Service-Checker.dmg"
```

**錯誤：`FileNotFoundError: dist/IP Service Checker.app`**
→ 第 5 步還沒完成，先執行 `python3 setup.py py2app`

**App 開啟後出現 `Launch error`**
→ 在 Terminal 執行以下指令查看詳細錯誤：
```bash
./dist/IP\ Service\ Checker.app/Contents/MacOS/IP\ Service\ Checker
```
把錯誤訊息回報給開發者。
