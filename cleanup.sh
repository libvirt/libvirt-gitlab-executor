#!/bin/bash

source "./job${CUSTOM_ENV_CI_JOB_ID}"

set -eo pipefail

# destroy the transient VM and the overlay storage
virsh destroy "${VM_NAME}"
virsh vol-delete --pool default "${VM_IMAGE}"
