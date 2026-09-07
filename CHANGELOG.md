# Changelog

本项目的版本变更记录。

## [1.1.1] - 2026-09-07

### Added

- 新增 `custom_components/fresh_air/services.yaml`，为注册的 `fresh_air.sync_time` 服务提供 Home Assistant 要求的服务描述文件。
- 在 `translations/zh-Hans.json` 中补充 `sync_time` 服务的中文名称与描述。

### Fixed

- 修复调用 `fresh_air.sync_time` 服务时，Home Assistant 报 `Failed to load services.yaml for integration: fresh_air` 的问题。

## [1.1.0] - 2026-09-07

### Changed

- Modbus 客户端断线自动重连，读/写失败重连后重发一次。
- 实体改为 `CoordinatorEntity`，首次刷新并恢复 30 秒周期轮询。
- 修复 `fresh_air.sync_time` 服务、周日星期映射、INT16 负温度与单位。
- 更新 `manifest.json` / `README.md` / `DEPLOYMENT.md`，补充 MIT LICENSE 与模拟网关测试。
