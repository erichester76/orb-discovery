from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
from netboxlabs.diode.sdk import DiodeClient
from netboxlabs.diode.sdk.ingester import Device, VirtualMachine, Cluster, Interface, VMInterface, VirtualDisk, IPAddress, Prefix, Entity


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
            device_data = {
                "type": "device",
                "name": host.name,
                "hostname": host.name,
                "site": "Default Site",
            }
            if DiodeClient and Entity and Device:
                entity = Entity(device=Device(name=host.name, hostname=host.name, site="Default Site"))
                diode.ingest(entity)
            else:
                print(f"Debug: Would send to Diode: {device_data}")
        host_view.Destroy()
    except Exception as e:
        print(f"Error during discovery: {e}")
    finally:
        if si:
            Disconnect(si)