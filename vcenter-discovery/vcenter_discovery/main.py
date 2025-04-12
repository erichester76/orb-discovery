import argparse
import netboxlabs.diode.sdk.version as SdkVersion
from .discovery import discover_vcenter
from .version import version_semver

def main():
    parser = argparse.ArgumentParser(description='Clemson University vCenter Discovery Backend')
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"CU Vcenter Discovery version: {version_semver()} "
        f"Diode SDK version: {SdkVersion.version_semver()}",
        help="Display Vcenter Version and Diode SDK versions",
    )
    parser.add_argument('-t', '--diode-target', required=True, help='Diode target URL')
    parser.add_argument('-k', '--diode-api-key', required=True, help='Diode API key')
    parser.add_argument('--vcenter-host', required=True, help='vCenter host')
    parser.add_argument('--vcenter-username', required=True, help='vCenter username')
    parser.add_argument('--vcenter-password', required=True, help='vCenter password')
    args = parser.parse_args()
    discover_vcenter(args.diode_target, args.diode_api_key, args.vcenter_host, args.vcenter_username, args.vcenter_password)

if __name__ == '__main__':
    main()