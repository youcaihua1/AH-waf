"""
模块名称: test_bond_create.py

该模块的目标：
    测试链路聚合的创建
  
作者: ych
修改历史:
    1. 2025/8/14 - 创建文件
"""
import pytest
import allure

from testcase.test_case_by_feature.test_delivery.func import check_interface_member, check_interface  # 检查接口函数
from testcase.cfg_example.cfg_api import SkipByCase
from testcase.utils.id_update import node_namespace_update  # 集群命名空间更新工具函数


class TestBondCreate:
    @allure.title('网络层创建链路聚合')
    @allure.description('''
    前置条件：
    1、WAF正常启动。
    2、建立正常的配置连接。
    3、链路聚合工作模式为负载均衡Round Robin或负载均衡XOR
    测试步骤：
    1、链路聚合成员口选择2个或多个，创建链路聚合【check1】
    预期结果：
    【check1】创建成功，链路聚合成员口显示与配置一致，状态正常
    ''')
    @pytest.mark.level2
    @SkipByCase.SKIP_NOT_NUMBER_INTERFACE_4  # 接口数必须大于4
    def test_bond_create(self, g_api_global, g_default_cfg_bond, reset_network_by_cfg):
        with allure.step('1、链路聚合成员口选择2个或多个，创建链路聚合【check1】'):
            query_get = {'type': 'bond'}  # 类型为bond

            # 集群环境适配：更新命名空间映射
            query_get = node_namespace_update(
                namespace_map_name='namespace_id',  # 集群命名空间映射字段
                param_obj=query_get,  # 需要更新的参数对象
                api_obj=g_api_global  # API访问对象
            )

            net_dev_list = g_api_global.interface_filter_get(**query_get)['choices']  # 获取可用的网络设备列表（bond成员口候选）

            with allure.step('成员口为2个时'):
                g_default_cfg_bond.net_dev = net_dev_list[-3:-1]  # 配置bond参数：取列表末尾两个网口（索引-3到-1）

                cfg = g_api_global.bond__list_set(g_default_cfg_bond)  # 调用API创建bond并返回配置信息

                g_api_global.config_issued_global_get_until_zero()  # 等待全局配置生效（轮询直到返回0）

                # 验证：1.bond接口存在且状态正常 2.成员口与配置一致
                assert check_interface(g_api_global, cfg['name']) \
                       and check_interface_member(g_api_global, cfg['name'], net_dev_list[-3:-1])

            g_api_global.bond__detail_delete(pk=cfg['_pk'])  # 清理：删除创建的bond

            with allure.step('成员口为多个时'):
                g_api_global.config_issued_global_get_until_zero()  # 确保配置状态归零（准备环境）

                g_default_cfg_bond.net_dev = net_dev_list  # 配置bond参数：使用所有可用网口

                cfg = g_api_global.bond__list_set(g_default_cfg_bond)  # 创建新的bond

                g_api_global.config_issued_global_get_until_zero()  # 等待配置生效

                # 验证bond状态和成员口
                assert check_interface(g_api_global, cfg['name']) \
                       and check_interface_member(g_api_global, cfg['name'], net_dev_list)

            g_api_global.bond__detail_delete(pk=cfg['_pk'])  # 清理：删除创建的bond
