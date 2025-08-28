import oci
import csv

# Config
config = oci.config.from_file(file_location='/Users/girishraja/.oci/config', profile_name='DEFAULT')
vss_client = oci.vulnerability_scanning.VulnerabilityScanningClient(config)
compute_client = oci.core.ComputeClient(config)

TENANCY_OCID = config["tenancy"]

# Collect all CVEs
vulnerabilities = []
response = oci.pagination.list_call_get_all_results(
    vss_client.list_host_vulnerabilities,
    compartment_id=TENANCY_OCID
)

for vuln in response.data:
    # Get impacted hosts
    impacted_hosts = vss_client.list_host_vulnerability_impacted_hosts(
        host_vulnerability_id=vuln.id
    ).data

    for host in impacted_hosts:
        try:
            # Use instance_id instead of host_id
            instance = compute_client.get_instance(host.instance_id).data
            instance_name =_
