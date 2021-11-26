#!/bin/bash

PASS=true
WORKSPACE="/opt/gitlab"
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


install_lcitool() {
    LCITOOL_DIR="$WORKSPACE/libvirt-ci.git/guests/lcitool"

    if lcitool &>/dev/null; then
        return 0
    fi

    if [[ -d "$WORKSPACE/libvirt-ci.git" ]]; then
        print_ok "Update lcitool" git -C "$WORKSPACE/libvirt-ci.git" \
                 pull --rebase
    else
        print_ok "Clone lcitool repo" \
                 git clone https://gitlab.com/libvirt/libvirt-ci.git \
                           "$WORKSPACE/libvirt-ci.git"
    fi

    export PYTHONPATH="$LCITOOL_DIR"
    print_ok "Install lcitool" python3 setup.py develop
    unset PYTHONPATH
}


create_workspace() {
    if ! [[ -d "$WORKSPACE" ]]; then
        print_ok "Create a new workspace" mkdir -p "$WORKSPACE"
    fi

    if ! [[ -f "$WORKSPACE/id_ed25519" ]]; then
        print_ok "Generate a new SSH key pair" ssh-keygen -q \
                                                          -N "" \
                                                          -t ed25519 \
                                                          -C gitlab-runner \
                                                          -f "$WORKSPACE/id_ed25519"
    fi
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

    print_ok "Start virtual machine [$distro]" start_domain $distro || return 1

    print_ok "Customize machine for GitLab [$distro]" \
             ansible-playbook -i "$distro," \
                              --ssh-common-args "$COMMON_SSH_ARGS" \
                              "$SCRIPT_BASE/playbooks/main.yml" || return 1

    print_ok "Shut down virtual machine [$distro]" stop_domain $distro

    print_ok "Create a machine template [$distro]" \
             virt-sysprep --operations defaults,-ssh-userdir \
                          -d "$distro" || return 1
}

create_workspace || exit 1
install_lcitool || exit 1

for distro in fedora-34 centos-stream-8; do
    prepare_base_image $distro || continue
    print_ok "Undefine template machine [$distro]" virsh undefine $distro
done

if ! $PASS; then
    echo "See '$LOG_FILE' for more details about the failures"
fi
