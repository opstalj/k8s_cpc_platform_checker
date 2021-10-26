# This file contains parameters used by CPC_platform_checker:
# Define here your platform parameters
#
# info: jan.van_opstal@nokia.com
#
# v21.10

# for now:
worker_node_username='core'
skip_username_worker_node_to_ssh=True

# platform: set to: ncs (NCS), os (OpenShift) or gcp (Google Anthos)
target_platform='gcp'

# container runtime: 'docker', 'containerd'
container_runtime='docker'

# worker node NIC brand: 'Intel', 'Mellanox'
nic_brand='Mellanox'

# K8s CNI: 'calico', 'cilium'
k8s_cni='cilium'

# start commands with:
# could be: kubectl, sudo kubectl, sudo KUBECONFIG=$KUBECONFIG kubectl, ...
cmd_start_kubectl='sudo KUBECONFIG=$KUBECONFIG kubectl '

# OPTIONAL: skip the following node(s) when running script:
# eg: nodes_to_skip=['labmechra010n110.lab.tc.intern.telenet.be']
nodes_to_skip=[]

# OPTIONAL: skip the following checks: 
# NOTE: run: 'python3 cpc_k8s_platform_check_v21.9.py --listchecks' to get an overview of possible checks 
checks_to_skip=['check_glusterFS','check_AMF_worker_nodes_docker_msgqueue_unlimited']

# OPTIONAL: run checks in alphabetical order
run_checks_alphabetically=True

# check before running CPC_checker:
##################################
# generic:
namespace_istio_system='istio-system'
podname_istio_ingressgateway='istio-ingressgateway'
#namespace_istio_system='gke-system'
#podname_istio_ingressgateway='istio-ingress'

# nrd:
#namespace_nrd_dabatase='nrd-database'
namespace_nrd_dabatase='nrd'
namespace_nrd='nrd'
check_nrd_istio=True
label_nrdnode='nrd=nrd1'
label_nrd_database='app=nrddb'
label_nrd='app=nrd'
check_NRD_performance=True

# amf:
namespace_amf='amf'
#label_amf='region=amf'
label_amfnode='baremetal.cluster.gke.io/node-pool=node-pool-1'
amf_worker_node_rmem_max=4194304
amf_worker_node_wmem_max=4194304
# OPTIONAL: ipvlan host interfaces (see values file of AMF):
#leave empty when not using ipvlan 
#amf_host_interface_list=['bond0.101','bond0.301','bond0.401']
amf_host_interface_list=['bond0.101','bond0.301','bond0.401']


# cmg:
# if using dpdk, the worker nodes should use huge pages
deploy_cmg_with_dpdk=True
cmg_worker_node_rmem_max=4194304
cmg_worker_node_wmem_max=4194304
cmg_worker_node_udp_rmem_min=1048576
cmg_worker_node_udp_wmem_min=1048576                                                          

# smf/upf:
namespace_smf='smf'
namespace_upf='upf'
label_cmgnode='hostname=worker'
#leave empty when you do not want the SRIOV interfaces being checked
# OPTIONAL: if sriov device plugin is used, check the CMG SRIOV defined interfaces:
# -> state, mtu size, num of vf, trust on
#  k get cm sriovdp-config -n kube-system -o 'go-template={{index .data "config.json" }}' | awk -F"[][]" '/pfNames/ { printf "["$2"]\n"}'
# eg: cmg_sriov_interface_list=['eno5','ens1f0','eno6','ens1f1','ens2f0','ens3f0','ens2f1','ens3f1']
cmg_sriov_interface_list=[]
cmg_sriov_interface_mtu_min=8900

# variables for report:
dotline_length=100
level1=2
level2=5
level3=7
level4=11
check_failed=False
check_passed=True