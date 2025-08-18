"""
模块名称: test_bond_delete.py

该模块的目标：
    测试链路聚合的删除
  
作者: ych
修改历史:
    1. 2025/8/14 - 创建文件
"""
import pytest
import allure
from testcase.test_case_by_feature.test_delivery.func import func_adapt, check_interface  # 检查接口
from swagger_client.lib.common import ApiException  # 导入API异常类
from testcase.cfg_example.cfg_skip import SkipByCase
from testcase.utils.id_update import node_namespace_update  # 导入集群命名空间更新工具


class TestBondDelete:
    # 测试数据：IP地址、网关和子网掩码
    test_data = {
        'ip': '159.123.23.89',  # 测试用IP地址
        'gateway': '159.123.23.1',  # 测试用网关
        'mask': 24  # 子网掩码长度
    }

    @allure.title('网络层删除链路聚合')
    @allure.description('''
    前置条件：
    1、WAF正常启动。
    2、建立正常的配置连接。
    3、链路聚合工作模式为负载均衡Round Robin或负载均衡XOR
    测试步骤：
    1、链路聚合下有IP地址，删除链路聚合【check1】
    2、链路聚合下无IP地址，删除链路聚合【check2】
    预期结果：
    【check1】提示接口上存在IP地址
    【check2】删除成功
    ''')
    @pytest.mark.level2
    @SkipByCase.SKIP_NOT_NUMBER_INTERFACE_4  # 接口不足时跳过
    def test_bond_delete(self, reset_network_by_cfg, g_api_global, g_default_cfg_bond,
                         g_default_cfg_ip):
        ip = self.test_data['ip']
        gateway = self.test_data['gateway']
        mask = self.test_data['mask']

        query_get = {'type': 'bond'}  # 指定查询类型为bond
        query_get = node_namespace_update(  # 更新命名空间映射
            namespace_map_name='namespace_id',
            param_obj=query_get,
            api_obj=g_api_global
        )
        net_dev_list = g_api_global.interface_filter_get(**query_get)['choices']  # 获取可用的网络设备列表

        g_default_cfg_bond.net_dev = net_dev_list[-3:-1]  # 配置bond参数：取列表末尾两个网口
        bond_res = g_api_global.bond__list_set(g_default_cfg_bond)  # 创建bond接口
        bond_pk = bond_res['_pk']  # 获取bond的主键ID
        bond_name = bond_res['name']  # 获取bond的名称

        g_default_cfg_ip.net_dev = func_adapt(g_api_global, g_api_global.bond__list_get)[-1]['name']  # 获取最新创建的bond接口名称
        g_default_cfg_ip.ip = ip  # 设置IP地址
        g_default_cfg_ip.gateway = gateway  # 设置网关
        g_default_cfg_ip.mask = mask  # 设置子网掩码
        ip_info = g_api_global.network_ips_set(g_default_cfg_ip)  # 添加IP配置
        ip_pk = ip_info['_pk']  # 获取IP配置的主键ID
        g_api_global.config_issued_global_get_until_zero()  # 等待配置生效（轮询直到返回0）

        with allure.step('1、链路聚合下有IP地址，删除链路聚合【check1】'):
            with pytest.raises(ApiException):  # 预期会抛出ApiException异常（因为有IP地址不能删除）
                g_api_global.bond__detail_delete(bond_pk)  # 尝试删除bond

        with allure.step('2、链路聚合下无IP地址，删除链路聚合【check2】'):
            g_api_global.ip__detail_delete(pk=ip_pk)  # 先删除IP配置
            g_api_global.bond__detail_delete(pk=bond_pk)  # 再删除bond接口
            g_api_global.config_issued_global_get_until_zero()  # 等待配置生效
            assert not check_interface(g_api_global, bond_name)  # 验证bond接口是否已删除
