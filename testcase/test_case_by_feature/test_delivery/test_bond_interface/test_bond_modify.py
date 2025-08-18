"""
模块名称: test_bond_modify.py

该模块的目标：
    测试链路聚合的修改
  
作者: ych
修改历史:
    1. 2025/8/14 - 创建文件
"""
import pytest
import allure

from testcase.cfg_example.cfg_skip import SkipByCase
from testcase.test_case_by_feature.test_delivery.func import func_adapt, get_interface_name_list, check_interface_member
from testcase.utils.id_update import node_namespace_update  # 导入集群命名空间更新工具


class TestBondModify:
    test_data = {
        'desc': 'for test &asd12测试test'  # 测试用的描述信息（含特殊字符和中文）
    }

    @allure.title('网络层修改链路聚合')
    @allure.description('''
    前置条件：
    1、WAF正常启动。
    2、建立正常的配置连接。
    3、链路聚合工作模式为负载均衡Round Robin或负载均衡XOR
    测试步骤：
    1、修改链路聚合成员口【check1】
    预期结果：
    【check1】修改成功，链路聚合成员口显示与配置一致，状态正常
    ''')
    @pytest.mark.level2
    @SkipByCase.SKIP_NOT_NUMBER_INTERFACE_4
    def test_bond_modify(self, g_api_global, g_default_cfg_bond, reset_network_by_cfg):
        query_get = {'type': 'bond'}  # 指定查询类型为bond
        query_get = node_namespace_update(  # 更新命名空间映射（集群环境专用）
            namespace_map_name='namespace_id',
            param_obj=query_get,
            api_obj=g_api_global
        )
        net_dev_list = g_api_global.interface_filter_get(**query_get)['choices']  # 获取可用的网络设备列表（bond成员口候选）

        g_default_cfg_bond.net_dev = net_dev_list[-3:-1]  # 配置bond参数：取列表末尾两个网口
        bond_info = g_api_global.bond__list_set(g_default_cfg_bond)  # 创建bond接口
        bond_pk = bond_info['_pk']  # 获取bond的主键ID

        with allure.step('1、修改链路聚合成员口【check1】'):
            desc = self.test_data['desc']  # 从测试数据中获取描述信息
            g_default_cfg_bond.desc = desc  # 更新bond的描述信息
            g_default_cfg_bond.net_dev = net_dev_list[0:2]  # 修改bond的成员口为前两个网口
            g_api_global.bond__detail_update(pk=bond_pk, params=g_default_cfg_bond)  # 更新bond配置
            g_api_global.config_issued_global_get_until_zero()  # 等待配置生效

            bond_info = g_api_global.bond__detail_get(pk=bond_pk)  # 获取更新后的bond信息
            assert bond_info['desc'] == desc  # 验证描述信息是否更新成功
            assert bond_info['net_dev'] == net_dev_list[0:2]  # 验证成员口是否更新成功

            bond_name = bond_info['name']  # 获取bond的名称
            assert check_interface_member(g_api_global, bond_name, net_dev_list[0:2])  # 验证成员口状态是否正常
