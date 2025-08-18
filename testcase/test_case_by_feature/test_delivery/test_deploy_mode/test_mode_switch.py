"""
模块名称: test_mode_switch.py

该模块的目标：
    验证 WAF设备在不同工作模式之间切换时的行为
  
作者: ych
修改历史:
    1. 2025/8/18 - 创建文件
"""
import pytest
import allure
from testcase.cfg_example.cfg_api import SkipByCase


class TestModeSwitch:
    @pytest.fixture(scope='function')  # 该夹具用于在每个测试执行后将WAF模式重置为透明代理
    def reset_deploy(self, g_api_global):
        yield
        g_api_global.deploy_update('transparent')  # 将部署模式重置为透明代理

    @allure.title('透明代理模式切换功能验证')
    @allure.description('''
    1、接入方式切换为反向代理，提示"切换后需要重新配置网络配置"，查看网络配置【check1】
    2、接入方式切换为路由牵引，提示"切换后需要重新配置网络配置"，查看网络配置【check1】
    3、接入方式切换为旁路监控，提示"切换后需要重新配置网络配置"，查看网络配置【check1】
    【check1】接入方式切换成功，网络配置不变化。
    ''')
    @pytest.mark.level2
    @pytest.mark.smoke
    @pytest.mark.transparent
    @SkipByCase.SKIP_NOT_STANDALONE  # 非单机环境跳过此测试
    def test_mode_switch(self, g_api_global, get_waf_ssh_obj, reset_deploy):
        mode_list = ['reverse', 'traction', 'sniffer', 'transparent']  # 四种部署模式
        # •reverse: 反向代理模式   •traction: 路由牵引模式
        # •sniffer: 旁路监控模式   •transparent: 透明代理模式

        for mode in mode_list:  # 遍历所有部署模式进行测试
            net_config = get_waf_ssh_obj.exec_cmd('ip a')  # 获取当前WAF设备的网络配置（使用SSH执行'ip a'命令）
            g_api_global.deploy_update(mode)  # 调用API将部署模式更新为当前测试模式
            mode_now = g_api_global.deploy_get()  # 查询当前部署模式以验证更新是否成功
            assert mode_now == mode  # 断言1：确认更新后的模式与预期一致

            # 断言2：确保网络配置没有因模式切换而改变
            # 比较切换前后的'ip a'命令输出结果（索引[1]获取命令返回的stdout内容）
            assert net_config[1] == get_waf_ssh_obj.exec_cmd('ip a')[1]
