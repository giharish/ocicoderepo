import oci
import pandas as pd
from datetime import datetime, timedelta
import os

# Load config and create Cost Analysis client
config = oci.config.from_file(file_location='/Users/girishraja/.oci/config', profile_name='DEFAULT')
usage_client = oci.usage_api.UsageapiClient(config)

# === PARAMETERS ===
compartment_ocid = "ocid1.tenancy.oc1..aaaaaaaakilrwdkq74qaqcavit6uem56h5dia6l3qiyp4mfrzeey7iuoad6q"  # BU compartment OCID
target_compartment_name = "tvscreditai"
tenancy_ocid = config["tenancy"]
# Today at midnight UTC
today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)

# Yesterday at midnight UTC
yesterday = today - timedelta(days=1)

# Day before yesterday
day_before_yesterday = today - timedelta(days=2)

# Format to ISO 8601 with Z
dby = day_before_yesterday.isoformat().replace('+00:00', 'Z')
y = yesterday.isoformat().replace('+00:00', 'Z')
t = today.isoformat().replace('+00:00', 'Z')

print("Start:", yesterday)
print("End:", today)

# === FUNCTION TO FETCH COST DATA ===
def fetch_daily_costs(start_date, end_date):
    request = oci.usage_api.models.RequestSummarizedUsagesDetails(
        tenant_id=tenancy_ocid,
        time_usage_started=start_date,
        time_usage_ended=end_date,
        granularity="DAILY",
        compartment_depth=6,
        group_by=["service", "compartmentName"]
    )
    response = usage_client.request_summarized_usages(request_summarized_usages_details = request)

    # Extract relevant data
    data = []
    for item in response.data.items:
        if item.compartment_name == target_compartment_name:
            data.append({
                "service": item.service,
                "date": item.time_usage_started.date(),
                "cost": item.computed_amount
            })

    return pd.DataFrame(data)

# === FETCH COSTS ===
df_today = fetch_daily_costs(y, t )
df_yesterday = fetch_daily_costs(dby, y)

# === MERGE AND CALCULATE DEVIATION ===
report = pd.merge(
    df_today, df_yesterday,
    on="service", how="outer", suffixes=('_today', '_yesterday')
).fillna(0)

report["%_change"] = ((report["cost_today"] - report["cost_yesterday"]) /
                      report["cost_yesterday"].replace(0, 0.01)) * 100

# === FORMAT FOR EMAIL OR STORAGE ===
report = report[["service", "cost_today", "cost_yesterday", "%_change"]]
report = report.sort_values(by="cost_today", ascending=False)

# === OPTIONAL: Save to CSV or HTML ===
report.to_csv(f"oci_daily_cost_{today}.csv", index=False)
report.to_html(f"oci_daily_cost_{today}.html", index=False)

print("✅ Daily cost report generated.")
