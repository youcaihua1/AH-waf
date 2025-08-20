"""
模块名称: test_vlan_create.py

该模块的目标：
    测试创建VLAN的功能
  
作者: ych
修改历史:
    1. 2025/8/18 - 创建文件
"""
import pytest
import allure
from loguru import logger
from testcase.cfg_example.cfg_skip import SkipByCase
from testcase.utils.id_update import node_namespace_update  # 导入命名空间更新函数


class TestVLANCreate:
    @allure.title('网络层创建VLAN')
    @allure.description('''
        预置条件
            1、WAF正常启动。
            2、建立正常的配置连接。
        测试步骤
            1、物理接口作为父接口，创建VLAN子接口【check1】【check2】
            2、链路聚合口作为父接口，创建VLAN子接口【check1】【check2】
        预期结果
            【check1】创建VLAN成功，界面显示与配置一致
            【check2】linux查看接口ip address一致
    ''')
    @pytest.mark.level4  # 标记测试级别为level4（较低优先级）
    @SkipByCase.SKIP_NOT_NUMBER_INTERFACE_4  # 没有足够的网络接口时跳过测试
    def test_vlan_create(self, g_api_global, g_default_cfg_vlan, g_default_cfg_bond, reset_network_by_cfg,
                         get_node_ssh_obj):
        with allure.step(' 1、物理接口作为父接口，创建VLAN子接口【check1】【check2】'):
            query_get = {'type': 'vlan'}  # 只筛选vlan类型接口
            query_get = node_namespace_update(
                namespace_map_name='namespace_id',
                param_obj=query_get,
                api_obj=g_api_global)  # 更新命名空间
            dev_name_list = g_api_global.interface_filter_get(**query_get)['choices']  # 获取可用的VLAN接口设备列表
            logger.info(f'dev_name_list: {dev_name_list}')  # 记录获取的设备列表
            ssh_connection = get_node_ssh_obj  # 获取SSH连接对象
            g_default_cfg_vlan.net_dev = dev_name_list[0]  # 配置默认VLAN设置：选择第一个物理接口作为父接口
            vlan_res = g_api_global.vlan__list_set(params=g_default_cfg_vlan)  # 通过API创建VLAN子接口
            g_api_global.config_issued_global_get_until_zero()  # 等待配置生效（轮询直到配置发布成功）

            # 验证【check1】和【check2】：
            # 检查SSH命令输出中是否包含新创建的VLAN接口
            assert f'{dev_name_list[0]}.{g_default_cfg_vlan.tag_id}' in ssh_connection.exec_cmd(cmd='ip address')[1]
            g_api_global.vlan__detail_delete(pk=vlan_res["_pk"])  # 测试完成后删除创建的VLAN配置

        with allure.step('2、链路聚合口作为父接口，创建VLAN子接口【check1】【check2】'):
            query_get = {'type': 'bond'}  # 查询可用的bond类型接口
            query_get = node_namespace_update(namespace_map_name='namespace_id', param_obj=query_get,
                                              api_obj=g_api_global)  # 更新命名空间
            bond_support_list = g_api_global.interface_filter_get(**query_get)['choices']  # 获取支持的链路聚合接口列表
            bond_last_seq = min(len(bond_support_list), 2)  # 确定bond接口数量（至少2个接口才能创建bond）
            g_default_cfg_bond.net_dev = bond_support_list[:bond_last_seq]  # 配置bond接口：只使用前两个可用接口
            bond_info = g_api_global.bond__list_set(g_default_cfg_bond)  # 创建链路聚合接口
            bond_name = bond_info['name']  # 提取创建的bond接口名称
            g_default_cfg_vlan.net_dev = bond_name  # 配置VLAN：使用bond接口作为父接口
            g_api_global.vlan__list_set(params=g_default_cfg_vlan)  # 创建基于bond的VLAN子接口
            g_api_global.config_issued_global_get_until_zero()  # 等待配置生效

            # 验证【check1】和【check2】：
            # 检查SSH命令输出中是否包含新创建的VLAN接口
            assert f'{bond_name}.{g_default_cfg_vlan.tag_id}' in get_node_ssh_obj.exec_cmd(cmd='ip address')[1]
