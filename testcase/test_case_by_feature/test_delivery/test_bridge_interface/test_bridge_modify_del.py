"""
模块名称: test_bridge_modify_del.py

该模块的目标：
    测试网桥修改和删除功能
  
作者: ych
修改历史:
    1. 2025/8/13 - 创建文件
"""
import pytest
import allure

from loguru import logger
from testcase.cfg_example.cfg_skip import SkipByCase  # 导入自定义的跳过测试用例类
from testcase.test_case_by_feature.test_delivery.func import check_interface, \
    check_interface_member  # 导入检查函数
from testcase.utils.id_update import node_namespace_update  # 导入节点命名空间更新工具


class TestBridgeModifyDel:  # 网桥修改和删除的测试类
    @pytest.fixture(scope='function')
    def create_bridge(self, g_api_global, g_default_cfg_bridge, g_default_cfg_bond):
        """创建网桥的夹具，用于测试前置准备"""
        query_get = {'type': 'bridge'}  # 查询参数：类型为网桥
        query_get = node_namespace_update(namespace_map_name='namespace_id', param_obj=query_get,
                                          api_obj=g_api_global)  # 更新节点命名空间
        net_dev_list = g_api_global.interface_filter_get(**query_get)['choices']  # 获取接口过滤列表
        g_default_cfg_bridge.desc = 'for test'  # 配置默认网桥描述
        g_default_cfg_bridge.net_dev = net_dev_list[:2]  # 选择前两个网络设备作为网桥成员
        bridge = g_api_global.bridge__list_set(g_default_cfg_bridge)  # 创建网桥
        bond_list = []  # 存储链路聚合口名称的列表
        bond_pk = []  # 存储链路聚合口主键的列表

        # 创建两个链路聚合口
        for item in [net_dev_list[2:4], net_dev_list[4:6]]:
            g_default_cfg_bond.net_dev = item  # 设置链路聚合口的网络设备
            params = g_api_global.bond__list_set(g_default_cfg_bond)  # 创建链路聚合口
            bond_list.append(params['name'])  # 添加链路聚合口名称
            bond_pk.append(params['_pk'])  # 添加链路聚合口主键

        g_api_global.config_issued_global_get_until_zero()  # 等待配置下发完成
        yield {'bridge': bridge, 'net_dev_list': net_dev_list[6:8], 'bond_list': bond_list}  # 返回创建的网桥和网络设备列表

        for pk in bond_pk:
            g_api_global.bond__detail_delete(pk)  # 测试清理：删除创建的链路聚合口

    @allure.title('网络层修改/删除网桥')
    @allure.description('''  # 设置测试用例详细描述
    前置条件：
    1、WAF正常启动。
    2、建立正常的配置连接。
    测试步骤：
    1、修改网桥成员接口，选择其他两个物理口【check1】【check2】
    2、修改网桥成员接口，选择其他两个链路聚合口【check1】【check2】
    3、删除网桥【check2】【check3】
    预期结果：
    【check1】修改网桥成功，界面显示与配置一致
    【check2】linux查看接口ip address一致
    【check3】删除网桥成功，界面显示与配置一致
    ''')
    @pytest.mark.level2  # 标记为二级测试用例
    @SkipByCase.SKIP_NOT_NUMBER_INTERFACE_12  # 接口数量小于12则跳过
    @pytest.mark.transparent  # 标记为透明测试
    def test_bridge_modify_del(self, g_api_global, g_default_cfg_bridge, g_default_cfg_bond, create_bridge):
        """测试网桥修改和删除功能"""
        with allure.step(' 1、修改网桥成员接口，选择其他两个物理口【check1】【check2】'
                         '【check1】修改网桥成功，界面显示与配置一致【check2】linux查看接口ip address一致'):
            # 记录创建的网桥信息
            logger.info(create_bridge)
            # 获取可用的网络设备列表
            net_dev_list = create_bridge['net_dev_list']
            # 获取创建的网桥对象
            bridge = create_bridge['bridge']
            # 设置网桥使用新的网络设备
            g_default_cfg_bridge.net_dev = net_dev_list
            # 更新网桥配置
            g_api_global.bridge__detail_update(pk=bridge['_pk'], params=g_default_cfg_bridge)
            # 等待配置下发完成
            g_api_global.config_issued_global_get_until_zero()
            # 检查接口成员是否更新成功
            check_interface_member(g_api_global, bridge['name'], net_dev_list)

        with allure.step('2、修改网桥成员接口，选择其他两个链路聚合口【check1】【check2】'):
            # 设置网桥使用链路聚合口
            g_default_cfg_bridge.net_dev = create_bridge['bond_list']
            # 等待配置下发完成
            g_api_global.config_issued_global_get_until_zero()
            # 更新网桥配置
            g_api_global.bridge__detail_update(pk=bridge['_pk'], params=g_default_cfg_bridge)
            # 等待配置下发完成
            g_api_global.config_issued_global_get_until_zero()
            # 检查接口成员是否更新成功
            check_interface_member(g_api_global, bridge['name'], g_default_cfg_bridge.net_dev)

        with allure.step('3、删除网桥【check2】【check3】'):
            # 删除网桥
            g_api_global.bridge__detail_delete(pk=bridge['_pk'])
            # 等待配置下发完成
            g_api_global.config_issued_global_get_until_zero()
            # 验证网桥是否成功删除
            assert not check_interface(g_api_global, bridge['name'])
