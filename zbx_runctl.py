# -*- coding: utf-8 -*-


# Author: AcidGo
# Usage:
#   mode: ִ��ģʽ����ѡ���£�
#       - edit: �޸�����ģʽ�����Զ�ָ�����ý����޸ġ�
#       - start: ���� agent��
#       - restart: ���� agent��
#       - stop: ֹͣ agent��
#       - status: �鿴 agent ״̬��
#       - check: ��� agent ���á�
#   zbx_cnf_server: �޸� zabbix-agent ���� Server �����á�
#   zbx_cnf_activeserver: �޸� zabbix-agent ���� ServerActive �����á�
#   zbx_cnf_hostname: �޸� zabbix-agent ���� Hostname �����á�
#   zbx_cnf_listenport: �޸� zabbix-agent ���� ListenPort �����á�
#   zbx_cnf_logpath: �޸� zabbix-agent ���� LogFile �����á�
#   zbx_cnf_userparameter: �޸� zabbix-agent ���� UserParameter �����á�


import platform, sys, os, time
import subprocess
import re

if platform.system().lower() == "windows":
    import win32serviceutil
    import shutil


# ########## CONFIG
LOGGING_LEVEL = "DEBUG"
USE_ACCODE = False
WIN_ZBX_AGENT_DES = "C:\\zabbix_agent"
WIN_ZBX_CONF_PATH = "C:\\zabbix_agent\\zabbix_agentd.win.conf"
WIN_ZBX_SERVICE_NAME = "Zabbix Agent"
LNX_ZBX_CONF_PATH = "/etc/zabbix/zabbix_agentd.conf"
LNX_ZBX_SERVICE_NAME = "zabbix-agent"

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
# ########## EOF CONFIG


class ACLogger(object):
    """�Զ�������� logging ���ܵ���Ϣ�����ࡣ
    ���� Easyops �еĻ����ǿ�������ҳ����ʾ����˿��Բ�ʹ�� logging ģ�飬��������롢logging ���̸߳��š�Logger ���ŵȡ�
    """
    NOTSET = 0
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    def __init__(self, level):
        self.setlevel(level)
        self.addtime = False
    def setlevel(self, level):
        if isinstance(level, str):
            level = {"NOTSET": self.NOTSET,
                "DEBUG": self.DEBUG,
                "INFO": self.INFO,
                "WARNING": self.WARNING,
                "ERROR": self.ERROR,
                "CRITICAL": self.CRITICAL
            }[level]
        self.level = level
    def enabletime(self, isenable):
        if isenable is True:
            self.addtime = True
            from datetime import datetime
            self.datetime = datetime
        else:
            self.addtime = False
    def _print(self, prefix, msg):
        if not prefix:
            return 
        if not isinstance(msg, (str,)):
            try:
                resstr = str(msg)
            except Exception as e:
                return 
        if self.addtime:
            prefix = self.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]") + "-" + prefix
        print(prefix + " " + msg)
    def debug(self, msg):
        if self.level > self.DEBUG:
            return 
        prefix = "[DEBUG]"
        self._print(prefix, msg)
    def info(self, msg):
        if self.level > self.INFO:
            return 
        prefix = "[INFO]"
        self._print(prefix, msg)
    def warning(self, msg):
        if self.level > self.WARNING:
            return 
        prefix = "[WARN]"
        self._print(prefix, msg)
    def error(self, msg):
        if self.level > self.ERROR:
            return 
        prefix = "[ERROR]"
        self._print(prefix, msg)
    def critial(self, msg):
        if self.level > self.CRITICAL:
            return 
        prefix = "[CRITICAL]"
        self._print(prefix, msg)


def zbx_runctl(mode, zbx_cnf_server, zbx_cnf_activeserver, zbx_cnf_hostname, zbx_cnf_listenport, zbx_cnf_logpath, zbx_cnf_userparameter):
    """�� zabbix-agent �������п����������޸ġ�
    """
    in_args = set([i for i in locals()])
    args_info = "Input args: " + ", ".join(["{!s}:[{!s}]".format(i, j) for i, j in locals().items() if i in in_args])
    logging.info(args_info + ".")
    logging.info("Start check.")
    # Ԥ���
    tmp_res = precheck_zbx_runctl(mode, zbx_cnf_server, zbx_cnf_activeserver, zbx_cnf_hostname, zbx_cnf_listenport, zbx_cnf_logpath, zbx_cnf_userparameter)
    if not tmp_res:
        logging.error("The check is not pass.EXIT.")
        raise Exception("Check Error.")
    else:
        mode =tmp_res[0]
        zbx_cnf_server = tmp_res[1]
        zbx_cnf_activeserver = tmp_res[2]
        zbx_cnf_hostname = tmp_res[3]
        zbx_cnf_listenport = tmp_res[4]
        zbx_cnf_logpath = tmp_res[5]
        zbx_cnf_userparameter = tmp_res[6]
    tmp_out = {}
    for j in [i for i in locals() if i in in_args]:
        tmp_out[j] = locals().get(j)
    logging.info("After check, the args change to: " + ", ".join(["{!s}:[{!s}]".format(i, j) for i, j in tmp_out.items()]) + ".")

    # �༭���õ�����ӳ���
    edit_dict = {
        "Server": zbx_cnf_server,
        "ServerActive": zbx_cnf_activeserver,
        "Hostname": zbx_cnf_hostname,
        "ListenPort": zbx_cnf_listenport,
        "LogFile": zbx_cnf_logpath,
        "UserParameter": zbx_cnf_userparameter
    }

    iserror = False
    try:
        if mode == "start":
            if platform.system().lower() == "windows":
                zbx_start_win()
            if platform.system().lower() == "linux":
                zbx_start_lnx()
        elif mode == "restart":
            if platform.system().lower() == "windows":
                zbx_restart_win()
            if platform.system().lower() == "linux":
                zbx_restart_lnx()
        elif mode == "stop":
            if platform.system().lower() == "windows":
                zbx_stop_win()
            if platform.system().lower() == "linux":
                zbx_stop_lnx()

    except Exception as e:
        iserror = True
        logging.error("It has erro, when exec command, it is: \n{0!s}".format(e))

    if mode in ("start", "restart", "stop", "status"):
        if mode != "status":
            time.sleep(4)
        if platform.system().lower() == "windows":
            logging.info("The status is : \n{0!s}".format(WIN_SERVICE_STATUS_MAPPING[win_status_service(WIN_ZBX_SERVICE_NAME)]))
        if platform.system().lower() == "linux":
            logging.info("The status is : \n{0!s}".format(LNX_SERVICE_STATUS_MAPPING[lnx_status_servcie(LNX_ZBX_SERVICE_NAME)]))
        if iserror is True:
            exit(1)
    if mode == "check":
        if platform.system().lower() == "windows":
            config_path = WIN_ZBX_CONF_PATH
        if platform.system().lower() == "linux":
            config_path = LNX_ZBX_CONF_PATH
        zbx_config_check(config_path)
    elif mode == "edit":
        if platform.system().lower() == "windows":
            config_path = WIN_ZBX_CONF_PATH
            zbx_config_edit(config_path, edit_dict)
            logging.info("Begin restart zabbix-agent.")
            zbx_restart_win()
        if platform.system().lower() == "linux":
            config_path = LNX_ZBX_CONF_PATH
            zbx_config_edit(config_path, edit_dict)
            logging.info("Begin restart zabbix-agent.")
            zbx_restart_lnx()


def precheck_zbx_runctl(mode, zbx_cnf_server, zbx_cnf_activeserver, zbx_cnf_hostname, zbx_cnf_listenport, zbx_cnf_logpath, zbx_cnf_userparameter):
    """Ԥ��� zbx_runctl ִ�в�����
    """
    # �����Է���: ��Ŀǰ��֧�ֵĲ���ϵͳ���ܾ�ִ��
    if platform.system().lower() not in ("linux", "windows"):
        logging.error("Current OS is [{!s}].".format(platform.system().lower()))
        return False
    # �����Է���: ����Ƿ�װ agent
    if platform.system().lower() == "windows":
        if win_status_service(WIN_ZBX_SERVICE_NAME) == -1:
            if mode == "status":
                logging.info("The status is : \nNoinstall")
                exit(0)
            logging.error("On windows, the agent is not installed.")
            return False
    elif platform.system().lower() == "linux":
        if lnx_status_servcie(LNX_ZBX_SERVICE_NAME) == -1:
            if mode == "status":
                logging.info("The status is : \nNoinstall")
                exit(0)
            logging.error("On linux, the agent is not installed.")
            return False
    # �����Ż�: ��� mode Ϊ�Ǳ༭����������صı�����Ϊ None
    if mode.lower() != "edit":
        zbx_cnf_server = None
        zbx_cnf_activeserver = None
        zbx_cnf_hostname = None
        zbx_cnf_listenport = None
        zbx_cnf_logpath = None
    # �������: ��� mode Ϊ�༭���༭��������Ϊ��
    else:
        if not any([zbx_cnf_server, zbx_cnf_activeserver, zbx_cnf_hostname, zbx_cnf_listenport, zbx_cnf_logpath, zbx_cnf_userparameter]):
            logging.error("On mode:[{!s}], your zbx_cnf_* is emtpy all.".format(mode))
            return False
    # �������: ������� zbx_cnf_listenport�������Ϊ 1024 - 32767 ֮��
    if zbx_cnf_listenport:
        try:
            if '.' in str(zbx_cnf_listenport):
                logging.error("Your zbx_cnf_listenport:[{!s}] has '.'.".format(zbx_cnf_listenport))
                return False
            tmp = int(zbx_cnf_listenport)
            if not 1024 < tmp < 32767:
                logging.error("Your zbx_cnf_listenport:[{!s}] must be between 1024 and 32767.".format(zbx_cnf_listenport))
                return False
        except Exception as e:
            logging.error("Check zbx_cnf_listenport:[{!s}] is failed.".format(zbx_cnf_listenport))
            return False
    # �����Ż�: ���� zbx_cnf_hostname ������� @@ �������ʾʹ���Զ���������
    if zbx_cnf_hostname == "@@":
        logging.info("Your zbx_cnf_hostname choice @@, to be auto.")
        zbx_cnf_hostname = get_preferred_ipaddres()
        logging.info("The zbx_cnf_hostname change to [{!s}].".format(zbx_cnf_hostname))
    # �����Ż�: zbx_cnf_userparameter �����и�
    res_zbx_cnf_userparameter = [i.strip() for i in zbx_cnf_userparameter.split('\n')]
    # �����Ż�: zbx_cnf_userparameter �����е� key �������ظ�
    tmp_set = set()
    for i in res_zbx_cnf_userparameter:
        key_ = i.split(',')[0].strip()
        if key_ in tmp_set:
            logging.error("In UserParameter, it has same key:[{!s}].".format(key_))
            return False
        else:
            tmp_set.add(key_)
    return mode, zbx_cnf_server, zbx_cnf_activeserver, zbx_cnf_hostname, zbx_cnf_listenport, zbx_cnf_logpath, res_zbx_cnf_userparameter


def win_status_service(service_name):
    """�鿴 Windows ע������״̬��Ϣ��

    Args:
        service_name: �鿴�ķ�������
    Returns:
        <int>: �����룬-1 Ϊδע�ᣬ�����ɼ� WIN_SERVICE_STATUS_MAPPING��
    """
    try:
        status_code = win32serviceutil.QueryServiceStatus(service_name)[1]
    except Exception as e:
        # ����δע��
        if hasattr(e, "winerror") and e.winerror == 1060:
            return -1
        else:
            raise e
    return status_code


def lnx_status_servcie(service_name):
    """�鿴 Linux �з���İ�װ�����

    Args:
        service_name: �鿴�ķ�������
    Returns:
        <int> -1: δ��װ��
        <int> != -1: ���������
    """
    if get_sysversion() == "el7":
        command_lst = ["systemctl", "status", service_name]
        try:
            subprocess.check_output(command_lst)
        except subprocess.CalledProcessError as e:
            if e.returncode == 4:
                return -1
            elif e.returncode == 3:
                return 1
            else:
                return 0
        else:
            return 2
    else:
        try:
            command_lst = ["service", service_name, "status"]
            subprocess.check_output(command_lst)
        except subprocess.CalledProcessError as e:
            if e.returncode == 1:
                return -1
            elif e.returncode == 3:
                return 603
            else:
                return 99
        else:
            return 600


def zbx_restart_win():
    """�� Windows ������ zabbix-agent ����
    """
    win32serviceutil.RestartService(WIN_ZBX_SERVICE_NAME)
    time.sleep(3)
    return win_status_service(WIN_ZBX_SERVICE_NAME)


def zbx_start_win():
    """�� Windows ������ zabbix-agent ����
    """
    win32serviceutil.StartService(WIN_ZBX_SERVICE_NAME)
    time.sleep(3)
    return win_status_service(WIN_ZBX_SERVICE_NAME)


def zbx_stop_win():
    """�� Windows ������ zabbix-agent ����
    """
    win32serviceutil.StopService(WIN_ZBX_SERVICE_NAME)
    time.sleep(3)
    return win_status_service(WIN_ZBX_SERVICE_NAME)


def zbx_restart_lnx():
    """�� Linux(CentOS/RedHat) ������ zabbix-agent ����
    """
    if get_sysversion() == "el7":
        command_lst = ["systemctl", "restart", LNX_ZBX_SERVICE_NAME]
    else:
        command_lst = ["service", LNX_ZBX_SERVICE_NAME, "restart"]
    lnx_command_execute(command_lst)


def zbx_start_lnx():
    """�� Linux(CentOS/RedHat) ������ zabbix-agent ����
    """
    if get_sysversion() == "el7":
        command_lst = ["systemctl", "start", LNX_ZBX_SERVICE_NAME]
    else:
        command_lst = ["service", LNX_ZBX_SERVICE_NAME, "start"]
    lnx_command_execute(command_lst)


def zbx_stop_lnx():
    """�� Linux(CentOS/RedHat) ������ zabbix-agent ����
    """
    if get_sysversion() == "el7":
        command_lst = ["systemctl", "stop", LNX_ZBX_SERVICE_NAME]
    else:
        command_lst = ["service", LNX_ZBX_SERVICE_NAME, "stop"]
    lnx_command_execute(command_lst)


def zbx_config_check(config_path):
    """��� zabbix-agent ������Ϣ��

    Args:
        config_path: �����ļ�·����
    """
    import re
    if not os.path.isfile(config_path):
        logging.error("The config:[{!s}] is not a file not not exists.".format(config_path))
        raise Exception()
    if not os.access(config_path, os.W_OK):
        logging.error("The config:[{!s}] is not allow to write.".format(config_path))
        raise Exception()
    conf_lst = []
    with open(config_path, "r") as f:
        for line in f:
            if re.search(r"^ *#", line) or re.search(r"^ *$", line):
                continue
            conf_lst.append(line.strip())
    out_str = "Check the conf:[{!s}] is:\n".format(config_path)
    out_str += "\n".join(conf_lst)
    logging.info(out_str)


def zbx_config_edit(config_path, config_dict):
    """�޸� zabbix-agent �����ļ��Ĳ�����

    Args:
        config_path: ��Ҫ�޸ĵ� zabbix-agent �������ļ�·����
        config_dict: ��Ҫ�޸ĵĲ������ݡ�
    """
    import re
    if len(filter(lambda x: config_dict.get(x, '') in ('', []), config_dict)) == len(config_dict):
        logging.info("No config to edit.")
        with open(config_path, "r") as f:
            for line in f:
                for i in config_dict:
                    tmp = re.search(r"^{!s} *= *(.*?)$".format(i), line)
                    if not tmp:
                        continue
                    else:
                        logging.info("Now config: {!s}.".format(line.strip()))
                        break
        return 
    if not os.path.isfile(config_path):
        logging.error("The config:[{!s}] is not a file not not exists.".format(config_path))
        raise Exception()
    if not os.access(config_path, os.W_OK):
        logging.error("The config:[{!s}] is not allow to write.".format(config_path))
        raise Exception()
    logging.info("Begin to chagne config.")
    conf_lst = []
    old_config_dict = {}
    if config_dict.get("UserParameter", None):
        userparameter_append = [i for i in config_dict["UserParameter"]]
        userparameter_change = []
        old_config_dict["UserParameter"] = []
    with open(config_path, "r") as f:
        for line in f:
            for i in config_dict:
                if not config_dict[i]:
                    continue
                tmp = re.search(r"^{!s} *= *(.*?)$".format(i), line)
                if not tmp:
                    continue
                else:
                    if i == "UserParameter":
                        # ��� config_dict["UserParameter"] �е�����Ԫ��Ϊ�գ��������ϲ� for
                        for ii_1 in config_dict[i]:
                            if ii_1.strip() != "":
                                break
                        else:
                            continue
                        cnf_userparameter_key = "".join(line.strip().split('=')[1:]).split(',')[0].strip()
                        for j_value in config_dict[i]:
                            if cnf_userparameter_key == j_value.strip().split(',')[0].strip():
                                logging.debug("Catch userparameter_key:[{!s}].".format(cnf_userparameter_key))
                                logging.debug("It is [{!s}].".format(line.strip()))
                                # ��� UserParameter �Ǵ��� DEL ���ŵģ�����Ҫɾ��
                                if j_value.strip().split(',')[-1].strip() == "DEL":
                                    logging.debug("For the userparameter_key:[{!s}], DEL it.".format(cnf_userparameter_key))
                                    userparameter_append.remove(j_value)
                                    line = "@@"
                                    break
                                else:
                                    old_line = line
                                    line = re.sub(r"^{!s} *= *(.*?)$".format(i), "{!s}={!s}".format(i, j_value), line)
                                    old_config_dict[i].append(tmp.group(1))
                                    userparameter_change.append((old_line.strip(), j_value.strip()))
                                    userparameter_append.remove(j_value)
                                    break
                    else:
                        old_config_dict[i] = tmp.group(1)
                        line = re.sub(r"^{!s} *= *(.*?)$".format(i), "{!s}={!s}".format(i, config_dict[i]), line)
                    break
            if line != "@@":
                conf_lst.append(line)
            else:
                logging.debug("Get the special symbol:[{!s}].".format(line.strip()))
    hassplit = 0 if conf_lst[-1].endswith(os.linesep) else 1
    # ĳЩ���ܴ�����һ��δƥ��õ����޸����ã����ｲ׷����β��
    for i in config_dict:
        if i == "UserParameter":
            if len(filter(lambda x: x.strip() != "", userparameter_append)) > 0:
                for j in userparameter_append:
                    if j.strip().split(',')[-1].strip() == "DEL":
                        continue
                    conf_lst.append("{!s}={!s}".format(os.linesep*hassplit + i, str(j) + os.linesep))
                    userparameter_change.append(('', "UserParameter={!s}".format(j.strip())))
        elif i not in old_config_dict and config_dict[i]:
            conf_lst.append("{!s}={!s}".format(os.linesep*hassplit + i, str(config_dict[i]) + os.linesep))
            old_config_dict[i] = ""
    with open(config_path, "w") as f:
        for line in conf_lst:
            f.write(line)
    for i in old_config_dict:
        if i != "UserParameter":
            logging.info("Change {!s}={!s} -> {!s}".format(i, old_config_dict[i], config_dict[i]))
        else:
            for j in userparameter_change:
                logging.info("Change {!s} -> {!s}".format(j[0], j[1]))


def get_preferred_ipaddres():
    """ѡ����ʵĵ��������ڵ� IP ��ַ��
    ����� easyops �汾��������ʹ�� EASYOPS_LOCAL_IP ������
    ����Ƿ� easyops �汾����ʹ�ñ���Э���ȡ����IP��Ȼ��ѡ��Ĭ������ͬ���ε�IP��ַ���ء�

    Returns:
        <str> ip: ���ʵ�IP��ַ�����ܷ��� None��
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


def list_all_netcards():
    """��ȡ��ǰϵͳ�����пɼ�������

    Returns:
        <list> netcards_lst: �������ϡ�
    """
    import psutil
    if hasattr(psutil, "net_if_addrs"):
        addrs = psutil.net_if_addrs()
        return addrs.keys()
    else:
        import socket
        import fcntl
        import struct
        import array
        max_possible = 128
        bytes = max_possible * 32
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        names = array.array('B', '\0' * bytes)
        outbytes = struct.unpack("iL", fcntl.ioctl(
            s.fileno(),
            0x8912,
            struct.pack("iL", bytes, names.buffer_info()[0])
        ))[0]
        name_str = names.tostring()
        lst = []
        for i in range(0, outbytes, 40):
            name = name_str[i:i+16].split('\0', 1)[0]
            lst.append(name)
        return lst


def get_default_gateway():
    """��ȡ��ǰ��Ĭ�����ء�
    """
    res = None
    if platform.system().lower() == "linux":
        res_tmp = subprocess.check_output(["ip", "-4", "route"]).strip().split(os.linesep)
        for i in res_tmp:
            if "default" in i:
                res = i.split()[2].strip()
    elif platform.system().lower() == "windows":
        logging.error("get_default_gateway not in windows.")
        pass
    return res


def get_sysversion():
    """��ȡ��ǰ����ϵͳ�İ汾��Ϣ��

    Returns:
        <str> " ": ���� windows ƽ̨��
        <str> "el5": CentOS/RedHat 5��
        <str> "el6": CentOS/RedHat 6��
        <str> "el7": CentOS/RedHat 7��
    """
    if platform.system().lower() == "windows":
        return " "
    elif platform.system().lower() == "linux":
        res_tmp = subprocess.check_output(["uname", "-r"]).strip()
        res = re.search('el[0-9]', res_tmp).group()
        if res:
            return res
        else:
            logging.error("Cannot get sysversion from [{!s}].".format(res_tmp))
            raise Exception()


def lnx_command_execute(command_lst):
    """�� Linux ƽִ̨�����

    Args:
        command_lst: �����б�shell ������Ŀո�ֶ���ʽ��
    Returns:
        <bool> False: ִ�з��ط�Ԥ�� exitcode��
        <bool> True: ִ�з���Ԥ�� exitcode��
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


if __name__ == "__main__":
    logging = ACLogger(LOGGING_LEVEL)
    logging.enabletime(True)
    # ########## Self Test
    # INPUT_MODE = "edit"
    # INPUT_ZBX_CNF_SERVER = "10.10.24.30"
    # INPUT_ZBX_CNF_ACTIVESERVER = ""
    # INPUT_ZBX_CNF_HOSTNAME = ""
    # INPUT_ZBX_CNF_LISTENPORT = "" 
    # INPUT_ZBX_CNF_LOGPATH = ""
    # zbx_runctl(
          # mode = INPUT_MODE, 
          # zbx_cnf_server = INPUT_ZBX_CNF_SERVER, 
          # zbx_cnf_activeserver = INPUT_ZBX_CNF_ACTIVESERVER, 
          # zbx_cnf_hostname = INPUT_ZBX_CNF_HOSTNAME, 
          # zbx_cnf_listenport = INPUT_ZBX_CNF_LISTENPORT, 
          # zbx_cnf_logpath = INPUT_ZBX_CNF_LOGPATH,
          # zbx_cnf_userparameter = INPUT_ZBX_CNF_USERPARAMETER
        # )
    # ########## EOF Self Test


    try:
        zbx_runctl(
          mode = INPUT_MODE, 
          zbx_cnf_server = INPUT_ZBX_CNF_SERVER, 
          zbx_cnf_activeserver = INPUT_ZBX_CNF_ACTIVESERVER, 
          zbx_cnf_hostname = INPUT_ZBX_CNF_HOSTNAME, 
          zbx_cnf_listenport = INPUT_ZBX_CNF_LISTENPORT, 
          zbx_cnf_logpath = INPUT_ZBX_CNF_LOGPATH,
          zbx_cnf_userparameter = INPUT_ZBX_CNF_USERPARAMETER
        )
    except Exception as e:
        logging.error("Runtime has error: {!s}.Please check.".format(e))
        exit(1)
