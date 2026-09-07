# HomeAssistant 部署指南（新风系统）

## 方式一：HACS 安装（推荐）

1. HACS → 集成 → 右上角 ⋮ → 自定义存储库
2. 添加：`https://github.com/kkesaikou6717/panasonic_rs485_homeassistant`
3. 类别选择：**集成**
4. 下载完成后重启 Home Assistant
5. 设置 → 设备与服务 → 添加集成 → 搜索“新风系统”或 Fresh Air
6. 输入 Modbus TCP 网关信息

## 方式二：手动安装

把本目录中的 `custom_components/fresh_air/` 复制到 HA 配置目录：

```text
custom_components/
└── fresh_air/
    ├── __init__.py
    ├── manifest.json
    ├── config_flow.py
    ├── const.py
    ├── modbus_client.py
    ├── sensor.py
    ├── switch.py
    ├── select.py
    ├── button.py
    ├── services.py
    └── translations/
        └── zh-Hans.json
```

重启 HA 后，在 设置 → 设备与服务 → 添加集成 中搜索“新风系统”或 Fresh Air。

## 配置项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| host | Modbus 网关 IP 地址 | 10.0.0.6 |
| port | Modbus 端口 | 10123 |
| slave | 从站地址 | 1 |

网关必须能 ping 通；添加集成时会先做连接测试。

## 可用实体

添加成功后，设备下会生成：

- 电源开关 / 度假模式开关
- 运行模式选择（热交换、普通换气、内循环、自动、静音、混风）
- 风速选择（低、高）
- 同步时间按钮
- 室外/送风/回风 PM2.5、温湿度，回风 CO2、TVOC 传感器

## 服务

`fresh_air.sync_time`：同步设备时间。

```yaml
service: fresh_air.sync_time
```

## 故障排除

- 添加集成失败：检查 IP/端口/从站地址，确认网关可达。
- 网关重启后暂时无数据：30 秒轮询内会自动重连并恢复，无需重载集成。
- 日志搜索 `fresh_air` 可查看连接与更新状态。