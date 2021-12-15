# CPC K8s platform checker tool

As you might know, the deployment of the Nokia CPC CNFs has quite some dependencies on the target platform.
Sometimes, it can be a hassle to check these pre-requirements, but if you don't, there is a big chance that your deployment will fail.

That's where the CPC K8s platform checker tool comes in :)!
It is written in python3 and allows you to check quickly whether the pre-requirements are fulfilled on the target Kubernetes platform :).
(currently around 20 checks are performed like CPU pinning, hugepages, multus, istio, whereabouts, ...)
Target platforms are all based on Kubernetes like:

- native K8s
- NCS (Nokia Container Services)
- Google Cloud Platform: Anthos
- Ericson's CCD (Cloud Container Distribution)
- RedHat's OpenShift
- ...

## Short instructions:

1. Download tool zip file (eg: cpc_k8s_platform_checker_v21_9.zip) file from: 

	Nokia Sharepoint CPC Community -> Tools -> [CPC_K8s_platform_checker](https://nokia.sharepoint.com/sites/cpc-community/CPC%20document%20library/Forms/AllItems.aspx?e=5%3Ad488902a526f4dce86667f051f1f8e68&at=9&FolderCTID=0x0120005A03A7568C4F3549BAFD8610CAC5F74F&viewid=8ccd19be%2D805b%2D443f%2Db414%2D985050af38f2&id=%2Fsites%2Fcpc%2Dcommunity%2FCPC%20document%20library%2FTools%2FCPC%20K8s%20platform%20checker) 

2. Put the zip file on a linux server from where you can run kubectl commands and reach the master/worker nodes.
3. Unzip the archive.
4. Tailor the `CPC_checker_parms.py` to your platform.
    
	> Make sure that your parameter file gets called:  `CPC_checker_parms.py`
	> 
	> Eg: you start from: `CPC_checker_parms_NCS_example.py` -> later on, copy over or overwrite as `CPC_checker_parms.py`
    
5. Start using the `cpc_k8s_platform_checker_v21.9.y` !
  
## Example 1 - installation & node check:

    [tc@jumpserver-01 cpc_k8s_platform_checker]$ ls -lrt
    total 16
    -rw-rw-r--. 1 tc tc 15388 Sep 10 08:30 cpc_k8s_platform_checker_v21_9.zip
    [tc@jumpserver-01 cpc_k8s_platform_checker]$ 
    [tc@jumpserver-01 cpc_k8s_platform_checker]$ unzip cpc_k8s_platform_checker_v21_9.zip 
    Archive:  cpc_k8s_platform_checker_v21_9.zip
      inflating: CPC_checker_parms.py    
      inflating: CPC_checker_parms_Anthos_example.py  
      inflating: CPC_checker_parms_ECCD_example.py  
      inflating: CPC_checker_parms_NCS_example.py  
      inflating: cpc_k8s_platform_checker_v21.9.py  
    [tc@jumpserver-01 cpc_k8s_platform_checker]$ 
    [tc@jumpserver-01 cpc_k8s_platform_checker]$ chmod 755 cpc_k8s_platform_checker_v21.9.py 
    [tc@jumpserver-01 cpc_k8s_platform_checker]$ 
    [tc@jumpserver-01 cpc_k8s_platform_checker]$ ./cpc_k8s_platform_checker_v21.9.py -n

    NAME                                       CAP_CPU   CAP_MEM       HUGE_1Gi   ARCH    ContRunTime                kernelVers                     kubeletVers        OSImage
    labmechra01n010.lab.tc.intern.telenet.be   48        263535820Ki   20Gi       amd64   containerd://1.4.6-gke.0   4.18.0-240.15.1.el8_3.x86_64   v1.20.5-gke.1301   Red Hat Enterprise Linux 8.3 (Ootpa)
    labmechra01n030.lab.tc.intern.telenet.be   48        263535820Ki   20Gi       amd64   containerd://1.4.6-gke.0   4.18.0-240.22.1.el8_3.x86_64   v1.20.5-gke.1301   Red Hat Enterprise Linux 8.3 (Ootpa)
    labmechra01n050.lab.tc.intern.telenet.be   48        263536008Ki   20Gi       amd64   containerd://1.4.6-gke.0   4.18.0-240.22.1.el8_3.x86_64   v1.20.5-gke.1301   Red Hat Enterprise Linux 8.3 (Ootpa)
    labmechra01n070.lab.tc.intern.telenet.be   48        263536008Ki   20Gi       amd64   containerd://1.4.6-gke.0   4.18.0-240.22.1.el8_3.x86_64   v1.20.5-gke.1301   Red Hat Enterprise Linux 8.3 (Ootpa)
    labmechra01n090.lab.tc.intern.telenet.be   48        263536028Ki   20Gi       amd64   containerd://1.4.6-gke.0   4.18.0-240.22.1.el8_3.x86_64   v1.20.5-gke.1301   Red Hat Enterprise Linux 8.3 (Ootpa)
    labmechra01n110.lab.tc.intern.telenet.be   48        263535880Ki   20Gi       amd64   containerd://1.4.6-gke.0   4.18.0-240.22.1.el8_3.x86_64   v1.20.5-gke.1301   Red Hat Enterprise Linux 8.3 (Ootpa)


    NAME                                       CAP_SRIOV_IAVF_1   CAP_SRIOV_IAVF_2   CAP_SRIOV_IAVF_3   CAP_SRIOV_IAVF_4
    labmechra01n010.lab.tc.intern.telenet.be   1                  1                  1                  1
    labmechra01n030.lab.tc.intern.telenet.be   64                 64                 1                  1
    labmechra01n050.lab.tc.intern.telenet.be   64                 64                 1                  1
    labmechra01n070.lab.tc.intern.telenet.be   64                 64                 1                  1
    labmechra01n090.lab.tc.intern.telenet.be   64                 64                 1                  1
    labmechra01n110.lab.tc.intern.telenet.be   64                 64                 1                  1

    [tc@jumpserver-01 cpc_k8s_platform_checker]$    

## Example 2 - global check:
    [tc@jumpserver-01 cpc_k8s_platform_checker]$ ./cpc_k8s_platform_checker_v21.10.py

    Progress: [########################################] 28/28                                                                       

    Successful tests [24/28]:
     - check_AMF_CPU_pinning
     - check_AMF_whereabouts_plugin_installed
     - check_AMF_worker_nodes_containerd_msgqueue_unlimited
     - check_AMF_worker_nodes_ipsec_enabled
     - check_AMF_worker_nodes_ipv6_enabled
     - check_AMF_worker_nodes_ipvlan_interfaces
     - check_AMF_worker_nodes_kernel_sched_rt_runtime
     - check_AMF_worker_nodes_rmem_max_socket_buffer
     - check_AMF_worker_nodes_sctp_enabled
     - check_AMF_worker_nodes_selinux_permissive
     - check_AMF_worker_nodes_transparent_hugepage_madvise
     - check_AMF_worker_nodes_wmem_max_socket_buffer
     - check_CMG_CPU_pinning
     - check_CMG_HugePages
     - check_CMG_net_ipv6_conf_all_forwarding
     - check_CMG_worker_nodes_rmem_default
     - check_CMG_worker_nodes_rmem_max_socket_buffer
     - check_CMG_worker_nodes_udp_rmem_min_socket_buffer
     - check_CMG_worker_nodes_udp_wmem_min_socket_buffer
     - check_CMG_worker_nodes_wmem_default
     - check_CMG_worker_nodes_wmem_max_socket_buffer
     - check_NRD_labels
     - check_istio
     - check_multus

    Failing tests    [4/28]:
     - check_CMG_worker_nodes_sriov_interfaces                       : node: worker0 number of VF functions = 0 (NOK: is not above 0)
     - check_NRD_performance_nf_conntrack_tcp_timeout_max_retrans    : node: worker0 does not have net.netfilter.nf_conntrack_tcp_timeout_max_retrans = 10
     - check_NRD_performance_nf_conntrack_tcp_timeout_unacknowledged : node: worker0 does not have net.netfilter.nf_conntrack_tcp_timeout_unacknowledged = 10
     - check_NRD_performance_tcp_slow_start                          : node: worker0 does not have net.ipv4.tcp_slow_start_after_idle = 0


## Example 3 - check AMF IPVLAN interfaces on worker nodes:
    [tc@jumpserver-01 cpc_k8s_platform_checker]$ ./cpc_k8s_platform_checker_v21.10.py -c check_AMF_worker_nodes_ipvlan_interfaces -v

    Progress: [########################################] 1/1                                                                       

    Successful tests [1/1]:
     - check_AMF_worker_nodes_ipvlan_interfaces

    CPC platform checker report:
    ****************************
    CPC checker version:     version 21.10
    Platform:                Google Cloud Platform (Anthos) - version: 
    K8s version:             Client Version: v1.22.2
                             Server Version: v1.20.5-gke.1301
    Start time:              2021-Oct-26 06:01:19

    -> check_AMF_worker_nodes_ipvlan_interfaces:
         node: worker0
           has interface: bond0.101 -> UP & RUNNING.......................................................... OK
           has interface: bond0.301 -> UP & RUNNING.......................................................... OK
           has interface: bond0.401 -> UP & RUNNING.......................................................... OK
         node: worker1
           has interface: bond0.101 -> UP & RUNNING.......................................................... OK
           has interface: bond0.301 -> UP & RUNNING.......................................................... OK
           has interface: bond0.401 -> UP & RUNNING.......................................................... OK
         node: worker2
           has interface: bond0.101 -> UP & RUNNING.......................................................... OK
           has interface: bond0.301 -> UP & RUNNING.......................................................... OK
           has interface: bond0.401 -> UP & RUNNING.......................................................... OK

    Some extra info:
    -> Worker nodes:              worker0
                                  worker1
                                  worker2
    -> NRD worker nodes:          worker0
                                  worker1
                                  worker2
    -> AMF worker nodes:          worker0
                                  worker1
                                  worker2
    -> CMG worker nodes:          worker0
                                  worker1
                                  worker2

    -> skipped nodes:             None
    -> skipped checks:            check_glusterFS
                                  check_AMF_worker_nodes_docker_msgqueue_unlimited

## Example 4: do a specific test on a specific worker node
	  [tc@jumpserver-01 cpc_k8s_platform_checker]$ ./cpc_k8s_platform_checker_v21.10.py -c check_AMF_worker_nodes_selinux_permissive -o worker2 -v

    Progress: [########################################] 1/1                                                                       

    Successful tests [1/1]:
     - check_AMF_worker_nodes_selinux_permissive

    CPC platform checker report:
    ****************************
    CPC checker version:     version 21.10
    Platform:                Google Cloud Platform (Anthos) - version: 
    K8s version:             Client Version: v1.22.2
                             Server Version: v1.20.5-gke.1301
    Start time:              2021-Oct-26 06:07:25

    -> check_AMF_worker_nodes_selinux_permissive:
         node: worker2 has SELINUX setting OK -> SELINUX = permissive........................................ OK
	 
## Example 5: output on an OpenShift platform (only doing the CMG checks):
    [vanopsta@centoc84-oc scripts]$ ./cpc_k8s_platform_checker_v21.12_uc.py -v

    Progress: [########################################] 6/6                                                                       

    Successful tests [4/6]:
     - check_CMG_CPU_pinning
     - check_CMG_HugePages
     - check_CMG_worker_nodes_ipvlan_interfaces
     - check_multus

    Failing tests    [2/6]:
     - check_CMG_worker_nodes_sriov_interfaces : mtu = 1500 (NOK: is NOT above: 8900)
     - check_CMG_worker_nodes_sysctl           : sysctl value: net.ipv4.udp_wmem_min = 4096 -> not set to: 1048576

    CPC platform checker report:
    ****************************
    CPC checker version:     version 21.12_UC
    Platform:                OpenShift
    K8s version:             Client Version: 4.9.4
                             Server Version: 4.9.4
    Start time:              2021-Dec-14 10:11:19

    -> check_CMG_CPU_pinning:
         node: m0 has cpuManagerPolicy: static............................................................... OK
         node: m1 has cpuManagerPolicy: static............................................................... OK
         node: m2 has cpuManagerPolicy: static............................................................... OK
         node: w1 has cpuManagerPolicy: static............................................................... OK
    -> check_CMG_HugePages:
         node: m0 has HugePages enabled -> HugePages_Total: 50............................................... OK
         node: m1 has HugePages enabled -> HugePages_Total: 50............................................... OK
         node: m2 has HugePages enabled -> HugePages_Total: 50............................................... OK
         node: w1 has HugePages enabled -> HugePages_Total: 50............................................... OK
    -> check_CMG_worker_nodes_ipvlan_interfaces:
         node: m0
           has interface: enp1s0 -> UP & RUNNING............................................................. OK
         node: m1
           has interface: enp1s0 -> UP & RUNNING............................................................. OK
         node: m2
           has interface: enp1s0 -> UP & RUNNING............................................................. OK
         node: w1
           has interface: enp1s0 -> UP & RUNNING............................................................. OK
    -> check_CMG_worker_nodes_sriov_interfaces:
         node: m0
           has interface: ens93f1 
               UP & RUNNING.................................................................................. OK
               mtu = 1500 (NOK: is NOT above: 8900).......................................................... FAILED
         node: m1
           has interface: ens93f1 
               UP & RUNNING.................................................................................. OK
               mtu = 1500 (NOK: is NOT above: 8900).......................................................... FAILED
         node: m2
           has interface: ens93f1 
               UP & RUNNING.................................................................................. OK
               mtu = 1500 (NOK: is NOT above: 8900).......................................................... FAILED
         node: w1
           has interface: ens93f1 
               UP & RUNNING.................................................................................. OK
               mtu = 1500 (NOK: is NOT above: 8900).......................................................... FAILED
    -> check_CMG_worker_nodes_sysctl:
         node: m0
           sysctl value: net.core.rmem_default = 212992 -> not set to: 1048576............................... FAILED
           sysctl value: net.core.rmem_max = 212992 -> not set to: 4194304................................... FAILED
           sysctl value: net.core.wmem_default = 212992 -> not set to: 1048576............................... FAILED
           sysctl value: net.core.wmem_max = 212992 -> not set to: 4194304................................... FAILED
           sysctl value: net.ipv4.tcp_rmem = 4096 87380 6291456 -> not set to: 187380 655360 6291456......... FAILED
           sysctl value: net.ipv4.udp_rmem_min = 4096 -> not set to: 1048576................................. FAILED
           sysctl value: net.ipv4.udp_wmem_min = 4096 -> not set to: 1048576................................. FAILED
           sysctl value: net.ipv6.conf.all.forwarding = 1.................................................... OK
         node: m1
           sysctl value: net.core.rmem_default = 212992 -> not set to: 1048576............................... FAILED
           sysctl value: net.core.rmem_max = 212992 -> not set to: 4194304................................... FAILED
           sysctl value: net.core.wmem_default = 212992 -> not set to: 1048576............................... FAILED
           sysctl value: net.core.wmem_max = 212992 -> not set to: 4194304................................... FAILED
           sysctl value: net.ipv4.tcp_rmem = 4096 87380 6291456 -> not set to: 187380 655360 6291456......... FAILED
           sysctl value: net.ipv4.udp_rmem_min = 4096 -> not set to: 1048576................................. FAILED
           sysctl value: net.ipv4.udp_wmem_min = 4096 -> not set to: 1048576................................. FAILED
           sysctl value: net.ipv6.conf.all.forwarding = 1.................................................... OK
         node: m2
           sysctl value: net.core.rmem_default = 212992 -> not set to: 1048576............................... FAILED
           sysctl value: net.core.rmem_max = 212992 -> not set to: 4194304................................... FAILED
           sysctl value: net.core.wmem_default = 212992 -> not set to: 1048576............................... FAILED
           sysctl value: net.core.wmem_max = 212992 -> not set to: 4194304................................... FAILED
           sysctl value: net.ipv4.tcp_rmem = 4096 87380 6291456 -> not set to: 187380 655360 6291456......... FAILED
           sysctl value: net.ipv4.udp_rmem_min = 4096 -> not set to: 1048576................................. FAILED
           sysctl value: net.ipv4.udp_wmem_min = 4096 -> not set to: 1048576................................. FAILED
           sysctl value: net.ipv6.conf.all.forwarding = 1.................................................... OK
         node: w1
           sysctl value: net.core.rmem_default = 212992 -> not set to: 1048576............................... FAILED
           sysctl value: net.core.rmem_max = 212992 -> not set to: 4194304................................... FAILED
           sysctl value: net.core.wmem_default = 212992 -> not set to: 1048576............................... FAILED
           sysctl value: net.core.wmem_max = 212992 -> not set to: 4194304................................... FAILED
           sysctl value: net.ipv4.tcp_rmem = 4096 87380 6291456 -> not set to: 187380 655360 6291456......... FAILED
           sysctl value: net.ipv4.udp_rmem_min = 4096 -> not set to: 1048576................................. FAILED
           sysctl value: net.ipv4.udp_wmem_min = 4096 -> not set to: 1048576................................. FAILED
           sysctl value: net.ipv6.conf.all.forwarding = 1.................................................... OK
    -> check_multus:
         node: m0 multus enabled............................................................................. OK
         node: m1 multus enabled............................................................................. OK
         node: m2 multus enabled............................................................................. OK
         node: w1 multus enabled............................................................................. OK

## More Info:

[`jan.van_opstal@nokia.com`](mailto:jan.van_opstal@nokia.com)    
