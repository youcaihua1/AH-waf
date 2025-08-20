"""
模块名称: test_vlan_modify.py

该模块的目标：
    测试VLAN修改功能
  
作者: ych
修改历史:
    1. 2025/8/20 - 创建文件
"""
import pytest
import allure

from testcase.cfg_example.cfg_skip import SkipByCase
from testcase.utils.id_update import node_namespace_update  # 导入命名空间更新函数


class TestVLANModify:
    @staticmethod
    def create_vlan(g_api_global, g_default_cfg_vlan):
        """
        创建一个vlan返回其对应信息
        """
        query_get = {'type': 'vlan'}  # 筛选类型为vlan
        query_get = node_namespace_update(  # 更新命名空间参数
            namespace_map_name='namespace_id',
            param_obj=query_get,
            api_obj=g_api_global
        )
        dev_name_list = g_api_global.interface_filter_get(**query_get)['choices']  # 获取符合条件的接口设备列表
        if len(dev_name_list) < 1:
            pytest.skip('当前接口数量不足以支持本用例执行 请检查运行环境')
        g_default_cfg_vlan.net_dev = dev_name_list[0]  # 使用第一个可用接口作为VLAN设备
        vlan_info = g_api_global.vlan__list_set(params=g_default_cfg_vlan)  # 创建VLAN并获取返回信息
        return {'pk': vlan_info['_pk'], 'name': vlan_info['name'], 'desc': 'for test'}  # 返回VLAN的关键信息：主键、名称和测试描述

    @allure.title('网络层修改VLAN')
    @allure.description('''  # allure报告的详细描述
        预置条件
            1、WAF正常启动。
            2、建立正常的配置连接。
        测试步骤
            1、修改VLAN描述【check1】
        预期结果
            【check1】修改VLAN成功，界面显示与配置一致
    ''')
    @pytest.mark.level4
    @SkipByCase.SKIP_NOT_NUMBER_INTERFACE_4
    def test_vlan_modify(self, g_api_global, g_default_cfg_vlan, reset_network_by_cfg):
        vlan_info = self.create_vlan(g_api_global, g_default_cfg_vlan)  # 创建测试用的VLAN并获取信息
        with allure.step('1、修改VLAN描述【check1】'):
            g_default_cfg_vlan.desc = vlan_info['desc']  # 更新VLAN配置对象的描述
            g_api_global.vlan__detail_update(  # 调用API修改VLAN描述
                pk=vlan_info['pk'],
                params=g_default_cfg_vlan
            )
            g_api_global.config_issued_global_get_until_zero()  # 等待配置下发完成（全局配置生效）
            assert g_api_global.vlan__detail_get(pk=vlan_info['pk'])['desc'] == vlan_info['desc']
