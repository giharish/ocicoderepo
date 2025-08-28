import oci
from collections import defaultdict
import csv

# Load configuration from default location (~/.oci/config)
config = oci.config.from_file(file_location='/Users/girishraja/.oci/config', profile_name='CIFCLSV6')
identity = oci.identity.IdentityClient(config)
vss_client = oci.vulnerability_scanning.VulnerabilityScanningClient(config)
tenancy_id = config["tenancy"]

# Helper: fetch all active compartments
def get_all_compartments(identity_client, tenancy_id):
    resp = oci.pagination.list_call_get_all_results(
        identity_client.list_compartments,
        compartment_id=tenancy_id,
        compartment_id_in_subtree=True,
        access_level="ACCESSIBLE"
    )
    comps = [c for c in resp.data if c.lifecycle_state == "ACTIVE"]
    # also include root tenancy
    comps.append(identity_client.get_tenancy(tenancy_id).data)
    return comps

comps = get_all_compartments(identity, tenancy_id)

# Dictionary to map CVE → { "severity": ..., "hosts": set() }
cve_map = defaultdict(lambda: {"severity": "", "description": "", "hosts": set()})

for comp in comps:
    print(f"Checking compartment: {comp.name}")
    try:
        # Fetch scan results in compartment
        scan_results = oci.pagination.list_call_get_all_results(
            vss_client.list_host_agent_scan_results,
            compartment_id=comp.id
        ).data

        for scan in scan_results:
            # List vulnerabilities for each scan result
            vulnerabilities = oci.pagination.list_call_get_all_results(
                vss_client.list_host_agent_vulnerabilities,
                host_agent_scan_result_id=scan.id
            ).data

            for v in vulnerabilities:
                cve_id = v.cve_reference or "NO-CVE"
                cve_map[cve_id]["severity"] = v.severity
                cve_map[cve_id]["description"] = v.name or ""
                # The impacted host OCID / name (depending on availability)
                cve_map[cve_id]["hosts"].add(scan.target_id)
    except Exception as e:
        print(f"Error in {comp.name}: {e}")

# Export to CSV
with open("oci_cve_hosts.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["CVE", "Severity", "Description", "Impacted Hosts"])
    for cve, details in cve_map.items():
        writer.writerow([
            cve,
            details["severity"],
            details["description"],
            "; ".join(details["hosts"])
        ])

print(f"✅ Export complete. Found {len(cve_map)} CVEs. Output saved to oci_cve_hosts.csv")
