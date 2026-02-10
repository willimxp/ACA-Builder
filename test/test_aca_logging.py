# 测试文件：验证 ACA Builder 日志模块功能
# 使用方法：在 Blender 的 Text Editor 中运行此脚本
# 260210 创建

import sys
import os
import logging

# 添加插件路径到 sys.path
addon_path = os.path.dirname(os.path.dirname(__file__))
if addon_path not in sys.path:
    sys.path.insert(0, addon_path)

# 导入模块
from tools import aca_logging


def test_constants():
    """测试常量定义"""
    print("\n" + "=" * 60)
    print("测试1: 常量定义")
    print("=" * 60)
    
    assert aca_logging.LOGGER_NAME == "ACA", "LOGGER_NAME 应为 'ACA'"
    print(f"✓ LOGGER_NAME = '{aca_logging.LOGGER_NAME}'")
    
    assert aca_logging.DEFAULT_LOG_FILENAME == "aca_log.txt"
    print(f"✓ DEFAULT_LOG_FILENAME = '{aca_logging.DEFAULT_LOG_FILENAME}'")
    
    assert aca_logging.DEFAULT_MAX_BYTES == 5 * 1024 * 1024
    print(f"✓ DEFAULT_MAX_BYTES = {aca_logging.DEFAULT_MAX_BYTES} (5MB)")
    
    assert aca_logging.DEFAULT_BACKUP_COUNT == 3
    print(f"✓ DEFAULT_BACKUP_COUNT = {aca_logging.DEFAULT_BACKUP_COUNT}")
    
    assert len(aca_logging.LOG_LEVELS) == 4
    print(f"✓ LOG_LEVELS 定义了 {len(aca_logging.LOG_LEVELS)} 个级别")
    for level in aca_logging.LOG_LEVELS:
        print(f"  - {level[0]}: {level[1]}")


def test_get_log_level_from_string():
    """测试日志级别转换函数"""
    print("\n" + "=" * 60)
    print("测试2: 日志级别转换")
    print("=" * 60)
    
    test_cases = [
        ('DEBUG', logging.DEBUG),
        ('INFO', logging.INFO),
        ('WARNING', logging.WARNING),
        ('ERROR', logging.ERROR),
    ]
    
    for level_name, expected in test_cases:
        result = aca_logging.get_log_level_from_string(level_name)
        assert result == expected, f"{level_name} 应返回 {expected}"
        print(f"✓ {level_name} -> {result}")
    
    # 测试默认值
    result = aca_logging.get_log_level_from_string('UNKNOWN')
    assert result == aca_logging.DEFAULT_LOG_LEVEL
    print(f"✓ 未知级别返回默认值: {result}")


def test_get_default_log_path():
    """测试默认日志路径"""
    print("\n" + "=" * 60)
    print("测试3: 默认日志路径")
    print("=" * 60)
    
    log_path = aca_logging.get_default_log_path()
    print(f"✓ 默认日志路径: {log_path}")
    
    # 验证路径包含关键部分
    path_str = str(log_path)
    assert "ACA Builder" in path_str, "路径应包含 'ACA Builder'"
    assert "scripts/addons" in path_str, "路径应包含 'scripts/addons'"
    print("✓ 路径格式正确")


def test_get_logger():
    """测试获取日志记录器"""
    print("\n" + "=" * 60)
    print("测试4: 获取日志记录器")
    print("=" * 60)
    
    logger = aca_logging.get_logger()
    assert logger is not None, "应返回有效的日志记录器"
    assert logger.name == aca_logging.LOGGER_NAME, f"记录器名称应为 '{aca_logging.LOGGER_NAME}'"
    print(f"✓ 获取日志记录器成功: {logger.name}")


def test_init_logger():
    """测试初始化日志记录器"""
    print("\n" + "=" * 60)
    print("测试5: 初始化日志记录器")
    print("=" * 60)
    
    # 测试基本初始化
    logger = aca_logging.init_logger(
        log_level=logging.DEBUG,
        use_rotating=False
    )
    assert logger is not None, "应返回有效的日志记录器"
    assert logger.level == logging.DEBUG, "日志级别应设置为 DEBUG"
    assert len(logger.handlers) == 2, "应有2个处理器（控制台+文件）"
    print(f"✓ 基本初始化成功，处理器数量: {len(logger.handlers)}")
    
    # 测试日志级别
    print("✓ 测试各级别日志输出:")
    logger.debug("这是一条 DEBUG 日志")
    logger.info("这是一条 INFO 日志")
    logger.warning("这是一条 WARNING 日志")
    logger.error("这是一条 ERROR 日志")
    
    # 清理
    aca_logging.remove_logger()
    print("✓ 日志记录器清理完成")


def test_update_log_level():
    """测试动态更新日志级别"""
    print("\n" + "=" * 60)
    print("测试6: 动态更新日志级别")
    print("=" * 60)
    
    # 初始化为 INFO 级别
    logger = aca_logging.init_logger(log_level=logging.INFO)
    assert logger.level == logging.INFO
    print("✓ 初始级别: INFO")
    
    # 更新为 DEBUG 级别
    aca_logging.update_log_level(logging.DEBUG)
    assert logger.level == logging.DEBUG
    print("✓ 更新为: DEBUG")
    
    # 验证所有处理器级别已更新
    for handler in logger.handlers:
        assert handler.level == logging.DEBUG
    print("✓ 所有处理器级别已更新")
    
    # 清理
    aca_logging.remove_logger()


def test_log_system_info():
    """测试记录系统信息"""
    print("\n" + "=" * 60)
    print("测试7: 记录系统信息")
    print("=" * 60)
    
    logger = aca_logging.init_logger(log_level=logging.INFO)
    
    try:
        aca_logging.log_system_info(logger)
        print("✓ 系统信息记录成功")
    except Exception as e:
        print(f"✗ 系统信息记录失败: {e}")
    
    # 清理
    aca_logging.remove_logger()


def test_remove_logger():
    """测试移除日志处理器"""
    print("\n" + "=" * 60)
    print("测试8: 移除日志处理器")
    print("=" * 60)
    
    # 先初始化
    logger = aca_logging.init_logger()
    assert len(logger.handlers) > 0, "初始化后应有处理器"
    print(f"✓ 初始化后处理器数量: {len(logger.handlers)}")
    
    # 移除处理器
    aca_logging.remove_logger()
    assert len(logger.handlers) == 0, "移除后应无处理器"
    print("✓ 移除后处理器数量: 0")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("ACA Builder 日志模块回归测试")
    print("=" * 60)
    
    tests = [
        test_constants,
        test_get_log_level_from_string,
        test_get_default_log_path,
        test_get_logger,
        test_init_logger,
        test_update_log_level,
        test_log_system_info,
        test_remove_logger,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n✗ 测试失败: {e}")
            failed += 1
        except Exception as e:
            print(f"\n✗ 测试异常: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"通过: {passed}/{len(tests)}")
    print(f"失败: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n✓ 所有测试通过!")
    else:
        print(f"\n✗ {failed} 个测试失败")
    
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
