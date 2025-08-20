"""
模块名称: test_vlan_delete.py

该模块的目标：
    测试VLAN删除功能
  
作者: ych
修改历史:
    1. 2025/8/20 - 创建文件
"""
import pytest
import allure
from env.config import WafDut
from swagger_client.lib.common import ApiException
from testcase.cfg_example.cfg_skip import SkipByCase
from testcase.utils.id_update import node_namespace_update


class TestVLANDelete:

    @staticmethod
    def create_vlan_interface(g_api_global, g_default_cfg_vlan):  # 创建多个VLAN接口
        query_get = {'type': 'vlan'}  # 准备查询参数
        query_get = node_namespace_update(
            namespace_map_name='namespace_id',
            param_obj=query_get,
            api_obj=g_api_global)  # 更新命名空间参数
        dev_name_list = g_api_global.interface_filter_get(**query_get)['choices']  # 获取符合条件的接口设备列表
        if len(dev_name_list) < 1:
            pytest.skip('当前接口数量不足以支持本用例执行 请检查运行环境')
        g_default_cfg_vlan.net_dev = dev_name_list[0]  # 使用第一个可用接口作为VLAN基础设备
        for index in range(5):
            g_default_cfg_vlan.tag_id = index + 1  # 设置不同的VLAN标签ID
            g_api_global.vlan__list_set(params=g_default_cfg_vlan)  # 调用API创建VLAN接口

        name_list = []  # 用于存储创建的VLAN信息
        # 根据设备类型(中心机或单机)获取VLAN列表
        if WafDut().run_type == 'central':  # 中心机
            namespace_id = g_api_global.node__list_get()[0]['namespace_id']  # 获取第一个节点的命名空间ID
            for item in g_api_global.vlan__list_get(namespace_id=namespace_id):  # 获取该命名空间下的VLAN列表
                name_list.append({'pk': item['_pk'], 'name': item['name']})
        else:  # 单机模式
            for item in g_api_global.vlan__list_get():
                name_list.append({'pk': item['_pk'], 'name': item['name']})
        return name_list  # 返回创建的VLAN信息列表

    @staticmethod
    def create_ip_in_vlan_interface(g_api_global, g_default_cfg_ip, name, ip, geteway):  # 在指定VLAN接口上配置IP地址
        g_default_cfg_ip.net_dev = name  # 设置网络设备名
        g_default_cfg_ip.ip = ip  # 设置IP地址
        g_default_cfg_ip.geteway = geteway  # 设置网关地址
        g_default_cfg_ip.mask = 24  # 设置子网掩码(/24)
        g_api_global.network_ips_set(g_default_cfg_ip)  # 调用API配置IP地址

    @allure.title('网络层删除VLAN')
    @allure.description('''  # allure报告的详细描述
        预置条件
            1、WAF正常启动。
            2、建立正常的配置连接。
        测试步骤
            1、VLAN下无IP地址，删除VLAN【check1】【check2】
            2、VLAN下有IP地址，删除VLAN【check3】
        预期结果
            【check1】删除成功
            【check2】linux查看接口ip address一致
            【check3】提示接口上存在IP地址
    ''')
    @pytest.mark.level4
    @SkipByCase.SKIP_NOT_NUMBER_INTERFACE_4
    def test_vlan_delete(self, g_api_global, g_default_cfg_vlan, g_default_cfg_ip, reset_network_by_cfg,
                         get_node_ssh_obj):
        ssh_connection = get_node_ssh_obj  # 获取SSH连接对象
        name_list = self.create_vlan_interface(g_api_global, g_default_cfg_vlan)  # 创建5个VLAN接口并获取它们的详细信息
        with allure.step('1、VLAN下无IP地址，删除VLAN【check1】【check2】'):
            g_api_global.vlan__detail_delete(name_list[0]['pk'])  # 删除第一个VLAN接口
            g_api_global.config_issued_global_get_until_zero()  # 等待配置下发完成
            assert name_list[0]['name'] not in ssh_connection.exec_cmd(cmd='ip address')[1]

        with allure.step('2、VLAN下有IP地址，删除VLAN【check3】'):
            self.create_ip_in_vlan_interface(  # 在第二个VLAN接口上配置IP地址
                g_api_global=g_api_global,
                g_default_cfg_ip=g_default_cfg_ip,
                name=name_list[1]['name'],
                ip='1.1.1.2',
                geteway='1.1.1.1'
            )

            with pytest.raises(ApiException):  # 尝试删除带有IP地址的VLAN，预期会抛出异常
                g_api_global.vlan__detail_delete(name_list[1]['pk'])

            query_get = {'dev_name': name_list[1]['name']}
            query_get = node_namespace_update(
                namespace_map_name='namespace_id',
                param_obj=query_get,
                api_obj=g_api_global
            )
            g_api_global.network_ips_delete_by_dev(**query_get)  # 删除接口上的IP配置
