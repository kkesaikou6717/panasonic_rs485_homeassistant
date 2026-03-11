# HomeAssistant 部署指南

## 方式一：通过 HACS 安装（推荐）

1. **安装 HACS**（如果未安装）
   - 在 HomeAssistant 设置 → 添加-on 中搜索 "HACS"
   - 按照提示完成安装

2. **安装新风系统集成**
   - 进入 HACS → 集成
   - 点击右上角 ⋮ → 自定义存储库
   - 填写仓库地址
   - 搜索 "Fresh Air" 或 "新风系统"
   - 点击下载

3. **重启 HomeAssistant**
   - 设置 → 系统 → 重新启动

4. **添加设备**
   - 设置 → 设备与服务 → 添加集成
   - 搜索 "Fresh Air" 或 "新风系统"
   - 按照提示配置网关地址和端口

---

## 方式二：手动安装

1. **复制文件**
   ```
   将 custom_components/fresh_air/ 目录复制到
   HomeAssistant 配置目录下的 custom_components/ 目录
   ```

   目录结构：
   ```
   custom_components/
   └── fresh_air/
       ├── __init__.py
       ├── climate.py
       ├── config_flow.py
       ├── const.py
       ├── manifest.json
       ├── modbus_client.py
       ├── sensor.py
       ├── services.py
       ├── switch.py
       └── translations/
           └── zh-Hans.json
   ```

2. **重启 HomeAssistant**
   - 设置 → 系统 → 重新启动

3. **添加设备**
   - 设置 → 设备与服务 → 添加集成
   - 搜索 "Fresh Air"
   - 输入 Modbus 网关信息
     - 网关地址：默认 `10.0.0.6`
     - 端口：默认 `10123`
     - 设备地址：默认 `1`

---

## 配置选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| host | Modbus 网关 IP 地址 | 10.0.0.6 |
| port | Modbus 端口 | 10123 |
| slave | 从站地址 | 1 |

---

## 验证安装

1. 检查集成是否正常加载：
   - 设置 → 系统 → 日志 → 查看是否有 fresh_air 相关日志

2. 查看设备：
   - 设置 → 设备与服务 → 已配置设备

3. 可用实体：
   - `climate.fresh_air` - 新风系统（开关、模式、风速）
   - `sensor.*_temp_*` - 温度传感器
   - `sensor.*_humidity_*` - 湿度传感器  
   - `sensor.*_pm25_*` - PM2.5 传感器
   - `sensor.*_co2_*` - CO2 传感器
   - `sensor.*_tvoc_*` - TVOC 传感器
   - `switch.fresh_air_vacation_mode` - 度假模式开关

---

## 服务

| 服务 | 说明 |
|------|------|
| `fresh_air.sync_time` | 同步时间 |

调用示例：
```yaml
service: fresh_air.sync_time
```

---

## 故障排除

1. **连接失败**
   - 检查网关 IP 和端口是否正确
   - 确认网络可达性
   - 查看 HomeAssistant 日志

2. **时间同步失败**
   - 检查网关是否支持时间写入
   - 确认时间格式正确

3. **传感器数据无效**
   - 检查传感器是否连接
   - 确认寄存器地址正确
