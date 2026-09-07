# Panasonic RS485 Home Assistant Integration

🏠 **松下新风系统 RS485/Modbus 集成** - 将 Panasonic 新风系统接入 Home Assistant

通过 RS485/Modbus TCP 网关读取传感器数据并控制新风系统，支持模式切换、风速调节、时间同步等功能。

## 功能特性

- 🌡️ 传感器数据：温度、湿度、PM2.5、CO2、TVOC
- 🌀 运行模式：热交换 / 普通换气 / 内循环 / 自动 / 静音 / 混风
- 💨 风速：低 / 高
- 🔌 电源开关与度假模式开关
- ⏰ 时间同步按钮 + 每 6 小时自动校时
- 🔄 断线自动重连：网关重启后无需重载集成，下一次轮询自动恢复
- 📱 UI 配置
- 🌐 中文界面

## 硬件要求

- 松下新风系统（支持 RS485/Modbus 协议）
  - 参考型号：`FY-15ZJD2C`、`FY-25ZJD2C`、`FY-35ZJD2C`
- Modbus TCP 网关（RS485 → TCP）
- Home Assistant 实例

## 安装

### HACS

1. HACS → 集成 → 右上角 ⋮ → 自定义存储库
2. 添加 `https://github.com/kkesaikou6717/panasonic_rs485_homeassistant`，类别选择“集成”
3. 下载后重启 Home Assistant

### 手动安装

```text
<config>/custom_components/
└── fresh_air/
```

将本仓库 `custom_components/fresh_air/` 整个目录复制到 Home Assistant 配置目录的 `custom_components/` 下，然后重启。

## 配置

设置 → 设备与服务 → 添加集成 → 搜索“新风系统”或 Fresh Air。

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 网关地址 | Modbus TCP 网关 IP | `10.0.0.6` |
| 端口 | Modbus TCP 端口 | `10123` |
| 设备地址 | 从站地址 | `1` |

网关在添加集成时必须可达；运行中若网关重启，集成会自动重连。

## 实体

添加成功后设备下会生成以下实体（实体 ID 以 HA 实际显示为准）：

- 开关：电源、度假模式
- 选择器：运行模式、风速
- 按钮：同步时间
- 传感器：室外/送风/回风 PM2.5、湿度、温度，回风 CO2、TVOC

## 服务

- `fresh_air.sync_time`：同步系统时间（也可直接使用“同步时间”按钮）

```yaml
service: fresh_air.sync_time
```

## 开发与测试

测试使用本地模拟 Modbus TCP 网关，不依赖真实硬件：

```bash
python -m venv .venv
pip install pymodbus==3.6.9 pytest
python -m pytest tests -v
```

覆盖内容：寄存器读写、传感器解析、控制写入、网关重启后的自动重连与恢复采集。

## 协议文档

- `rs485.csv` / `rs485.xlsx`：寄存器地址表
- `RS485设置方法.pdf`：RS485 设置说明

## 许可证

MIT License - 详见 [LICENSE](LICENSE)