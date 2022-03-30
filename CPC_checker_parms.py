# This file contains parameters used by CPC_platform_checker:
# Define here your platform parameters
#
# info: jan.van_opstal@nokia.com
#
# v22.04

# for now:
worker_node_username='core'
skip_username_worker_node_to_ssh=True

# target platform -> set to one of these: 
#   ncs     : Nokia Container Services (NCS)
#   os      : RedHat's OpenShift 
#   gcp     : Google Cloud Platform (Anthos)
#   eccd    : Ericson's Cloud Container Distribution
#   k8s     : native k8s platform
target_platform='gcp'

# container runtime: 'docker', 'containerd'
container_runtime='docker'

# worker node NIC brand: 'Intel', 'Mellanox'
nic_brand='Mellanox'

# K8s CNI: 'calico', 'cilium'
k8s_cni='cilium'

# start commands with:
# could be: kubectl, sudo kubectl, sudo KUBECONFIG=$KUBECONFIG kubectl, ...
# for OpenShift: oc
cmd_start_kubectl='sudo KUBECONFIG=$KUBECONFIG kubectl '

# label to define a worker node:
labels_workernode=['baremetal.cluster.gke.io/node-pool=node-pool-1']

# OPTIONAL: skip the following node(s) when running script:
# eg: nodes_to_skip=['labmechra010n110.lab.tc.intern.telenet.be']
nodes_to_skip=[]

# OPTIONAL: skip the following checks: 
# NOTE: run: 'python3 cpc_k8s_platform_check_v21.9.py --listchecks' to get an overview of possible checks 
checks_to_skip=['check_glusterFS','check_AMF_worker_nodes_docker_msgqueue_unlimited']

# OPTIONAL: run checks in alphabetical order
run_checks_alphabetically=True

# print out extra info about which nodes are used by the script
show_extra_info=False                                                               
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
labels_nrdnode=['nrd=nrd1']
label_nrd_database='app=nrddb'
label_nrd='app=nrd'
check_NRD_performance=True
nrd_worker_node_sysctl={
'net.ipv4.tcp_slow_start_after_idle': 0,
'net.netfilter.nf_conntrack_tcp_timeout_unacknowledged': 10,
'net.netfilter.nf_conntrack_tcp_timeout_max_retrans': 10
}

# amf:
namespace_amf='amf'
#label_amf='region=amf'
labels_amfnode=['baremetal.cluster.gke.io/node-pool=node-pool-1']
# AMF sysctl values
# note: kernel.sched_rt_runtime_us': -1 -> only for RHEL / CentOS (Openshift, NCS, ...)
amf_worker_node_sysctl={
'net.core.rmem_max': 4194304,
'net.core.wmem_max': 4194304,
'kernel.sched_rt_runtime_us': -1,
'kernel.core_pattern': '/var/crash/core.%p'
}
# OPTIONAL: check IPSEC (for 4G - LI)
check_amf_ipsec=True
if check_amf_ipsec:
    amf_worker_node_sysctl['net.ipv4.conf.all.accept_redirects']=0
    amf_worker_node_sysctl['net.ipv4.conf.all.send_redirects']=0
    amf_worker_node_sysctl['net.ipv4.conf.default.rp_filter']=0
    amf_worker_node_sysctl['net.ipv4.conf.default.accept_source_route']=0
    amf_worker_node_sysctl['net.ipv4.conf.default.send_redirects']=0
    amf_worker_node_sysctl['net.ipv4.icmp_ignore_bogus_error_responses']=1
    amf_worker_node_sysctl['net.ipv4.conf.all.rp_filter']=0
# OPTIONAL: ipvlan host interfaces (see values file of AMF):
#leave empty when not using ipvlan 
#amf_ipvlan_interface_list=['bond0.101','bond0.301','bond0.401']
amf_ipvlan_interface_list=['bond0.101','bond0.301','bond0.401']

# cmg:
# if using dpdk, the worker nodes should use huge pages
deploy_cmg_with_dpdk=True

# CMG sysctl values
cmg_worker_node_sysctl={
'net.ipv4.ip_forward' : 1,                          
'net.ipv4.tcp_rmem' : '187380 655360 6291456',
'net.ipv4.tcp_wmem' : '187380 655360 6291456',                                              
'net.ipv4.udp_rmem_min' : 1048576,
'net.ipv4.udp_wmem_min' : 1048576,
'net.ipv6.conf.all.forwarding' : 1,
'net.core.rmem_max':4194304,
'net.core.wmem_max':4194304,
'net.core.rmem_default' : 1048576,
'net.core.wmem_default' : 1048576
} 

# smf/upf:
namespace_smf='smf'
namespace_upf='upf'
labels_cmgnode=['hostname=worker']
# SRIOV:
labels_cmgnode_sriov=[]        
#leave empty when you do not want the SRIOV interfaces being checked
# OPTIONAL: if sriov device plugin is used, check the CMG SRIOV defined interfaces:
# -> state, mtu size, num of vf, trust on
#  k get cm sriovdp-config -n kube-system -o 'go-template={{index .data "config.json" }}' | awk -F"[][]" '/pfNames/ { printf "["$2"]\n"}'
# eg: cmg_sriov_interface_list=['eno5','ens1f0','eno6','ens1f1','ens2f0','ens3f0','ens2f1','ens3f1']
cmg_sriov_interface_list=[]
cmg_sriov_interface_mtu_min=8900
# IPVLAN:
# if you use a specific set of worker nodes for hosting the CMG OAM pods,
# then you can add their label here
# if they are the same worker nodes as where the other CMG pods can land, then no need to fill in the labels_cmgnode_ipvlan
labels_cmgnode_ipvlan=[] 
# ipvlan for oam:
cmg_ipvlan_interface_list=[]
#
# CSF: check whether k8s cluster interface has got correct mtu size
# worker node k8s cluster interface name
# eg:   calico  -> tunl0
#       cilium  -> cilium_host
cmg_workernode_k8s_interface_name='tunl0'
cmg_CSF_mtu_size=9000

# LOG REPORT to FILE:
#####################
# send report output to file - files are kept in subfolder 'report_history'
CREATE_REPORT_FILE=True
# report file prefix -> full name becomes: REPORT_FILE_PREFIX + '_' + timestamp + '.log'
REPORT_FILE_PREFIX = 'Telenet_pre-prod'
report_header_length=115

# variables for report:
dotline_length=100
level1=2
level2=5
level3=7
level4=11
check_failed=False
check_passed=True