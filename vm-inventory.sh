#!/bin/bash

# Output CSV file
output_file="oci_vm_inventory.csv"
echo "Region,Compartment Name,Instance Name,Shape,Lifecycle State,Image Name" > "$output_file"

# Get all regions
regions=$(oci iam region list --query "data[].\"name\"" --raw-output)

# Get all compartments
compartments=$(oci iam compartment list --all --compartment-id-in-subtree true --compartment-id $(oci iam compartment list --query "data[?contains(\"name\", 'root')].id" --raw-output) --query "data[?\"lifecycle-state\"=='ACTIVE'].{id:id,name:name}" --output json)

for region in $regions; do
  echo "Processing region: $region"

  export OCI_CLI_REGION=$region

  for row in $(echo "$compartments" | jq -c '.[]'); do
    comp_id=$(echo "$row" | jq -r '.id')
    comp_name=$(echo "$row" | jq -r '.name')

    # Get all instances in this compartment
    instances=$(oci compute instance list --compartment-id "$comp_id" --all --query 'data[?"lifecycle-state" != `TERMINATED`]' --output json)

    for inst in $(echo "$instances" | jq -c '.[]'); do
      name=$(echo "$inst" | jq -r ".display-name")
      shape=$(echo "$inst" | jq -r '.shape')
      state=$(echo "$inst" | jq -r '.["lifecycle-state"]')
      image_id=$(echo "$inst" | jq -r '.["source-details"]."image-id"')

      # Get image name from image ID
      image_name=$(oci compute image get --image-id "$image_id" --query 'data."display-name"' --raw-output 2>/dev/null)

      echo "$region,$comp_name,$name,$shape,$state,$image_name" >> "$output_file"
    done
  done
done

echo "✅ Inventory generated in: $output_file"
