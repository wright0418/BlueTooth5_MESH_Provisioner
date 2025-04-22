# MeshDeviceManager 使用說明

## 簡介
`mesh_device_manager.py` 是一個用於管理 RL62M02 Mesh 裝置的 Python 命令列工具，支援裝置掃描、綁定、解除綁定、自動綁定、裝置列表等功能，並可將裝置資訊儲存於 JSON 檔案。

## 執行方式

```bash
python mesh_device_manager.py <COM埠> [子命令] [參數]
```
- `<COM埠>`：指定 RL62M02 裝置連接的序列埠，例如 `COM3`

## 支援子命令與參數

- `scan`：掃描周圍 Mesh 裝置
  - `--time <秒數>`：掃描時間（預設 5 秒）
- `bind`：綁定單一裝置
  - `--uuid <裝置UUID>`
  - `--name <裝置名稱>`
  - `--subscribe <群組地址>`（選填，預設 0xC000）
  - `--publish <群組地址>`（選填，預設 0xC000）
- `unbind-all`：解除所有裝置綁定
  - `--clear-json`：同時清空 JSON 裝置記錄檔（預設不清空）
- `auto-bind`：根據 JSON 檔自動綁定裝置
- `list`：列出已記錄的裝置
- `reset-and-bind`：先解除所有裝置綁定，再綁定單一裝置
  - `--uuid <裝置UUID>`
  - `--name <裝置名稱>`
  - `--subscribe <群組地址>`（選填）
  - `--publish <群組地址>`（選填）
- `scan-and-bind`：互動式掃描並綁定裝置
  - `--time <秒數>`（預設 5 秒）
  - `--subscribe <群組地址>`（選填）
  - `--publish <群組地址>`（選填）

## 常用範例

1. 掃描裝置：
```bash
python mesh_device_manager.py COM3 scan --time 5
```

2. 綁定裝置：
```bash
python mesh_device_manager.py COM3 bind --uuid <裝置UUID> --name "客廳燈"
```

3. 解除所有裝置綁定：
```bash
python mesh_device_manager.py COM3 unbind-all
```

4. 解除所有裝置綁定並清空 JSON 裝置記錄檔：
```bash
python mesh_device_manager.py COM3 unbind-all --clear-json
```

5. 自動綁定（根據 mesh_devices_config.json）：
```bash
python mesh_device_manager.py COM3 auto-bind
```

6. 列出已記錄裝置：
```bash
python mesh_device_manager.py COM3 list
```

7. 互動式掃描並綁定：
```bash
python mesh_device_manager.py COM3 scan-and-bind
```

## 注意事項
- 執行前請確認已安裝 rl62m02 套件及相關依賴。
- 預設裝置資訊儲存於 mesh_devices_config.json，可用 `--device-file` 指定其他檔案。
- 詳細日誌可加上 `--debug` 參數。
- 綁定/解除綁定過程請確保裝置已上電且在有效範圍內。

---
如需進階功能或遇到問題，請參考原始碼註解或聯絡開發者。
