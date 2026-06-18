## 下載

| 平台 | 下載 |
|---|---|
| macOS | [IP-Service-Checker.dmg](https://github.com/leifeng1688/ip-service-checker/releases/latest/download/IP-Service-Checker.dmg) |
| Windows | [IP-Service-Checker.exe](https://github.com/leifeng1688/ip-service-checker/releases/latest/download/IP-Service-Checker.exe) |

# IP Service Checker
> 網路服務掃描工具，支援 TCP Port 掃描、HTTP 狀態檢查、SSL/TLS 憑證查詢。

![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 功能

| 模式 | 說明 |
|---|---|
| **TCP** | 掃描 Port 開關狀態、Banner 抓取、服務識別 |
| **HTTP** | 查詢 URL 回應狀態碼與 Server Header |
| **SSL** | 查詢 TLS 憑證（CN、SAN、發行單位、到期日、剩餘天數） |

**共同功能：**
- 批次掃描（貼入多筆目標）
- 多執行緒並發（可調整）
- 即時 LOG + TABLE 視圖切換
- 匯出 HTML 報告 / CSV
- 在瀏覽器開啟報告

---

## 專案結構

```
ip-service-checker/
├── src/
│   └── ip-service_check_app.py   # 主程式（macOS / Windows 共用）
├── macos/
│   ├── README.md                 # ← macOS 打包步驟（從這裡開始）
│   ├── setup.py
│   ├── dmg_settings.py
│   ├── icon.icns
│   └── icon_1024.png
├── windows/
│   ├── README.md                 # ← Windows 打包步驟（從這裡開始）
│   ├── ip_checker.spec
│   ├── version_info.txt
│   └── icon_windows.ico
├── .gitignore
├── LICENSE
└── README.md                     # 本文件
```

---

## 快速開始（直接執行，不打包）

```bash
# 建立虛擬環境
python3 -m venv venv
source venv/bin/activate      # macOS
# venv\Scripts\activate       # Windows

# 安裝依賴
pip install pywebview requests chardet

# 執行
python3 src/ip-service_check_app.py
```

---

## 打包成應用程式

| 平台 | 說明文件 |
|---|---|
| macOS → `.dmg` | [macos/README.md](macos/README.md) |
| Windows → `.exe` | [windows/README.md](windows/README.md) |

---

## 系統需求

| 平台 | 需求 |
|---|---|
| macOS | macOS 11+ / Python 3.11+ |
| Windows | Windows 10/11 64bit / Python 3.11 / WebView2（Win11 內建）|

---

## License

MIT License © 2026 LeiFeng
