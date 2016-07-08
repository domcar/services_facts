# services_facts
provides facts of services in json format, it works with all init systems

usage: sudo python services.py

OUTPUT:

    "init": {
        "accounts-daemon_service": "enabled",
        "acpid_service": "enabled",
        "apache-htcacheclean_service": "disabled",
        "apache2_service": "enabled",
        "apport-forward@_service": "static",
        "apport_service": "enabled",
        "apt-daily_service": "static",
        "atd_service": "enabled",
         .
         .
         .
    "status": {
        "accounts-daemon_service": "active",
        "acpid_service": "active",
        "apache-htcacheclean_service": "active",
        "apache2_service": "active",
        "apparmor_service": "active",
        "apport_service": "active",
        "apt-daily_service": "inactive",
        "atd_service": "active",
         .
         .
         .
