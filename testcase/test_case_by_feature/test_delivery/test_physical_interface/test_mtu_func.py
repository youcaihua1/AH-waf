"""
模块名称: test_mtu_func.py

该模块的目标：

  
作者: ych
修改历史:
    1. 2025/8/21 - 创建文件
"""
import pytest
import allure
from scapy.all import *  # 导入scapy网络包分析库
from loguru import logger
from common.ip_tools.ip_address import NetToolLocal  # 本地网络工具类
from common.ip_tools.ip_address import NetToolSsh  # 通过SSH操作的网络工具类
from env.config import WafDut  # 导入WAF设备信息
from testcase.cfg_example.cfg_skip import SkipByCase

test_data = {'retry_count': 10,  # 重试次数
             'server_info': WafDut().servers_info[0],  # 服务器信息
             'client_info': WafDut().client_info[0],  # 客户端信息
             'bridge_name': WafDut().client_info[0].get('bridge', 'Protect1'),  # 网桥名称
             'bridge_sub_interface': WafDut().bridge_sub_interface}  # 网桥子接口

# 创建服务器网络对象（通过SSH连接）
server_net_obj = NetToolSsh(ip=test_data['server_info']['ip'],
                            usr=test_data['server_info']['usr'],
                            pwd=test_data['server_info']['pwd'])
# 创建客户端网络对象（通过SSH连接）
client_net_obj = NetToolSsh(ip=test_data['client_info']['ip'],
                            usr=test_data['client_info']['usr'],
                            pwd=test_data['client_info']['pwd'])


class TestMTUFunc:  # 定义MTU功能测试类
    @staticmethod
    def is_fragment(pcap_file):
        """
        静态方法：检查pcap文件中是否有分片包
        :param pcap_file: pcap文件路径
        :return: 如果检测到分片则返回True，否则返回False
        """
        # 读取pcap文件
        packets = rdpcap(f'{pcap_file}')
        # 如果包中没有ICMP流量，则抛出异常
        if 'ICMP' not in str(packets):
            logger.info(str(packets))
            raise Exception('无ICMP流量，请检查脚本运行环境。')
        # 遍历每个包，检查是否有分片标志
        for item in packets:
            logger.info(item)
            if 'icmp frag' in str(item):  # 如果包描述中包含'icmp frag'，说明有分片
                return True
        else:
            return False

    @staticmethod
    def modify_mtu(g_api_global, dev_name, mtu):
        """
        静态方法：修改指定接口的MTU值
        :param g_api_global: 全局API对象
        :param dev_name: 设备名称
        :param mtu: 要设置的MTU值
        """
        try:
            # 通过API获取接口信息
            interface = g_api_global.interface__list_get(search_data={'name': f'{dev_name}'})
            pk = interface['_pk']  # 获取接口的主键
            speed = interface['speed']  # 获取接口的速度
            # 更新接口的MTU值（同时保持速度不变）
            g_api_global.interface__detail_update(pk=pk, params={"speed": f"{speed}", "mtu": f'{mtu}'})
        except BaseException as be:
            logger.info(be)

    def set_all_mtu(self, g_api_global, mtu):
        """
        设置所有相关接口的MTU值（包括网桥子接口、eth0、服务器和客户端的网络接口以及网桥本身）
        :param g_api_global: 全局API对象
        :param mtu: 要设置的MTU值
        """
        # 修改第一个网桥子接口的MTU
        self.modify_mtu(g_api_global, mtu=mtu, dev_name=test_data['bridge_sub_interface'][0])
        # 修改第二个网桥子接口的MTU
        self.modify_mtu(g_api_global, mtu=mtu, dev_name=test_data['bridge_sub_interface'][1])
        # 修改eth0的MTU
        self.modify_mtu(g_api_global, mtu=mtu, dev_name='eth0')
        # 修改服务器网络接口的MTU（通过SSH）
        server_net_obj.modify_mtu(net_dev=test_data['server_info']['net_dev'], mtu=mtu)
        # 修改客户端网络接口的MTU（通过SSH）
        client_net_obj.modify_mtu(net_dev=test_data['client_info']['net_dev'], mtu=mtu)
        # 获取网桥信息并修改其MTU
        bridge = g_api_global.bridge__list_get(search_data={'name': test_data['bridge_name']})
        bridge['mtu'] = mtu
        g_api_global.bridge__detail_update(pk=bridge['_pk'], params=bridge)
        # 下发配置并等待完成
        g_api_global.config_issued_global_get_until_zero()

    @staticmethod
    def send_icmp_and_fetch_message(g_api_global, icmp_length, server_ip):
        """
        静态方法：发送ICMP流量并抓包，返回抓包文件
        :param g_api_global: 全局API对象
        :param icmp_length: ICMP数据包的长度（不包括IP和ICMP头）
        :param server_ip: 目标服务器IP
        :return: 抓包文件的路径
        """
        # 删除所有现有的tcpdump抓包任务
        g_api_global.tcpdumps_delete_all()
        # 设置新的tcpdump抓包任务（抓取指定接口的ICMP包）
        g_api_global.tcpdump_set(data={"tasks": [
            {"protocol": "icmp", "net_dev": f"{WafDut().bridge_sub_interface[1]}", }  # 服务端的子接口
        ]})
        time.sleep(10)  # 等待10秒，确保抓包任务启动
        # 尝试多次发送ping，直到成功或达到重试次数
        for index in range(test_data['retry_count']):
            # 使用本地网络工具发送ping
            res = NetToolLocal().ping(host=server_ip, length=icmp_length, count=10)
            if res['connected']:  # 如果ping通了，跳出循环
                break
            else:
                raise Exception('icmp流量不通')  # 否则抛出异常
        time.sleep(10)  # 等待10秒，确保抓包足够
        # 停止所有抓包任务
        g_api_global.tcpdumps_kill_all()
        # 获取抓包信息
        tcpdump_info = g_api_global.tcpdump__list_get()[0]
        # 如果抓包大小异常，抛出异常
        if tcpdump_info['size'] in [0, 24]:
            raise Exception('未抓取到数据')
        logger.info(">>>>>>>>>>>>>tcpdump_info", tcpdump_info)
        tcpdump_pk = tcpdump_info["_pk"]  # 获取抓包任务的主键
        # 获取抓包文件的下载信息
        tcpdump_info_data = g_api_global.tcpdump_download_get(pk=tcpdump_pk)
        # 下载抓包文件
        resp = g_api_global.download_by_url(resp_url_info=tcpdump_info_data)
        # 将抓包内容写入文件
        with open(f"{tcpdump_pk}.pcap", "wb") as f:
            f.write(resp.content)
        return f'{tcpdump_pk}.pcap'  # 返回抓包文件名

    @pytest.fixture(scope='function')
    def modify_mtu_to_init(self, g_api_global):
        """
        pytest fixture：在每个测试函数运行前后设置和恢复MTU值
        :param g_api_global: 全局API对象
        """
        # 测试前将所有接口的MTU设置为1500（标准值）
        self.set_all_mtu(g_api_global=g_api_global, mtu=1500)
        yield  # 执行测试函数
        # 测试后再次将所有接口的MTU设置为1500（恢复）
        self.set_all_mtu(g_api_global=g_api_global, mtu=1500)

    @allure.title('MTU功能验证')  # allure报告的测试标题
    @allure.description('''  # allure报告的详细描述
        前置条件
            1、WAF正常启动。
            2、建立正常的配置连接。
        用例步骤
            1、配置client、server、网桥子接口、waf管理口的mtu为1280 在client下ping -s 1252 -c 4 xx.xx.xx.xx
            2、配置client、server、网桥子接口、waf管理口的mtu为1280 在client下ping -s 1253 -c 4 xx.xx.xx.xx
            3、配置client、server、网桥子接口、waf管理口的mtu为1518 在client下ping -s 1490 -c 4 xx.xx.xx.xx
            4、配置client、server、网桥子接口、waf管理口的mtu为1518 在client下ping -s 1490 -c 4 xx.xx.xx.xx
        预期结果
            【check1】icmp流量正常  抓包查看icmp包未被拆分
            【check2】icmp流量正常  抓包查看icmp包被拆分
    ''')
    @pytest.mark.smoke  # pytest标记：冒烟测试
    @pytest.mark.level3  # pytest标记：测试级别3
    @SkipByCase.SKIP_NOT_HARDWARE_ENVIRONMENT  # 自定义跳过条件：非硬件环境跳过
    @pytest.mark.transparent  # 自定义标记：透明模式测试
    def test_mtu_func(self, g_api_global, server_ip, g_request_construct_special, modify_mtu_to_init):
        """
        测试MTU功能的主函数
        :param g_api_global: 全局API对象
        :param server_ip: 服务器IP（pytest fixture）
        :param g_request_construct_special: 特殊请求构造对象（用于发送HTTP请求）
        :param modify_mtu_to_init: fixture，用于设置和恢复MTU
        """
        # 步骤1：设置MTU为1280，发送1252字节的ping（预期不分片）
        with allure.step('1、配置client、server、网桥子接口、waf管理口的mtu为1280 在client下ping -s 1252 -c 4 xx.xx.xx.xx'):
            self.set_all_mtu(g_api_global=g_api_global, mtu=1280)  # 设置MTU
            pcap_file = self.send_icmp_and_fetch_message(g_api_global, 1252, server_ip)  # 发送ICMP并抓包
            assert not self.is_fragment(pcap_file=pcap_file)  # 断言没有分片
            # 发送一个HTTP请求（大请求体）并检查响应状态（确保WAF正常工作）
            assert g_request_construct_special.req_recv_exp_res_status(url='/request/body',
                                                                       expect_response_status=200,
                                                                       data='t' * 1520)

        # 步骤2：在MTU1280下发送1253字节的ping（预期分片）
        with allure.step('2、配置client、server、网桥子接口、waf管理口的mtu为1280 在client下ping -s 1253 -c 4 xx.xx.xx.xx'):
            pcap_file = self.send_icmp_and_fetch_message(g_api_global, 1253, server_ip)
            assert self.is_fragment(pcap_file=pcap_file)  # 断言有分片
            # 再次发送HTTP请求验证
            assert g_request_construct_special.req_recv_exp_res_status(url='/request/body',
                                                                       expect_response_status=200,
                                                                       data='t' * 1520)

        # 步骤3：设置MTU为1518，发送1490字节的ping（预期不分片）
        with allure.step('3、配置client、server、网桥子接口、waf管理口的mtu为1518 在client下ping -s 1490 -c 4 xx.xx.xx.xx'):
            self.set_all_mtu(g_api_global=g_api_global, mtu=1518)
            pcap_file = self.send_icmp_and_fetch_message(g_api_global, 1490, server_ip)
            assert not self.is_fragment(pcap_file=pcap_file)
            assert g_request_construct_special.req_recv_exp_res_status(url='/request/body',
                                                                       expect_response_status=200,
                                                                       data='t' * 1520)

        # 步骤4：在MTU1518下发送1491字节的ping（预期分片）
        with allure.step('4、配置client、server、网桥子接口、waf管理口的mtu为1518 在client下ping -s 1490 -c 4 xx.xx.xx.xx'):
            pcap_file = self.send_icmp_and_fetch_message(g_api_global, 1491, server_ip)
            assert self.is_fragment(pcap_file=pcap_file)
            assert g_request_construct_special.req_recv_exp_res_status(url='/request/body',
                                                                       expect_response_status=200,
                                                                       data='t' * 1520)
