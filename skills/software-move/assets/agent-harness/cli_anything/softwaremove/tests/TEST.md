# 测试计划 - cli-anything-softwaremove

## 测试清单

- test_core.py：计划 6 个单元测试
- test_full_e2e.py：计划 2 个端到端测试

## 单元测试计划

模块：core/history.py
- add_record 创建带 ID 的记录
- load_history 返回按时间排序的记录
- mark_restored 切换还原标志
- delete_record 删除记录

模块：utils/softwaremove_backend.py
- format_size 格式化大小边界
- move_software（link_mode=none）在临时文件夹中迁移文件

## 端到端测试计划

流程：迁移并在临时文件夹中还原
- 创建包含嵌套文件的临时源目录
- 使用 link_mode=none 运行 CLI 迁移
- 验证目标文件存在
- 运行 CLI history undo
- 验证文件已还原到源目录

流程：history list
- 运行 CLI history list 并确保 JSON 输出可解析
