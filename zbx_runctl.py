# -*- coding: utf-8 -*-


# Author: AcidGo
# Usage:
#   mode: 执行模式，可选如下：
#       - edit: 修改配置模式，可以对指定配置进行修改。
#       - start: 启动 agent。
#       - restart: 重启 agent。
#       - stop: 停止 agent。
#       - status: 查看 agent 状态。
#       - check: 检查 agent 配置。
#   zbx_cnf_server: 修改 zabbix-agent 关于 Server 的配置。
#   zbx_cnf_activeserver: 修改 zabbix-agent 关于 ServerActive 的配置。
#   zbx_cnf_hostname: 修改 zabbix-agent 关于 Hostname 的配置。
#   zbx_cnf_listenport: 修改 zabbix-agent 关于 ListenPort 的配置。
#   zbx_cnf_logpath: 修改 zabbix-agent 关于 LogFile 的配置。


import platform, sys, os, time
import re
import subprocess


if platform.system().lower == "windows";
    import win32serviceutil
    import shutil


# CONFIG
LOGGING_LEVEL = "DEBUG"

ZBX_WIN_AGENTD_SERVICE_NAME = "Zabbix Agent"
ZBX_WIN_AGENT2_SERVICE_NAME = "Zabbix Agent2"
ZBX_LNX_AGENTD_SERVICE_NAME = "zabbix-agent"
ZBX_LNX_AGENT2_SERVICE_NAME = "zabbix-agent2"

WIN_SERVICE_STATUS_MAPPING = {
    -1: "NO_INSTALL",
    0: "UNKNOWN",
    1: "STOPPED",
    2: "START_PENDING",
    3: "STOP_PENDING",
    4: "RUNNING"
}
LNX_SERVICE_STATUS_MAPPING = {
    -1: "NO_INSTALL",
    0: "UNKNOWN",
    1: "INACTIVE",
    2: "ACTIVE",
    603: "Stopped",
    600: "Running",
    99: "EL6"
}
# EOF CONFIG



def init_logger(level, logfile=None):
    """日志功能初始化。
    如果使用日志文件记录，那么则默认使用 RotatinFileHandler 的大小轮询方式，
    默认每个最大 10 MB，最多保留 5 个。
    Args:
        level: 设定的最低日志级别。
        logfile: 设置日志文件路径，如果不设置则表示将日志输出于标准输出。
    """
    import os
    import sys
    if not logfile:
        logging.basicConfig(
            level = getattr(logging, level.upper()),
            format = "%(asctime)s [%(levelname)s] %(message)s",
            datefmt = "%Y-%m-%d %H:%M:%S"
        )
    else:
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, level.upper()))
        if logfile.lower() == "local":
            logfile = os.path.join(sys.path[0], os.path.basename(os.path.splitext(__file__)[0]) + ".log")
        handler = RotatingFileHandler(logfile, maxBytes=10*1024*1024, backupCount=5)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logging.info("Logger init finished.")

def collect_zabbix_agent():
    """对当前操作系统检查是否存在 Zabbix-Agent，并且判断可用的是 Agentd 还是 Agent2。

    Returns:
        res <int>:
            0: 不存在 Zabbix-Agent。
            1: 存在 agentd。
            2: 存在 agent2。
    """
    os_system = platform.system().lower()
    if os_system == "windows":
        if win_service_status(ZBX_WIN_AGENT2_SERVICE_NAME) != -1:
            return 2
        elif win_service_status(ZBX_WIN_AGENTD_SERVICE_NAME) != -1:
            return 1
        else:
            return 0
    elif os_system == "linux":
        if lnx_service_action("is-enabled", ZBX_LNX_AGENT2_SERVICE_NAME):
            return 2
        elif lnx_service_action("is-enabled", ZBX_LNX_AGENTD_SERVICE_NAME):
            return 1
        else:
            return 0

def lnx_service_action(action, service_name):
    """
    """
    if action not in ("start", "stop", "restart", "status", "enable", "disable", "is-enabled"):
        raise Exception("not support the service action: {!s}".format(action))
    rc = -999
    if get_sysversion() in ("el5", "el6"):
        if action in ("start", "stop", "restart", "status"):
            command_lst = ["service", service_name, action]
            rc = lnx_command_execute(command_lst)
        elif action in ("enable",):
            command_lst = ["chkconfig", service_name, "on"]
            rc = lnx_command_execute(command_lst)
        elif action in ("disable",):
            command_lst = ["chkconfig", service_name, "off"]
            rc = lnx_command_execute(command_lst)
        elif action in ("is-enabled",):
            command_lst = ["chkconfig", service_name]
            rc = lnx_command_execute(command_lst)
        else:
            rc = -999
    elif get_sysversion() in ("el7"):
        command_lst = ["systemctl", action, service_name]
        rc = lnx_command_execute(command_lst)
    else:
        raise Exception("not support the OS now")
    return rc


def win_service_status(service_name):
    """查看 Windows 注册服务的状态信息。

    Args:
        service_name: 待查看的服务名称。
    Returns:
        <int>: 返回状态码，-1 为未注册，其他可见 WIN_SERVICE_STATUS_MAPPING。
    """
    try:
        status_code = win32serviceutil.QueryServiceStatus(service_name)[1]
    except Exception as e:
        if hasattr(e, "winerror") and e.winerror == 1060:
            return -1
        else:
            raise e
    return status_code

def win_service_restart(service_name):
    """
    """
    win32serviceutil.RestartService(service_name)
    time.sleep(3)
    return win_service_status(service_name) in (4,)

def win_service_start(service_name):
    """
    """
    win32serviceutil.StartService(service_name)
    time.sleep(3)
    return win_service_status(service_name) in (4,)

def win_service_stop(service_name):
    """
    """
    win32serviceutil.StopService(service_name)
    time.sleep(3)
    return win_service_status(service_name) in (1,2,3)

def get_sysversion():
    """获取当前操作系统的版本信息。

    Returns:
        <str> "win": 所有 windows 平台。
        <str> "el5": CentOS/RedHat 5。
        <str> "el6": CentOS/RedHat 6。
        <str> "el7": CentOS/RedHat 7。
    """
    if platform.system().lower() == "windows":
        return "win"
    elif platform.system().lower() == "linux":
        res_tmp = subprocess.check_output(["uname", "-r"]).strip()
        res = re.search('el[0-9]', res_tmp).group()
        if res:
            return res
        else:
            logging.error("Cannot get sysversion from [{!s}].".format(res_tmp))
            raise Exception()

def lnx_command_execute(command_lst):
    """在 Linux 平台执行命令。
    Args:
        command_lst: 命令列表，shell 下命令的空格分段形式。
    Returns:
        <bool> False: 执行返回非预期 exitcode。
        <bool> True: 执行返回预期 exitcode。
    """
    logging.info("---------- {!s} ----------".format(command_lst))
    try:
        res = subprocess.check_output(command_lst, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        for i in e.output.split('\n'):
            logging.error(i)
        logging.info("-"*30)
        return False
    for i in [i for i in res.split('\n') if not i.strip()]:
        logging.info(i)
    logging.info("-"*30)
    return True

def multi_service_action(action, service_name):
    """
    """
    os_system = platform.system().lower()
    if os_system in ("windows",):
        if action == "status":
            return win_service_status(service_name)
        elif action == "restart":
            return win_service_restart(service_name)
        elif action == "start":
            return win_service_start(service_name)
        elif action == "stop":
            return win_service_stop(service_name)
        else:
            raise Exception("not supported action {!s} for service {!s} on windows".format(action, service_name))
    elif os_system in ("el5", "el6", "el7"):
        return lnx_service_action(action, service_name)
    else:
        raise Exception("not suported for the os: {!s}".format(os_system))

def get_preferred_ipaddres():
    """选择合适的当期主机内的 IP 地址。
    如果是 easyops 版本，则首先使用 EASYOPS_LOCAL_IP 变量；
    如果是非 easyops 版本，将使用报文协议获取所有IP，然后选择默认网关同网段的IP地址返回。
    Returns:
        <str> ip: 合适的IP地址，可能返回 None。
    """
    if "EASYOPS_LOCAL_IP" in globals() and globals().get("EASYOPS_LOCAL_IP") != "":
        return EASYOPS_LOCAL_IP

    import socket
    import fcntl
    import struct
    from sys import version_info

    def get_ip_address(ifname):
        """
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if version_info.major == 3:
            ifname_ = bytes(ifname[:15], "utf-8")
        else:
            ifname_ = ifname[:15]
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,
            struct.pack('256s', ifname_)
        )[20:24])

    ip_lst = []
    for net in list_all_netcards():
        ip_lst.append(get_ip_address(net))
    if len(ip_lst) == 0:
        return None
    if len(ip_lst) == 2 and '127.0.0.1' in ip_lst:
        return ip_lst[2 - ip_lst.index("127.0.0.1")]
    gateway = get_default_gateway()
    if not gateway:
        return None
    gateway_prefix = '.'.join(gateway.split('.')[0:-1])
    res = None
    for i in ip_lst:
        if i.startswith(gateway_prefix):
            res = i
            break
    return res

def execute(mode, zbx_cnf_activeserver, zbx_cnf_hostname, zbx_cnf_listenport, zbx_cnf_logpath):
    """
    """
    # Pre Checking
    os_system = platform.system().lower()
    # 可行性分析：对目前不支持的操作系统，拒绝执行
    if os_system not in ("linux", "windows"):
        raise Exception("the OS is [{!s}], not supported now".format(os_system))
    # 可行性分析：检查是否安装了 agent
    agent_type = collect_zabbix_agent()
    if agent_type <= 0:
        if mode == "status":
            logging.info("the status is: Noinstall")
            exit(0)
        raise Exception("the agent is not installed")
    # 参数优化：如果 mode 为非编辑，则将配置相关的变量置为 None
    if mode.lower() != "edit":
        zbx_cnf_server = None
        zbx_cnf_activeserver = None
        zbx_cnf_hostname = None
        zbx_cnf_listenport = None
        zbx_cnf_logpath = None
    # 参数检查：如果 mode 为编辑，编辑参数不能为空
    else:
        if not any([zbx_cnf_activeserver, zbx_cnf_hostname, zbx_cnf_listenport, zbx_cnf_logpath]):
            raise Exception("on mode {!s}, your edit params is empty".format(mode))
    # 检查参数：如果编辑参数存在 zbx_cnf_listenport，则必须在 1024 - 32767 之间
    if zbx_cnf_listenport:
        if '.' in str(zbx_cnf_listenport):
            raise Exception("your zbx_cnf_listenport:[{!s}] has '.'".format(zbx_cnf_listenport))
        tmp = int(zbx_cnf_listenport)
        if not 1024 < tmp < 32767:
            raise Exception("your zbx_cnf_listenport:[{!s}] must be between 1024 and 32767".format(zbx_cnf_listenport))
    # 参数优化：对于 zbx_cnf_hostname 如果输入 @@ 符号则表示使用自动检索功能
    if zbx_cnf_hostname == "@@":
        logging.info("your zbx_cnf_hostname choice @@, to be auto")
        zbx_cnf_hostname = get_preferred_ipaddres()
        logging.info("the zbx_cnf_hostname change to [{!s}]".format(zbx_cnf_hostname))
    # EOF Pre Checking

    # 编辑配置的配置映射表
    edit_dict = {
        "Server": zbx_cnf_server,
        "ServerActive": zbx_cnf_activeserver,
        "Hostname": zbx_cnf_hostname,
        "ListenPort": zbx_cnf_listenport,
        "LogFile": zbx_cnf_logpath,
    }

    try:
        if os_system == "windows":
            service_name = ZBX_WIN_AGENT2_SERVICE_NAME if agent_type == 2 else ZBX_WIN_AGENTD_SERVICE_NAME
        else:
            service_name = ZBX_LNX_AGENT2_SERVICE_NAME if agent_type == 2 else ZBX_LNX_AGENTD_SERVICE_NAME
        
        if mode == "start":
            multi_service_action("start", service_name)
        elif mode == "restart":
            multi_service_action("restart", service_name)
        elif mode == "stop":
            multi_service_action("stop", service_name)
    except Exception as e:
        logging.error("it has error, when exec command: ")



