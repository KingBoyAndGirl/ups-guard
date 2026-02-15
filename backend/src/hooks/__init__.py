"""Pre-Shutdown Hook 插件模块"""

# 导入所有 hook 插件以触发注册
from hooks import ssh_shutdown
from hooks import windows_shutdown
from hooks import synology_shutdown
from hooks import qnap_shutdown
from hooks import http_api
from hooks import custom_script

