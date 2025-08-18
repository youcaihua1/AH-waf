"""
模块名称: test_bypass_switch_time.py

该模块的目标：
    测试 bypass 切换时间
  
作者: ych
修改历史:
    1. 2025/8/14 - 创建文件
"""
import re
import pytest
import allure
from loguru import logger
from testcase.cfg_example.cfg_skip import SkipByCase  # 自定义跳过条件
from env.config import WafDut  # 导入WAF设备信息
import threading  # 多线程支持


class TestBypassSwitchTime:
    ping_num = 200  # ping测试的次数

    @staticmethod
    def get_bridge_interface():
        bridge_interface = WafDut().topo_cfg['networks'][0]['bridge']['net_dev']  # 从WAF设备配置中获取桥接接口名称
        return bridge_interface

    @staticmethod
    def ping_server(get_system_op_obj, ping_num):  # 执行ping命令到服务器IP
        res = get_system_op_obj.exec_cmd(f"ping {WafDut().topo_cfg['servers'][0]['ip']} -c {ping_num}")
        return res

    @staticmethod
    def first_func(get_system_op_obj, ping_num, interface_type):
        res = TestBypassSwitchTime.ping_server(get_system_op_obj, ping_num)  # 执行ping测试
        result = re.findall(r'transmitted,\s(\d+).*?received', res)  # 使用正则表达式提取丢包数量

        # 根据接口类型设置不同的丢包阈值
        if interface_type == 'electric':  # 电口
            assert int(result[0]) > ping_num - 6  # 验证丢包不超过5个
        if interface_type == 'light':  # 光口
            assert int(result[0]) > ping_num - 3  # 验证丢包不超过2个
        return

    @staticmethod
    def second_func(g_api_global, run_level):
        g_api_global.run_level_update(params=run_level)  # 更新设备的运行级别
        return

    @allure.title('bypass切换时间验证')
    @allure.description('''
    前提条件：
    1、硬件设备含有bypass网卡
    测试步骤：
    1、正常防护切换到物理直通，保持ping server不停，查看丢包个数【check1】
    2、物理直通切换到正常防护，保持ping server不停，查看丢包个数【check1】
    预期结果
    【check1】电口丢包6个以内，光口丢包3个以内板卡灯显示正常
    ''')
    @pytest.mark.level2
    @pytest.mark.simple_smoke  # 简单冒烟测试
    @pytest.mark.transparent  # 透明模式测试
    @SkipByCase.SKIP_NOT_STANDALONE  # 非独立环境跳过
    @SkipByCase.SKIP_NOT_HARDWARE_ENVIRONMENT  # 非硬件环境跳过
    # 参数化测试：定义两种测试场景
    @pytest.mark.parametrize("init_status, desc, run_level", [
        ({"level": "none_execute"}, "1、正常防护切换到物理直通，保持ping server不停，查看丢包个数【check1】",
         {"level": "bypass_dev"}),
        ({"level": "bypass_dev"}, "2、物理直通切换到正常防护，保持ping server不停，查看丢包个数【check1】",
         {"level": "none_execute"})
    ])
    def test_bypass_switch_time(self, g_api_global, desc, run_level, get_system_op_obj, init_status):
        with allure.step(desc):
            logger.info(desc)
            g_api_global.run_level_update(params=init_status)  # 设置初始运行级别

            interface_all_info = g_api_global.interface_aggregate_get()  # 获取所有接口信息
            logger.info(interface_all_info)

            bridge_interface = self.get_bridge_interface()  # 获取桥接接口名称

            for interface_info in interface_all_info:  # 遍历接口信息，确定接口类型
                if interface_info['name'] in bridge_interface:
                    interface_status = interface_info['status']
                    logger.info(interface_status)
                    # 根据接口状态判断是电口还是光口
                    if interface_status == '1000Mb/s':
                        interface_type = 'electric'  # 电口
                    else:
                        interface_type = 'light'  # 光口

            # 创建两个线程
            t1 = threading.Thread(  # 线程1：执行ping测试并验证结果
                name="first_func",
                target=self.first_func,
                kwargs={
                    'get_system_op_obj': get_system_op_obj,
                    'ping_num': self.ping_num,
                    'interface_type': interface_type
                }
            )

            t2 = threading.Thread(  # 线程2：执行运行级别切换
                name="second_func",
                target=self.second_func,
                kwargs={
                    'g_api_global': g_api_global,
                    'run_level': run_level
                }
            )

            t1.start()  # 启动线程
            t2.start()

            t1.join()  # 等待线程结束
            t2.join()
