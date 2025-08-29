import oci
import csv

# Config
config = oci.config.from_file(file_location='~/.oci/config', profile_name='DEFAULT')
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
    # Get impacted hosts (use .items)
    impacted_hosts = vss_client.list_host_vulnerability_impacted_hosts(
        host_vulnerability_id=vuln.id
    ).data

    for host in impacted_hosts.items:   # <-- FIXED
        try:
            # instance_id is the compute instance OCID
            instance = compute_client.get_instance(host.instance_id).data
            instance_name = instance.display_name
        except Exception:
            instance_name = "Unknown"

        vulnerabilities.append({
            "CVE": vuln.name,
            "Severity": vuln.severity,
            "InstanceID": host.instance_id,
            "InstanceName": instance_name,
            "CompartmentID": host.compartment_id
        })

# Write to CSV
with open("oci_vulnerabilities.csv", "w", newline="") as csvfile:
    fieldnames = ["CVE", "Severity", "InstanceID", "InstanceName", "CompartmentID"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(vulnerabilities)

print("✅ Export completed: oci_vulnerabilities.csv")
