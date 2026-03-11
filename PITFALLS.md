# PITFALLS.md — 已知問題與解決方案

記錄踩過的坑，避免新對話重複犯錯。

---

## Python 套件

### google.generativeai 已棄用
- **問題**：執行時出現 `FutureWarning: All support for the google.generativeai package has ended`
- **原因**：Google 已停止維護 `google-generativeai`，官方改用新套件 `google-genai`
- **解法**：待需要時將 `requirements.txt` 的 `google-generativeai` 換成 `google-genai`，並更新 `main.py` 的 import（`import google.generativeai` → `from google import genai`）
- **現況**：目前仍可正常運作，只是警告，不影響功能；待 API 真正失效前不急著改
