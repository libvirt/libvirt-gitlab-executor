#!/bin/bash

PASS=true
LOG_FILE="gitlab-provisioner.log"
POOL_PATH="/var/lib/libvirt/images/base_imgs"
SCRIPT_BASE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
COMMON_SSH_ARGS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

> $LOG_FILE


print_ok() {
    CLEAR=$(tput sgr0)
    RED=$(tput setaf 1)
    GREEN=$(tput setaf 2)

    action=$1
    ret=1
    shift

    echo -en "[i] $action\r"
    run "$@"
    if [[ $? -eq 0 ]]; then
        echo -e "[${GREEN}OK${CLEAR}] $action"
        ret=0
    else
        echo -e "[${RED}FAILED${CLEAR}] $action"
        ret=1
        PASS=false
    fi

    return $ret
}


log() {
    echo "$@" &>> $LOG_FILE
}


log_cmd() {
    echo >> $LOG_FILE
    printf '=%.0s' {1..80} >> $LOG_FILE; echo >> $LOG_FILE
    echo "$ $@" &>> $LOG_FILE
    printf '=%.0s' {1..80} >> $LOG_FILE; echo >> $LOG_FILE
}


run() {
    log_cmd "$@"
    "$@" &>> $LOG_FILE
}


create_libvirt_base_img_pool() {
    if ! [[ -d "$POOL_PATH" ]]; then
        mkdir "$POOL_PATH"
    fi

    if ! (virsh --quiet pool-list --all | grep base_imgs &>/dev/null); then
        print_ok "Create a new storage pool for base images" \
                 virsh pool-define-as \
                       --name base_imgs \
                       --type dir \
                       --target "$POOL_PATH"
    fi
}


wait_for_domain_status() {
    domain=$1
    state=$2

    timeout=1
    while true; do
        if [[ $timeout -ge 30 ]]; then
            log "Maximum timeout reached waiting for domain $domain"
            return 1
        fi

        if [[ "$state" == "running" ]]; then
            if (ping -4 -c 1 $domain &>/dev/null) &&
                ssh $COMMON_SSH_ARGS $distro /bin/true; then
                break
            fi
        elif [[ "$state" == "shut off" ]]; then
            if [[ $(virsh domstate "$domain") == "$state" ]]; then
                break
            fi
        fi

        sleep $timeout
        timeout=$(( 2 * timeout ))
    done
}

start_domain() {
    distro=$1

    if ! (virsh list --name --all | grep $distro &>/dev/null); then
        log "ERROR: Template image not found, please install it manually..."
        return 1
    fi

    if [[ $(virsh domstate $distro) != "running" ]]; then
        run virsh start $distro || return 1
        wait_for_domain_status $distro "running"
    fi
}


stop_domain() {
    distro=$1

    if ! (virsh list --name --all | grep $distro &>/dev/null); then
        log "ERROR: Template image not found, please install it manually..."
        return 1
    fi

    run virsh shutdown $distro || return 1
    wait_for_domain_status $distro "shut off"
}

prepare_base_image() {
    distro=$1

    print_ok "Shut down virtual machine [$distro]" stop_domain $distro

    print_ok "Create a machine template [$distro]" \
             virt-sysprep --run-command "systemctl disable libvirtd.service" \
                          --run-command "systemctl disable libvirtd.socket" \
                          -d "$distro" || return 1
}

tput civis
while [ $# -gt 0 ]; do
    distro="$1"
    shift

    prepare_base_image $distro || continue
done
tput cnorm

if ! $PASS; then
    echo "See '$LOG_FILE' for more details about the failures"
fi
