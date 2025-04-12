from pyVmomi import vim, vmodl
from pyVim.connect import SmartConnect, Disconnect
from diode_sdk import DiodeClient

def discover_vcenter(diode_target, diode_api_key, vcenter_host, vcenter_username, vcenter_password):
    si = SmartConnect(host=vcenter_host, user=vcenter_username, pwd=vcenter_password)
    try:
        content = si.RetrieveContent()
        host_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
        hosts = host_view.view
        diode = DiodeClient(target=diode_target, api_key=diode_api_key)
        for host in hosts:
            device = {
                "type": "device",
                "name": host.name,
                "hostname": host.name,
                "site": "Default Site",  # Adjust as needed
            }
            diode.send(device)
    finally:
        Disconnect(si)