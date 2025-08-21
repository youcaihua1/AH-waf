"""
模块名称: test_vlan_limit.py

该模块的目标：
    测试VLAN接口的数量限制
  
作者: ych
修改历史:
    1. 2025/8/20 - 创建文件
"""
import pytest
import allure
from swagger_client.lib.common import ApiException
from testcase.cfg_example.cfg_skip import SkipByCase
from testcase.utils.id_update import node_namespace_update


class TestVLANLimit:
    @allure.title('接口VLAN上限测试')
    @allure.description('''  
        预置条件
            1、WAF正常启动。
            2、建立正常的配置连接。
        测试步骤
            vlan接口上限【check1】
        预期结果
            【check1】单物理口vlan可以配置64个
    ''')
    @pytest.mark.level3
    @SkipByCase.SKIP_NOT_NUMBER_INTERFACE_4
    def test_vlan_limit(self, g_api_global, g_default_cfg_vlan, reset_network_by_cfg):
        query_get = {'type': 'vlan'}  # 查询的接口类型为"vlan"
        query_get = node_namespace_update(
            namespace_map_name='namespace_id',
            param_obj=query_get,
            api_obj=g_api_global
        )  # 更新查询参数
        dev_name_list = g_api_global.interface_filter_get(**query_get)['choices']  # 获取符合条件的接口设备列表
        if len(dev_name_list) < 1:
            pytest.skip('当前接口数量不足以支持本用例执行 请检查运行环境')
        g_default_cfg_vlan.net_dev = dev_name_list[0]  # 使用第一个可用物理接口作为VLAN的基础设备
        with allure.step('vlan接口上限【check1】'):
            for index in range(64):  # 创建一个物理接口上创建64个VLAN接口
                g_default_cfg_vlan.tag_id = index + 1  # 设置VLAN标签ID（1到64）
                g_api_global.vlan__list_set(params=g_default_cfg_vlan)  # 调用API创建VLAN接口

            with pytest.raises(ApiException):  # 预期尝试创建第65个VLAN时应抛出ApiException
                g_default_cfg_vlan.tag_id = 999  # 设置一个不同的VLAN标签ID（999）避免重复
                g_api_global.vlan__list_set(params=g_default_cfg_vlan)  # 尝试创建第65个VLAN接口（预期会因数量限制而失败）
