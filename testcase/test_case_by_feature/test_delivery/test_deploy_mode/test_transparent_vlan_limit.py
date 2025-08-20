"""
模块名称: test_transparent_vlan_limit.py

该模块的目标：
    验证WAF设备处理1000个VLAN配置的能力（上限测试）
  
作者: ych
修改历史:
    1. 2025/8/18 - 创建文件
"""
import pytest
import allure


class TestTransparentVlanLimit:
    @allure.title('透明代理VLAN识别规格测试')
    @allure.description('''
    前置条件：
        1、WAF正常启动。
        2、建立正常的配置连接。
    测试步骤：
        1、透明代理VLAN识别上限【check1】
    预期结果：
        【check1】上限为1000个
    ''')
    @pytest.mark.transparent
    def test_transparent_vlan_limit(self, g_api_global):
        ip_vlan_map = []  # 创建空列表，用于存储要生成的VLAN配置
        ip_num = 0  # 初始化IP地址计数器（用于控制IP地址的生成）

        for index in range(1000):  # 循环生成1000个VLAN配置项（对应测试的规格上限）
            if index % 255 == 0:  # 当循环索引能被255整除时（每256个IP），递增IP地址第三段
                ip_num += 1

            # 构建VLAN配置字典并添加到列表：
            # - ip_mask: IP地址（格式如1.1.*.*/32）
            # - svlan: 源VLAN ID（固定为2）
            # - dvlan: 目标VLAN ID（固定为2）
            ip_vlan_map.append({
                "ip_mask": f"1.1.{ip_num}.{index % 255}/32",
                "svlan": 2,
                "dvlan": 2
            })
        with allure.step('1、透明代理VLAN识别上限【check1】'):
            params = g_api_global.net_parameter__list_get()  # 获取当前的网络配置（通过全局API对象）
            params['ip_vlan_map'] = ip_vlan_map  # 将生成的1000个VLAN配置应用到网络参数中

            # 使用API更新网络配置：
            # - pk: 主键（从当前配置中获取）
            # - params: 包含新VLAN配置的完整参数对象
            g_api_global.net_parameter_update(pk=params['_pk'], params=params)