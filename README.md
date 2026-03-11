# Panasonic RS485 Home Assistant Integration

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2023.1%2B-blue)](https://www.home-assistant.io/)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange)](https://hacs.xyz/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

🏠 **松下新风系统 RS485 Modbus 集成** - 将 Panasonic 新风系统接入 Home Assistant

通过 RS485/Modbus 协议控制松下新风系统，支持传感器数据读取、模式切换、风速调节等功能。

---

## ✨ 功能特性

- 🌡️ **传感器数据** - 温度、湿度、PM2.5、CO2、TVOC 实时监测
- 🌀 **模式控制** - 自动/手动/睡眠/度假等多种模式
- 💨 **风速调节** - 多档风速控制
- ⏰ **时间同步** - 自动同步设备时间
- 🏖️ **度假模式** - 支持度假模式开关
- 📱 **UI 配置** - 通过 Home Assistant UI 轻松配置
- 🌐 **中文支持** - 完整的中文界面

---

## 📋 硬件要求

- 松下新风系统（支持 RS485/Modbus 协议）
  - **已测试型号：** `FY-15ZJD2C`、`FY-25ZJD2C`、`FY-35ZJD2C`
- Modbus TCP 网关（将 RS485 转换为 TCP）
- Home Assistant 实例

---

## 🚀 安装方式

### 方式一：HACS 安装（推荐）

1. 安装 [HACS](https://hacs.xyz/)（如未安装）
2. 进入 HACS → 集成 → 右上角 ⋮ → 自定义存储库
3. 添加仓库地址：`https://github.com/kkesaikou6717/panasonic_rs485_homeassistant`
4. 选择类别：**集成**
5. 搜索 "新风系统" 并下载
6. 重启 Home Assistant

### 方式二：手动安装

1. 下载此仓库代码
2. 将 `custom_components/fresh_air/` 目录复制到 Home Assistant 配置目录：
   ```
   <config>/custom_components/fresh_air/
   ```
3. 重启 Home Assistant

---

## ⚙️ 配置

1. 进入 **设置** → **设备与服务** → **添加集成**
2. 搜索 "**新风系统**" 或 "**Fresh Air**"
3. 输入 Modbus 网关信息：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 网关地址 | Modbus TCP 网关 IP | `10.0.0.6` |
| 端口 | Modbus TCP 端口 | `10123` |
| 设备地址 | 从站地址 (Slave ID) | `1` |

---

## 📊 可用实体

集成添加后，会自动创建以下实体：

### 气候 (Climate)
- `climate.fresh_air` - 新风系统主控制
  - 开关控制
  - 模式选择：自动/手动/睡眠/度假
  - 风速调节

### 传感器 (Sensor)
| 实体 | 说明 | 单位 |
|------|------|------|
| `sensor.outdoor_temp` | 室外温度 | °C |
| `sensor.indoor_temp` | 室内温度 | °C |
| `sensor.outdoor_humidity` | 室外湿度 | % |
| `sensor.indoor_humidity` | 室内湿度 | % |
| `sensor.pm25` | PM2.5 浓度 | μg/m³ |
| `sensor.co2` | CO2 浓度 | ppm |
| `sensor.tvoc` | TVOC 浓度 | mg/m³ |

### 开关 (Switch)
- `switch.fresh_air_vacation_mode` - 度假模式

---

## 🔧 服务调用

### 同步时间
```yaml
service: fresh_air.sync_time
target:
  entity_id: climate.fresh_air
```

---

## 📁 项目结构

```
custom_components/fresh_air/
├── __init__.py          # 集成初始化
├── manifest.json        # 集成清单
├── config_flow.py       # 配置流程
├── const.py             # 常量定义
├── modbus_client.py     # Modbus 通信
├── climate.py           # 气候实体
├── sensor.py            # 传感器实体
├── switch.py            # 开关实体
├── button.py            # 按钮实体
├── select.py            # 选择实体
├── services.py          # 服务定义
└── translations/        # 翻译文件
    └── zh-Hans.json
```

---

## 🛠️ 开发相关

### 测试脚本

项目包含以下测试脚本：

- `test_modbus.py` - Modbus 通信测试
- `test_sensors.py` - 传感器数据测试
- `test_vacation.py` - 度假模式测试
- `fresh_air_control.py` - 独立控制脚本

### 依赖

- `pymodbus>=3.0.0`

---

## 🐛 故障排除

### 连接失败
- 检查网关 IP 和端口是否正确
- 确认网络可达性（`ping <网关IP>`）
- 查看 Home Assistant 日志中的错误信息

### 传感器数据异常
- 检查传感器是否正常工作
- 确认寄存器地址配置正确
- 查看 `rs485.csv` 或 `rs485.xlsx` 中的寄存器定义

### 时间同步失败
- 确认网关支持时间写入功能
- 检查设备是否在线

---

## 📄 协议文档

项目包含松下 RS485 通信协议文档：
- [`RS485设置方法.pdf`](RS485设置方法.pdf) - RS485 设置方法说明文档
- `rs485.csv` - 寄存器地址表（CSV 格式）
- `rs485.xlsx` - 寄存器地址表（Excel 格式）

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📜 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [Home Assistant](https://www.home-assistant.io/)
- [pymodbus](https://github.com/pymodbus/pymodbus)

---

💡 **提示**：此集成为非官方集成，与 Panasonic 公司无关。
