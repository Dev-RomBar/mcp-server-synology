# src/readonly.py - Fork: the server can only read.
#
# Two independent allowlists. The tool list decides what the model can call; the API
# list decides what reaches DSM, whatever a handler tries to send. A tool added upstream
# stays hidden until it is listed here, and a DSM method no listed tool needs is refused.

# Health and storage only: no File Station, Download Station, users or groups.
READ_ONLY_TOOLS = frozenset(
    {
        "synology_list_nas",
        "synology_system_info",
        "synology_utilization",
        "synology_disk_health",
        "synology_disk_smart",
        "synology_volume_status",
        "synology_storage_pool",
        "synology_lun_list",
        "synology_lun_get",
        "synology_target_list",
        "synology_target_get",
        "synology_network",
        "synology_ups",
        "synology_services",
        "synology_system_log",
        "synology_health_summary",
        "synology_nfs_status",
        "synology_nfs_list_shares",
        "synology_reverse_proxy_list",
        "synology_reverse_proxy_get",
        "synology_access_control_profile_list",
        "synology_container_list",
        "synology_container_health_summary",
        "synology_container_disk_usage",
        "synology_container_resource",
    }
)

# Every (api, method) pair the tools above send to /webapi/entry.cgi, fallbacks included.
READ_ONLY_API_METHODS = frozenset(
    {
        ("SYNO.Core.System", "info"),
        ("SYNO.DSM.Info", "getinfo"),
        ("SYNO.Core.System.Utilization", "get"),
        ("SYNO.Core.Storage.Disk", "list"),
        ("SYNO.Core.Storage.Volume", "list"),
        ("SYNO.Core.Storage.Pool", "list"),
        ("SYNO.Storage.CGI.Storage", "load_info"),
        ("SYNO.Storage.CGI.Smart", "get_smart_info"),
        ("SYNO.Core.ISCSI.LUN", "list"),
        ("SYNO.Core.ISCSI.Target", "list"),
        ("SYNO.Core.ISCSI.Target", "get"),
        ("SYNO.Core.Network", "get"),
        ("SYNO.Core.ExternalDevice.UPS", "get"),
        ("SYNO.Core.Package", "list"),
        ("SYNO.Core.SyslogClient.Log", "list"),
        ("SYNO.Core.FileServ.NFS", "get"),
        ("SYNO.Core.Share", "list"),
        ("SYNO.Core.AppPortal.ReverseProxy", "list"),
        ("SYNO.Core.AppPortal.AccessControl", "list"),
        ("SYNO.Docker.Container", "list"),
        ("SYNO.Docker.Container.Resource", "get"),
        ("SYNO.Docker.Image", "list"),
    }
)


def refusal(api: str, method: str) -> dict:
    """The failure a refused DSM call returns, shaped like any other API error."""
    return {
        "success": False,
        "error": {
            "code": "read_only",
            "message": f"{api}.{method} is not a read-only call; this server never sends it.",
        },
    }
