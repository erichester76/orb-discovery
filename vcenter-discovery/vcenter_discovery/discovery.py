from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
from netboxlabs.diode.sdk import DiodeClient
from netboxlabs.diode.sdk.ingester import Device, VirtualMachine, Cluster, Interface, VMInterface, VirtualDisk, IPAddress, Prefix, Entity


from .transformer import Transformer
transformer = Transformer(
    "includes/host_site_rules.yml",
    "includes/host_tenant_rules.yml",
    "includes/vm_role_rules.yml",
    "includes/vm_tenant_rules.yml",
    "includes/skip_vms.yml"
)

def extract_serial_number(other_identifying_info):
    if other_identifying_info:
        for item in other_identifying_info:
            if hasattr(item, "identifierType") and item.identifierType.key == "SerialNumberTag":
                return item.identifierValue
    return ""

def discover_vcenter(diode_target, diode_api_key, vcenter_host, vcenter_username, vcenter_password):
    si = None
    try:
        si = SmartConnect(host=vcenter_host, user=vcenter_username, pwd=vcenter_password, sslContext=None)
        content = si.RetrieveContent()
        diode = DiodeClient(
            target=diode_target,
            api_key=diode_api_key,
            app_name="vcenter-discovery",
            app_version="0.0.1"
        )

        def _get_nic_type(link_speed):
            if link_speed is None:
                return "other"
            link_speed_map = {
                1000: "1000base-t",
                10000: "10gbase-x-sfpp",
                25000: "25gbase-x-sfp28",
                40000: "40gbase-x-qsfpp",
                100000: "100gbase-x-qsfp28",
            }
            return link_speed_map.get(link_speed, "other")

        # Process hosts
        for datacenter in content.rootFolder.childEntity:
            for cluster in datacenter.hostFolder.childEntity:
                try:
                    site_name = transformer.host_to_site(cluster.name)
                    tenant = transformer.host_to_tenant(cluster.name)
                    if not hasattr(cluster, "host"):
                        continue
                    for host in cluster.host:
                        try:
                            clean_name = transformer.clean_name(host.name)
                            host_nics = []
                            for vnic in host.config.network.vnic:
                                ip_addresses = []
                                if vnic.spec.ip and hasattr(vnic.spec.ip, 'ipAddress'):
                                    from ipaddress import IPv4Network
                                    for ip in vnic.spec.ip.ipAddress.split(','):
                                        subnet_mask = vnic.spec.ip.subnetMask if hasattr(vnic.spec.ip, 'subnetMask') else None
                                        if subnet_mask:
                                            prefix_length = IPv4Network(f"0.0.0.0/{subnet_mask}").prefixlen
                                            ip_addresses.append(f"{ip}/{prefix_length}")
                                        else:
                                            ip_addresses.append(ip)
                                host_nics.append({
                                    "name": vnic.device,
                                    "type": "virtual",
                                    "mac_address": vnic.spec.mac,
                                    "ip_addresses": ip_addresses,
                                })
                            for pnic in host.config.network.pnic:
                                link_speed = pnic.linkSpeed.speedMb if pnic.linkSpeed else None
                                nic_type = _get_nic_type(link_speed)
                                host_nics.append({
                                    "name": pnic.device,
                                    "type": nic_type,
                                    "mac_address": getattr(pnic, "mac", ""),
                                    "ip_addresses": [],
                                })
                            serial_number = extract_serial_number(host.summary.hardware.otherIdentifyingInfo)
                            entity = Entity(device=Device(
                                name=clean_name,
                                manufacturer=host.hardware.systemInfo.vendor,
                                device_type=host.summary.hardware.model,
                                device_role="Hypervisor Host",
                                serial_number=serial_number,
                                platform=host.summary.config.product.fullName,
                                status="active" if host.summary.runtime.powerState == "poweredOn" else "offline",
                                site=site_name,
                                tenant=tenant,
                                interfaces=[
                                    Interface(
                                        name=nic["name"],
                                        type=nic["type"],
                                        mac_address=nic["mac_address"],
                                        ip_addresses=[IPAddress(address=ip) for ip in nic["ip_addresses"]]
                                    ) for nic in host_nics
                                ]
                            ))
                            diode.ingest(entity)
                            
                        except Exception as e:
                            print(f"Error processing host {host.name}: {e}")
                except Exception as e:
                    print(f"Error processing cluster {cluster.name}: {e}")

        # Process VMs
        def _fetch_vms_from_folder(folder):
            for vm in folder.childEntity:
                if isinstance(vm, vim.VirtualMachine):
                    try:
                        skip = transformer.should_skip_vm(vm.name)
                        if skip:
                            continue
                        vm_interfaces = []
                        for net in vm.guest.net:
                            if hasattr(vm, 'config') and hasattr(vm.config, 'hardware'):
                                for device in vm.config.hardware.device:
                                    if isinstance(device, vim.vm.device.VirtualEthernetCard):
                                        ipv4_addresses = []
                                        ipv6_addresses = []
                                        if net.macAddress == device.macAddress:
                                            ip_config = getattr(net, 'ipConfig', None)
                                            if ip_config and hasattr(ip_config, 'ipAddress'):
                                                for ip in ip_config.ipAddress:
                                                    if ':' in ip.ipAddress:
                                                        ipv6_addresses.append({"address": ip.ipAddress, "prefix_length": getattr(ip, 'prefixLength', 48)})
                                                    else:
                                                        ipv4_addresses.append({"address": ip.ipAddress, "prefix_length": getattr(ip, 'prefixLength', 24)})
                                        vm_interfaces.append({
                                            "name": device.deviceInfo.label,
                                            "mac_address": device.macAddress if hasattr(device, 'macAddress') else "",
                                            "enabled": device.connectable.connected if hasattr(device, 'connectable') else False,
                                            "ipv4_addresses": ipv4_addresses,
                                            "ipv6_addresses": ipv6_addresses,
                                        })
                        vm_disks = [
                            {"capacity": round(disk.capacityInKB / 1024)}
                            for disk in vm.config.hardware.device if hasattr(disk, "capacityInKB")
                        ]
                        
                        entity = Entity(virtual_machine=VirtualMachine(
                            name=vm.name,
                            status="active" if vm.runtime.powerState == "poweredOn" else "offline",
                            site=transformer.host_to_site(vm.runtime.host.name) if vm.runtime.host else "",
                            cluster=vm.runtime.host.parent.name if vm.runtime.host else "",
                            role=transformer.vm_to_role(vm.name),
                            device=transformer.clean_name(vm.runtime.host.name) if vm.runtime.host else "",
                            platform=vm.guest.guestFullName if vm.guest and vm.guest.guestFullName else "Unknown",
                            vcpus=vm.config.hardware.numCPU if hasattr(vm.config.hardware, "numCPU") else 0,
                            memory_mb=vm.config.hardware.memoryMB if hasattr(vm.config.hardware, "memoryMB") else 0,
                            disk=sum(d["capacity"] for d in vm_disks),
                            tenant=transformer.vm_to_tenant(vm.name),
                            comments=vm.summary.config.annotation if vm.summary.config.annotation else "",
                            interfaces=[
                                Interface(
                                    name=iface["name"],
                                    mac_address=iface["mac_address"],
                                    enabled=iface["enabled"],
                                    ip_addresses=[
                                        IPAddress(address=ip["address"], prefix_length=ip["prefix_length"])
                                        for ip in iface["ipv4_addresses"] + iface["ipv6_addresses"]
                                    ]
                                ) for iface in vm_interfaces
                            ]
                        ))
                        diode.ingest(entity)

                    except Exception as e:
                        print(f"Error processing VM {vm.name}: {e}")
                elif isinstance(vm, vim.Folder):
                    _fetch_vms_from_folder(vm)

        for datacenter in content.rootFolder.childEntity:
            vm_folder = datacenter.vmFolder
            _fetch_vms_from_folder(vm_folder)

    except Exception as e:
        print(f"Error during discovery: {e}")
    finally:
        if si:
            Disconnect(si)