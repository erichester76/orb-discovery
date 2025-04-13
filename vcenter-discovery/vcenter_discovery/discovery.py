from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
from netboxlabs.diode.sdk import DiodeClient

def discover_vcenter(diode_target, diode_api_key, vcenter_host, vcenter_username, vcenter_password):
    si = None
    try:
        si = SmartConnect(host=vcenter_host, user=vcenter_username, pwd=vcenter_password, sslContext=None)
        content = si.RetrieveContent()
        host_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
        hosts = host_view.view
        if DiodeClient:
            diode = DiodeClient(
                target=diode_target,
                api_key=diode_api_key,
                app_name="vcenter-discovery",
                app_version="0.0.1"
            )
        for host in hosts:
            device = {
                "type": "device",
                "name": host.name,
                "hostname": host.name,
                "site": "Default Site",
            }
            if DiodeClient:
                diode.ingest(device)
            else:
                print(f"Debug: Would send to Diode: {device}")
        host_view.Destroy()
    except Exception as e:
        print(f"Error during discovery: {e}")
    finally:
        if si:
            Disconnect(si)