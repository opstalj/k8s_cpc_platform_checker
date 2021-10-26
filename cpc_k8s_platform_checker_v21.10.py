#!/usr/bin/env python3
#
# script to check whether  platform fulfills the pre-requirements to install 5G CPC CNFs: NRD, AMF, SMF/UPF
# possible platforms:
#   ncs  ->  NCS (Nokia Container Services platform)
#   os   ->  RedHat OpenShift
#   gcp  ->  Google Cloud Platform (Anthos)
#   eccd ->  Ericsson CCD
#
# comments: jan.van_opstal@nokia.com
#
# !! needs input file: CPC_checker_parms.py
#
#
# xx.x  : fetch exact anthos version
# 21.10 : add NRD performance checks (NRD R21.8R1)
#         add extra checks for CMG (CMG R21.8.R1) - sriov interfaces
# 21.9  : SW version control like the other CPC components
# 1.13  : add possibility to skip certain checks (define in CPC_checker_parms.py: checks_to_skip)
# 1.12  : SELinux not only for OpenShift & NCS -> but depends on OS = RHEL/CentOS of host OS
# 1.11  : SuSe linux -> specific check on SELINUX
# 1.10  : add Ericsson ECCD (eccd)
# 1.09  : CMM21.5 -> needs whereabouts plugin
# 1.07  : allow to skip a node or do checks only on 1x node
# 1.06  : check sctp
# 1.05  : add kernel.sched_rt_runtime + check_AMF_worker_nodes_transparent_hugepage_madvise check for AMF
# 1.04  : add nodeInfo
# 1.03  : matches a value which is in a list
# 1.02  : blabla
# 1.01  : all checks in 1x proc
# 0.09  : add NRD stuff
# 0.08  : add list of checks and allow to execute only 1x particular check
# 0.07  : AMF CPU pinning for gcp
# 0.06  : catch cmd/ssh error during Popen
# 0.05  : set KUBECONFIG variable
# 0.04  : allow script to run as non-root user
# 0.03  : simplify Popen call
# 0.02  : split off parameters to separate file -> CPC_checker_parms.py
# 0.01  : initial

# CPC_checker_parms.py changes:
###############################
# 21.10 : 
#  1) NEW:
#   run_checks_alphabetically=True              : allows to run the checks in alphabetical order
#   check_NRD_performance=True                  : check specific settings when NRD performance is needed
#   amf_host_interface_list=['bond0.101']       : check whether AMF IPVLAN interfaces are up and running (existance, state) 
#   amf_worker_node_rmem_max=4194304            : value to check rmem_max on the AMF nodes
#   amf_worker_node_wmem_max=4194304            : value to check rwem_max on the AMF nodes
#   cmg_worker_node_rmem_max=4194304            : value to check rmem_max on the CMG nodes
#   cmg_worker_node_wmem_max=4194304            : value to check rwem_max on the CMG nodes
#   cmg_worker_node_udp_rmem_min=1048576        : value to check udp_rmem_max on the CMG nodes
#   cmg_worker_node_udp_wmem_min=1048576        : value to check udp_rwem_max on the CMG nodes                                                  
#   cmg_sriov_interface_list=['eno5','eno6']    : check SRIOV interfaces on the CMG nodes (existance, state, mtu, VFs) 
#   cmg_sriov_interface_mtu_min=8900            : min mtu size value for CMG SRIOV interface
#   level4=9                                    : indentation when printing report level4
#  2) DEPRECATED:                               
#   worker_node_rmem_max=4194304                : replaced by amf_worker_node_rmem_max
#   worker_node_wmem_max=4194304                : replaced by amf_worker_node_wmem_max


import os
import sys
import time
import argparse
import subprocess
from subprocess import PIPE, Popen
import CPC_checker_parms
from CPC_checker_parms import *
import re

CPC_PLATFORM_CHECKER_VERSION = "version 21.10"

def CPC_report(indents,addToReport,status=True,info_value=''):
    global CPC_checker_report
    
    if indents==level1:
        CPC_checker_report+='-> '+addToReport+':\n'
    elif indents==level2:
        if status:
            if info_value != "":
                CPC_checker_report+=indents*' '+addToReport.ljust(dotline_length,'.')+' '+info_value+'\n'
            else:
                CPC_checker_report+=indents*' '+addToReport.ljust(dotline_length,'.')+' OK'+'\n'
        else:
            CPC_checker_report+=indents*' '+addToReport.ljust(dotline_length,'.')+' FAILED'+'\n'
    else: #level3
        CPC_checker_report+=indents*' '+addToReport.ljust(dotline_length-level3+level2,'.')+' '+info_value+'\n'

def do_the_check(applicant,cmd,criteria_ok,msg_ok,msg_nok,min_value=-1,max_value=-1,list_to_match=[],text_printValue='',printValue=False,rightStrip=False):

    # applicant:
    #   ['local'] -> only apply check on local host, else on list of nodes 
    # criteria_ok:
    #   'info returned not empty'           -> if the cmd returns something, then it means it is OK
    #   'above min value'                   -> info returned should NOT be lower than min value (equal is OK)
    #   'lower max value'                   -> info returned should NOT be bigger than max value (equal is OK)
    #   'matches value in list'             -> info returned should match one of the values of 'list_to_match'

    #print(' -> cmd: '+str(cmd)+'FFFFFFFFFFF')
    if applicant==['local']:
    # only run command locally:
        ### get value:
        my_info=get_Popen_info(cmd,rightStrip)
        if my_info == '': 
            CPC_report(level2,msg_nok,check_failed)
            return("NOK",msg_nok)
        else:
            #### if value has been returned and that was enough to regard it as OK:
            ###############################
            #### 'info returned not empty':
            ###############################
            if criteria_ok == 'info returned not empty':  
                if printValue:
                    CPC_report(level2,msg_ok+text_printValue+str(my_info))
                else:
                    CPC_report(level2,msg_ok)
                return("OK")                        
            #### check value is above MIN value:
            #######################
            #### 'above min value':
            #######################          
            elif criteria_ok == 'above min value':
                if int(my_info) < min_value:
                    CPC_report(level2,msg_nok,check_failed)
                    return("NOK",msg_nok)
                else:
                    if printValue:
                        CPC_report(level2,msg_ok+text_printValue+str(my_info))
                    else:
                        CPC_report(level2,msg_ok)            
                    return("OK")  
            #### check value is below MAX value:
            #######################
            #### 'lower max value':
            #######################          
            elif criteria_ok == 'lower max value':
                if int(my_info) > max_value:
                    CPC_report(level2,msg_nok,check_failed)
                    return("NOK",msg_nok)
                else:
                    if printValue:
                        CPC_report(level2,msg_ok+text_printValue+str(my_info))
                    else:
                        CPC_report(level2,msg_ok)            
                    return("OK")                    
            #### if value returned matches one of the possible required values:
            #############################
            #### 'matches value in list':
            #############################            
            elif criteria_ok == 'matches value in list':
                if str(my_info) not in list_to_match:      
                    CPC_report(level2,msg_nok,check_failed)
                    return("NOK",msg_nok)
                else:
                    if printValue:
                        CPC_report(level2,msg_ok+text_printValue+str(my_info))
                    else:
                        CPC_report(level2,msg_ok)            
                    return("OK")          
           #### check value is above MIN value and lower than MAX value: TODO                                                     
    else: 
    # list of workers
        global_check_OK=True
        for i in range(0, len(applicant)):
            #### get value:
            if login_worker_nodes_with_SSHKEY:
                my_info=get_Popen_info('ssh -q -i '+sshkey+' '+worker_node_username+'@'+str(applicant[i])+' '+cmd,rightStrip)
            else:
                if skip_username_worker_node_to_ssh:        
                    my_info=get_Popen_info('ssh -q '+str(applicant[i])+' '+cmd,rightStrip)
                else:
                    my_info=get_Popen_info('ssh -q '+worker_node_username+'@'+str(applicant[i])+' '+cmd,rightStrip)
            #print(' -> my info:',str(my_info)+'FFFFFFF')
            #### check value on ERROR:
            if my_info=="" or my_info.startswith("ERROR"):
                global_check_OK=False
                if my_info.startswith("ERROR:"):
                    failure_reason = str(' '+my_info)
                elif my_info=="ERROR":
                    failure_reason = ' -> SSH error occurred?'
                else:
                    failure_reason = msg_nok
                CPC_report(level2,"node: "+str(applicant[i])+' '+failure_reason,check_failed)
                if not create_report:
                    return("NOK","node: "+str(applicant[i])+' '+failure_reason)
            else:
                #### if value has been returned and that was enough to regard it as OK:
                ###############################
                #### 'info returned not empty':
                ###############################                
                if criteria_ok == 'info returned not empty': 
                    if printValue:
                        CPC_report(level2,"node: "+str(applicant[i])+' '+msg_ok+text_printValue+str(my_info))
                    else:
                        CPC_report(level2,"node: "+str(applicant[i])+' '+msg_ok)
                #### check value is above MIN value:
                #######################
                #### 'above min value':
                #######################                 
                elif criteria_ok == 'above min value':
                    if int(my_info) < min_value:
                        global_check_OK=False
                        if printValue:
                            CPC_report(level2,"node: "+str(applicant[i])+' '+msg_nok+text_printValue+str(my_info),check_failed)
                        else:
                            CPC_report(level2,"node: "+str(applicant[i])+' '+msg_nok,check_failed)
                        if not create_report:
                            return("NOK","node: "+str(applicant[i])+' '+msg_nok)
                    else:
                        if printValue:
                            CPC_report(level2,"node: "+str(applicant[i])+' '+msg_ok+text_printValue+str(my_info))
                        else:
                            CPC_report(level2,"node: "+str(applicant[i])+' '+msg_ok)
                #### check value is below MAX value:
                #######################
                #### 'lower max value':
                #######################          
                elif criteria_ok == 'lower max value':
                    if int(my_info) > max_value:
                        global_check_OK=False
                        if printValue:
                            CPC_report(level2,"node: "+str(applicant[i])+' '+msg_nok+text_printValue+str(my_info),check_failed)
                        else:
                            CPC_report(level2,"node: "+str(applicant[i])+' '+msg_nok,check_failed)
                        if not create_report:
                            return("NOK","node: "+str(applicant[i])+' '+msg_nok)
                    else:
                        if printValue:
                            CPC_report(level2,"node: "+str(applicant[i])+' '+msg_ok+text_printValue+str(my_info))
                        else:
                            CPC_report(level2,"node: "+str(applicant[i])+' '+msg_ok)                           
                #### if value returned matches one of the possible required values:
                #############################
                #### 'matches value in list':
                #############################                
                elif criteria_ok == 'matches value in list':
                    if str(my_info) not in list_to_match:
                        global_check_OK=False
                        if printValue:
                            CPC_report(level2,"node: "+str(applicant[i])+' '+msg_nok+text_printValue+str(my_info),check_failed)
                        else:
                            CPC_report(level2,"node: "+str(applicant[i])+' '+msg_nok,check_failed)
                        if not create_report:
                            return("NOK","node: "+str(applicant[i])+' '+msg_nok)
                    else:
                        if printValue:
                            CPC_report(level2,"node: "+str(applicant[i])+' '+msg_ok+text_printValue+str(my_info))
                        else:
                            CPC_report(level2,"node: "+str(applicant[i])+' '+msg_ok)                
                #### check value is above MIN value and lower than MAX value: TODO
        if global_check_OK:
            return('OK')
        else:
            return("NOK",msg_nok)    

def check_test():
   
    apply_to=list_AMF_workers
    cmd_to_exec='"cat /etc/selinux/config|egrep \'^SELINUX=\'|cut -d\'=\' -f2"'
    criteria_ok='matches value in list'
    msg_ok='has SELINUX setting OK'
    to_printValue=' -> SELINUX = '
    matchOneOfTheseValues=['permissive','disabled']
    msg_nok='does not have SELINUX=permissive or disabled' 
   
    # if HugePage_Total is above 0 (eg: 1), we can assume HugePages have been enabled
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,list_to_match=matchOneOfTheseValues,text_printValue=to_printValue,printValue=True,rightStrip=True)
    return(check_my_test)                   
    
def get_Popen_info(cmd,rightStrip=False):
    
    #print(' -> cmd in Popen:'+str(cmd)+'FFFFFFFFFFFF')
    # run subprocess Popen:
    my_get_info = Popen (cmd,shell=True, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out,err=my_get_info.communicate()
    # need to check the return code of the command
    # https://tldp.org/LDP/abs/html/exitcodes.html
    # 0 = OK
    # 1 = catch all errors, but it can also be an empty return ... so if it is 1, I will check the output
    #     if empty -> still a good reply
    #print(' -> out:'+str(out)+'FFFFFFF')
    #print(' -> err:'+str(err)+'FFFFFFF')
    if my_get_info.returncode != 0 and my_get_info.returncode != 1:
        return('ERROR')
    # an empty reply is ok
    if my_get_info.returncode == 1:
        if out.decode('utf-8').rstrip() != '':
            return('ERROR')
        if err.decode('utf-8').rstrip() != '':
            return('ERROR: '+err.decode('utf-8').rstrip())

    if rightStrip:
        return(out.decode('utf-8').rstrip())
    else:
        return(out.decode('utf-8'))
    
def check_istio():
    # check istio-system namespace:
    #istio_system = Popen("kubectl get svc -n "+namespace_istio_system+" 2>/dev/null")
    #output_istio_system = istio_system.stdout.read().decode('utf-8')
    
    my_info=get_Popen_info(cmd_start_kubectl+" get svc -n "+namespace_istio_system+" 2>/dev/null")
    if my_info == "":
        CPC_report(level2,"istio-system namespace "+namespace_istio_system+" missing",check_failed)
        return("NOK","istio-system namespace "+namespace_istio_system+" missing")    
    else:
        CPC_report(level2,"istio-system namespace '"+namespace_istio_system+"' exists")        
  
    # check istio-ingressgateway:
    my_info=get_Popen_info(cmd_start_kubectl+" describe svc -n "+namespace_istio_system+" "+podname_istio_ingressgateway)
    if my_info == "": 
        CPC_report(level2,"istio-ingressgateway pod '"+podname_istio_ingressgateway+"' missing in "+namespace_istio_system,check_failed)
        return("NOK","istio-ingressgateway pod  '"+podname_istio_ingressgateway+"' missing in "+namespace_istio_system+" namespace")
    else:
        CPC_report(level2,"istio-ingressgateway pod '"+podname_istio_ingressgateway+"' exists in "+namespace_istio_system+" namespace")
          
    # check ior_enabled flag:
    # kubectl describe pod istio-ingressgateway-bzrsz  -n istio-system |grep ior_enabled
          
    ###### BEGIN: for OpenShift only ######
    if target_platform == 'os':
        # istio-installation check ior_enabled set for istio-ingressgateway
        # more precise:
        # kubectl get ServiceMeshControlPlane -n istio-system -o yaml |grep -v 'f:appliedValues'|grep -A1000 appliedValues|grep -A1000 istio-ingressgateway|grep -B1000 global
        my_info=get_Popen_info(cmd_start_kubectl+" get ServiceMeshControlPlane -n "+namespace_istio_system+" -o yaml |grep 'ior_enabled: true' 2>/dev/null")
        if my_info == "":
            CPC_report(level2,"istio-ingressgateway flag ior_enabled not set to true",check_failed)
            return("NOK","istio-ingressgateway flag ior_enabled not set to true")
        else:
            CPC_report(level2,"istio-ingressgateway flag ior_enabled flag set to true")

        # check istio version in ServiceMesh:
        # kubectl get csv -n openshift-operators `kubectl get csv -n openshift-operators |grep servicemeshoperator|awk '{print $1}'` -o custom-columns=vers:spec.version|tail -1
        my_info=get_Popen_info(cmd_start_kubectl+" get csv -n openshift-operators `kubectl get csv -n openshift-operators |grep servicemeshoperator|awk '{print $1}'` -o custom-columns=vers:spec.version|tail -1",rightStrip=True)
        if my_info == "":
            CPC_report(level2,"could not find the Red Hat Service Mesh version",check_failed)
        else:
            CPC_report(level2,"Red Hat Service Mesh version: ",info_value=str(my_info))
        
        # kubectl rsh -n openshift-operators `kubectl get pods -n openshift-operators |grep istio-operator-|awk '{print $1}'` env | grep ISTIO_VERSION|cut -d'=' -f2
        my_info=get_Popen_info(cmd_start_kubectl+" rsh -n openshift-operators `kubectl get pods -n openshift-operators |grep istio-operator-|awk '{print $1}'` env | grep ISTIO_VERSION|cut -d'=' -f2",rightStrip=True)
        if my_info == "":
            CPC_report(level2,"could not read istio version in istio-operator POD",check_failed)
        else:
            CPC_report(level2,"istio version in istio-operator POD: ",info_value=str(my_info))
            
        # check whether nrd has got a ServiceMeshMemberRoll (if not, the istio envoy will not be injected into the nrd pod)
        # kubectl get ServiceMeshMemberRoll -n istio-system -o yaml |grep -e '- nrd'
        # or: kubectl get ServiceMeshMemberRoll -n istio-system -o yaml |sed -n '/^  spec/,/status/p'|grep nrd
        my_info=get_Popen_info(cmd_start_kubectl+" get ServiceMeshMemberRoll -n "+namespace_istio_system+" -o yaml |sed -n '/^  spec/,/status/p'|grep nrd")
        if my_info == "":
            CPC_report(level2,"NRD: no entry for nrd in the ServiceMeshMemberRoll in namespace "+namespace_istio_system,check_failed)
            return("NOK","NRD: no entry for nrd in the ServiceMeshMemberRoll in namespace "+namespace_istio_system)
        else:
            CPC_report(level2,"NRD: entry present in the ServiceMeshMemberRoll in namespace "+namespace_istio_system)            
    ###### END: for OpenShift only ######

    if check_nrd_istio:
        if create_report:
            # is istio-ingressgateway setup as NodePort or ClusterIp?
            # kubectl get svc istio-ingressgateway -n istio-system -o custom-columns=type:.spec.type |grep NodePort
            # kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.spec.type}'
            my_info=get_Popen_info(cmd_start_kubectl+" get svc "+podname_istio_ingressgateway+" -n "+namespace_istio_system+" -o custom-columns=type:.spec.type |tail -1",rightStrip=True)
            CPC_report(level3,"NRD: istio-ingressgateway service created as type: ",info_value=str(my_info))
            
            # on which port are the worker nodes listening for http2 messages?
            # kubectl get svc istio-ingressgateway -n istio-system -o yaml |grep -A3 "name: http2"|grep nodePort|tr ' ' '\n' | tail -1
            # IP   -> kubectl get po -l istio=ingressgateway -n istio-system -o jsonpath='{.items[0].status.hostIP}'
            # PORT -> kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.spec.ports[?(@.name=="http2")].nodePort}'
            # 
            # grep more http2 ports: kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{range .spec.ports[*]}{.name}{" "}{.nodePort}{"\n"}{end}' | grep http2     

            my_info=get_Popen_info(cmd_start_kubectl+" get service "+podname_istio_ingressgateway+' -n '+namespace_istio_system+' -o jsonpath=\'{range .spec.ports[*]}{.name}{" "}{.nodePort}{"\\n"}{end}\' | grep http2')
            if my_info == '':
                CPC_report(level3,"NRD: "+podname_istio_ingressgateway+" is NOT listening for http2 traffic !! ",info_value='FAILED')
            else:
                CPC_report(level3,"NRD: "+podname_istio_ingressgateway+" is listening for http2 traffic on: ",info_value=str(my_info).replace('\n',',').rstrip(','))          
            
            if target_platform == 'os':
                # which router hostname got created in the openshift router in namespace istio-system for nrd:
                # kubectl get routes -n istio-system
                my_info=get_Popen_info(cmd_start_kubectl+" get routes -n "+namespace_istio_system+"|egrep '^"+namespace_nrd+"-nrd-'| awk '{print $2}'",rightStrip=True)
                CPC_report(level3,"NRD: host kubectl router created in istio-system for nrd: ",info_value=str(my_info))            
        
        return('OK')

def check_glusterFS():
    apply_to=['local']
    cmd_to_exec=cmd_start_kubectl+"get storageclass -A|grep glusterfs-storageclass  2>/dev/null"
    criteria_ok='info returned not empty'
    msg_ok='glusterFS present in storageclass'
    msg_nok='glusterFS is NOT present in storageclass'
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok)
    return(check_my_test)

def check_cephFS():
    apply_to=['local']
    cmd_to_exec=cmd_start_kubectl+"get storageclass -A|grep cephfs  2>/dev/null"
    criteria_ok='info returned not empty'
    msg_ok='cephfs present in storageclass'
    msg_nok='cephfs is NOT present in storageclass'
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok)
    return(check_my_test)
    
def check_multus():
    # check: sudo ls /etc/cni/net.d |grep multus
    # alternative check: kubectl get pods -A |grep -i multus

    # do ssh to worker and check command
    apply_to=list_workers
    cmd_to_exec='"sudo ls /etc/cni/net.d |grep multus"'
    criteria_ok='info returned not empty'
    msg_ok='multus enabled'
    msg_nok='does not seem to have multus installed/enabled'
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok)
    return(check_my_test)
 
def check_NRD_labels():
    #print("check_NRD_labels")
    if len(list_NRD_workers) == 0:
        CPC_report(level2,'There are no nodes labeled: '+label_nrdnode,check_failed) 
        return('NOK','There are no nodes labeled: '+label_nrdnode)
    else:
        CPC_report(level2,'There are '+str(len(list_NRD_workers))+' nodes labeled with: '+label_nrdnode) 
        return('OK')
 
def check_NRD_docker_images():
    #print("check_NRD_docker_images")
    time.sleep(0.5)
    return('OK')

def check_NRD_performance_tcp_slow_start():

    # NRD R21.8.R1:
    # to ensure NRD performance:    net.ipv4.tcp_slow_start_after_idle = 0
    apply_to=list_NRD_workers
    cmd_to_exec='"sudo sysctl -a |grep net.ipv4.tcp_slow_start_after_idle |awk \'{print \$3}\'"'
    criteria_ok='matches value in list'
    msg_ok='has correct setting'
    to_printValue=' -> value = '
    matchOneOfTheseValues=['-1']
    msg_nok='does not have net.ipv4.tcp_slow_start_after_idle = 0'          
   
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,list_to_match=matchOneOfTheseValues,text_printValue=to_printValue,printValue=True,rightStrip=True)
    return(check_my_test)

def check_NRD_performance_nf_conntrack_tcp_timeout_unacknowledged():

    # NRD R21.8.R1:
    # to ensure NRD performance:    net.netfilter.nf_conntrack_tcp_timeout_unacknowledged = 10
    apply_to=list_NRD_workers
    cmd_to_exec='"sudo sysctl -a |grep net.netfilter.nf_conntrack_tcp_timeout_unacknowledged |awk \'{print \$3}\'"'
    criteria_ok='matches value in list'
    msg_ok='has correct setting'
    to_printValue=' -> value = '
    matchOneOfTheseValues=['10']
    msg_nok='does not have net.netfilter.nf_conntrack_tcp_timeout_unacknowledged = 10'          
   
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,list_to_match=matchOneOfTheseValues,text_printValue=to_printValue,printValue=True,rightStrip=True)
    return(check_my_test)

def check_NRD_performance_nf_conntrack_tcp_timeout_max_retrans():

    # NRD R21.8.R1:
    # to ensure NRD performance:    net.netfilter.nf_conntrack_tcp_timeout_max_retrans = 10
    apply_to=list_NRD_workers
    cmd_to_exec='"sudo sysctl -a |grep net.netfilter.nf_conntrack_tcp_timeout_max_retrans |awk \'{print \$3}\'"'
    criteria_ok='matches value in list'
    msg_ok='has correct setting'
    to_printValue=' -> value = '
    matchOneOfTheseValues=['10']
    msg_nok='does not have net.netfilter.nf_conntrack_tcp_timeout_max_retrans = 10'          
   
    #check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,min_value=worker_node_rmem_max,text_printValue=to_printValue,printValue=True,rightStrip=True)
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,list_to_match=matchOneOfTheseValues,text_printValue=to_printValue,printValue=True,rightStrip=True)
    return(check_my_test)
 
def check_AMF_CPU_pinning():

    #### NCS or GCP ####
    if target_platform  in ['ncs','gcp','eccd']:    
        # check: sudo cat /var/lib/kubelet/cpu_manager_state |grep -- '"policyName":"static"'
        # -> ps -ef|grep kubelet     will give you the config file used for kubelet, eg: --config=/var/lib/kubelet/config.yaml    
        apply_to=list_AMF_workers
        cmd_to_exec='"sudo cat /var/lib/kubelet/cpu_manager_state |grep static"'
        criteria_ok='info returned not empty'
        msg_ok='has policyName: static'
        msg_nok='does not have policyName: static'
    #### OpenShift ####
    if target_platform == 'os':
        # check: https://docs.openshift.com/container-platform/4.5/nodes/nodes/nodes-nodes-managing.html
        apply_to=['local']
        cmd_to_exec=cmd_start_kubectl+" get machineconfigpool --show-labels|grep worker|grep cpumanager-enabled"
        criteria_ok='info returned not empty'        
        msg_ok='cpumanager-enabled set in machineconfigpool'
        msg_nok='cpu pinning NOK -> no cpu-manager on the worker nodes?'
        
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok)
    return(check_my_test)

def check_AMF_whereabouts_plugin_installed():
    # this is a pre-requirement from CMM21.5 onwards:

    # apply_to=['local']
    # cmd_to_exec=cmd_start_kubectl+"get pods -A | grep -i whereabouts"
    # criteria_ok='info returned not empty'
    # msg_ok='The whereabouts plugin has been installed'
    # msg_nok='The whereabouts plugin seems NOT installed'
    # check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok)
    # return(check_my_test)
    
    # also check:
    # k get crds -n kube-system |grep -i whereabout
    # ippools.whereabouts.cni.cncf.io                          2021-07-11T19:40:42Z
    # overlappingrangeipreservations.whereabouts.cni.cncf.io   2021-09-28T14:35:33Z    

    my_info=get_Popen_info(cmd_start_kubectl+" get pods -A | grep -i whereabouts 2>/dev/null")
    if my_info == "":
        CPC_report(level2,"whereabouts seems not installed",check_failed)
        return("NOK","whereabouts seems not installed")    
    else:
        CPC_report(level2,"whereabout pods exist")

    # check whereabout crds:
    # 1) ippools
    # 2) overlappingrangeipreservations
    # 3) ip-reconciler
    
    my_info=get_Popen_info(cmd_start_kubectl+" get crds -n kube-system |grep ippools.whereabouts 2>/dev/null")
    if my_info == "":
        CPC_report(level2,"whereabouts crd: ippools.whereabouts.cni.cncf.io seems not installed",check_failed)
        return("NOK","crd: ippools.whereabouts.cni.cncf.io seems not installed")    
    else:
        CPC_report(level2,"whereabouts crd: ippools.whereabouts.cni.cncf.io exists")    
        
    my_info=get_Popen_info(cmd_start_kubectl+" get crds -n kube-system |grep overlappingrangeipreservations.whereabouts 2>/dev/null")
    if my_info == "":
        CPC_report(level2,"whereabouts crd: overlappingrangeipreservations.whereabouts.cni.cncf.io seems not installed",check_failed)
        return("NOK","crd: overlappingrangeipreservations.whereabouts.cni.cncf.io seems not installed")    
    else:
        CPC_report(level2,"whereabouts crd: overlappingrangeipreservations.whereabouts.cni.cncf.io exists")        

    my_info=get_Popen_info(cmd_start_kubectl+" get crds -n kube-system |grep ip-reconciler 2>/dev/null")
    if my_info == "":
        CPC_report(level2,"whereabouts crd: ip-reconciler-job seems not installed",check_failed)
        return("NOK","crd: ip-reconciler-job seems not installed")    
    else:
        CPC_report(level2,"whereabouts crd: ip-reconciler exists") 

    return("OK")    
        
def check_AMF_worker_nodes_selinux_permissive():
    # check: selinux = Popen("ssh -q -i " + NCSKEY + " cloud-user@" + i + " 'sudo  cat /etc/selinux/config|grep SELINUX=permissive'")
    #
    # SELINUX=permissive or SELINUX=disabled        -> both are OK

    # TO DO: Suse linux
    #           eccd@worker-pool1-4xpr66hn-ccd0-mmt3-tenant1-testing:/etc/selinux> sudo sestatus -v
    #           SELinux status:                 disabled
    #           eccd@worker-pool1-4xpr66hn-ccd0-mmt3-tenant1-testing:/etc/selinux> cat /etc/os-release 
    #           NAME="SLES"
    #           VERSION="15-SP1"
    #           VERSION_ID="15.1"
    #           PRETTY_NAME="SUSE Linux Enterprise Server 15 SP1"
    #   

    # only check AMF worker nodes:
    apply_to=list_AMF_workers
    # if OS on worker node = SuSe linux, then the cmd_to_exec looks different than on Red Hat:
    # kubectl get node worker-pool1-4xpr66hn-ccd0-mmt3-tenant1-testing -o custom-columns=NAME:.metadata.name,OSImage:.status.nodeInfo.osImage |grep -i 'suse linux'
    # for now, check AMF worker0 (assumption is that all worker nodes have the same OS)
    cmd=cmd_start_kubectl+'get node '+list_AMF_workers[0]+' -o custom-columns=NAME:.metadata.name,OSImage:.status.nodeInfo.osImage |grep -i "suse linux"'
    my_nodeInfo=get_Popen_info(cmd)    
    if my_nodeInfo == '':
        cmd_to_exec='"cat /etc/selinux/config|egrep \'^SELINUX=\'|cut -d\'=\' -f2"'
    else: # SuSe Linux
        cmd_to_exec='sudo sestatus -v|awk \'{print $3}\''
    criteria_ok='matches value in list'
    msg_ok='has SELINUX setting OK'
    to_printValue=' -> SELINUX = '
    matchOneOfTheseValues=['permissive','disabled']
    msg_nok='does not have SELINUX='+ " or ".join(matchOneOfTheseValues) 
   
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,list_to_match=matchOneOfTheseValues,text_printValue=to_printValue,printValue=True,rightStrip=True)
    return(check_my_test)
            
def check_AMF_worker_nodes_ipv6_enabled():
    # check: lsmod |grep 'ipv6'
    # alternative check: test -f /proc/net/if_inet6 && echo "Running kernel is IPv6 ready"

    apply_to=list_AMF_workers
    cmd_to_exec='"sudo lsmod |grep ipv6"'
    criteria_ok='info returned not empty'
    msg_ok='has ipv6 enabled in its kernel'
    msg_nok='does not have ipv6 enabled in its kernel'
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok)
    return(check_my_test)

def check_AMF_worker_nodes_sctp_enabled():
    # Check: lsmod | grep sctp
    # ?? might also need to check whether SCTP is not blacklisted in:
    #
    # do not blacklist SCTP:
    #   -> following files should not be present:
    #             /etc/modprobe.d/sctp-blacklist.conf
    #             /etc/modprobe.d/sctp_diag-blacklist.conf

    apply_to=list_AMF_workers
    #cmd_to_exec='"sudo lsmod |grep sctp"'
    cmd_to_exec='"sudo modprobe sctp;sudo lsmod |grep sctp"'
    criteria_ok='info returned not empty'
    msg_ok='has sctp enabled in its kernel'
    msg_nok='does not have sctp enabled in its kernel'
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok)
    return(check_my_test)
      
def check_AMF_worker_nodes_ipsec_enabled():
    # check: lsmod | grep -i xfrm
    
    # NOTE: only needed for 4G LI ... not for 5G LI
    apply_to=list_AMF_workers
    cmd_to_exec='"sudo lsmod | grep -i xfrm"'
    criteria_ok='info returned not empty'
    msg_ok='has ipsec enabled in its kernel'
    msg_nok='does not have ipsec enabled in its kernel'
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok)
    return(check_my_test)        
    
def check_AMF_worker_nodes_rmem_max_socket_buffer():

    # CMM needs: 4GB of socket buffer size
    # net.core.rmem_max => Specifies the maximum size (in bytes) of the window for receiving TCP data.
    # net.core.wmem_max => Specifies the maximum size (in bytes) of the window for transmitting TCP data. 
    # 
    # to set: echo "net.core.rmem_max=4194304" | tee -a /etc/sysctl.conf -> check: sudo sysctl -a |grep net.core.rmem_max |awk '{print $3}'
    #         echo "net.core.wmem_max=4194304" | tee -a /etc/sysctl.conf -> check sudo sysctl -a |grep net.core.wmem_max |awk '{print $3}'
    apply_to=list_AMF_workers
    cmd_to_exec='"sudo sysctl -a |grep net.core.rmem_max |awk \'{print \$3}\'"'
    criteria_ok='lower max value'
    msg_ok='net.core.rmem_max OK'
    to_printValue=' -> net.core.rmem_max = '
    msg_nok='does not have net.core.rmem_max below: '+str(amf_worker_node_rmem_max)          
   
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,max_value=amf_worker_node_rmem_max,text_printValue=to_printValue,printValue=True,rightStrip=True)
    return(check_my_test)

def check_AMF_worker_nodes_wmem_max_socket_buffer():

    # CMM needs: 4GB of socket buffer size
    # net.core.rmem_max => Specifies the maximum size (in bytes) of the window for receiving TCP data.
    # net.core.wmem_max => Specifies the maximum size (in bytes) of the window for transmitting TCP data. 
    # 
    # to set: echo "net.core.rmem_max=4194304" | tee -a /etc/sysctl.conf -> check: sudo sysctl -a |grep net.core.rmem_max |awk '{print $3}'
    #         echo "net.core.wmem_max=4194304" | tee -a /etc/sysctl.conf -> check sudo sysctl -a |grep net.core.wmem_max |awk '{print $3}'
    apply_to=list_AMF_workers
    cmd_to_exec='"sudo sysctl -a |grep net.core.wmem_max |awk \'{print \$3}\'"'
    criteria_ok='lower max value'
    msg_ok='net.core.wmem_max OK'
    to_printValue=' -> net.core.wmem_max = '
    msg_nok='does not have net.core.wmem_max below: '+str(amf_worker_node_wmem_max)          
   
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,max_value=amf_worker_node_wmem_max,text_printValue=to_printValue,printValue=True,rightStrip=True)
    return(check_my_test)  

def check_AMF_worker_nodes_kernel_sched_rt_runtime():

    # For Redhat or Centos: 
    # kernel.sched_rt_runtime_us = -1
    # check: sudo sysctl -a |grep kernel.sched_rt_runtime_us |awk '{print $3}'

    # only check AMF worker nodes:
    apply_to=list_AMF_workers
    cmd_to_exec='"sudo sysctl -a |grep kernel.sched_rt_runtime_us |awk \'{print \$3}\'"'
    criteria_ok='matches value in list'
    msg_ok='has correct setting'
    to_printValue=' -> kernel.sched_rt_runtime_us = '
    matchOneOfTheseValues=['-1']
    msg_nok='does not have kernel.sched_rt_runtime_us = -1' 
   
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,list_to_match=matchOneOfTheseValues,text_printValue=to_printValue,printValue=True,rightStrip=True)
    return(check_my_test)  
 
def check_AMF_worker_nodes_transparent_hugepage_madvise():
    # cat /sys/kernel/mm/transparent_hugepage/enabled |grep -Po '\[\K[^]]*'
    
    # only check AMF worker nodes:
    apply_to=list_AMF_workers
    cmd_to_exec='"cat /sys/kernel/mm/transparent_hugepage/enabled |grep -Po \'\[\K[^]]*\'"'
    criteria_ok='matches value in list'
    msg_ok='has correct setting'
    to_printValue=' -> transparent_hugepage = '
    matchOneOfTheseValues=['madvise']
    msg_nok='does not have transparent_hugepage = '+ " or ".join(matchOneOfTheseValues)
   
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,list_to_match=matchOneOfTheseValues,text_printValue=to_printValue,printValue=True,rightStrip=True)
    return(check_my_test)

def check_AMF_worker_nodes_docker_msgqueue_unlimited():
    # Issue: AMF necc's do not become healthy if CMG OAM/LB's co-exist on worker node (on AMF remoted.service in FAILED state)
    #
    # docker:       'sudo cat /etc/systemd/system/multi-user.target.wants/docker.service |grep LimitMSGQUEUE=infinity'
    #
    # containerd:   'sudo cat /etc/systemd/system/multi-user.target.wants/containerd.service |grep LimitMSGQUEUE=infinity'
    #               'sudo cat /etc/systemd/system/containerd.service |grep LimitMSGQUEUE=infinity'
    #                         

    # only check AMF worker nodes:
    apply_to=list_AMF_workers
    cmd_to_exec='"sudo cat /etc/systemd/system/multi-user.target.wants/docker.service |grep LimitMSGQUEUE=infinity"'
    criteria_ok='info returned not empty'
    msg_ok='has LimitMSGQUEUE=infinity OK'
    msg_nok='does not have LimitMSGQUEUE=infinity' 
   
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok)
    return(check_my_test)

def check_AMF_worker_nodes_containerd_msgqueue_unlimited():
    # Issue: AMF necc's do not become healthy if CMG OAM/LB's co-exist on worker node (on AMF remoted.service in FAILED state)
    #
    # docker:       'sudo cat /etc/systemd/system/multi-user.target.wants/docker.service |grep LimitMSGQUEUE=infinity'
    #
    # containerd:   'sudo cat /etc/systemd/system/multi-user.target.wants/containerd.service |grep LimitMSGQUEUE=infinity'
    #               'sudo cat /etc/systemd/system/containerd.service |grep LimitMSGQUEUE=infinity'
    #                         

    # only check AMF worker nodes:
    apply_to=list_AMF_workers
    cmd_to_exec='"sudo cat /etc/systemd/system/multi-user.target.wants/containerd.service |grep LimitMSGQUEUE=infinity"'
    criteria_ok='info returned not empty'
    msg_ok='has LimitMSGQUEUE=infinity OK'
    msg_nok='does not have LimitMSGQUEUE=infinity' 
   
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok)
    return(check_my_test)

def check_AMF_worker_nodes_ipvlan_interfaces():

    # errors: interface does not exist, or state is not UP
    # apply_to=list_AMF_workers
    # for i in range(0, len(amf_host_interface_list)):
        # cmd_to_exec='"sudo /usr/sbin/ifconfig "' + amf_host_interface_list[i] + '" |grep \'UP,BROADCAST,RUNNING\'"'
        # criteria_ok='info returned not empty'
        # msg_ok='has interface: '+ amf_host_interface_list[i] + " UP & RUNNING"
        # msg_nok='does not have interface: ' + amf_host_interface_list[i] + " UP & RUNNING"
        # check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok)
    # return(check_my_test)    

    global CPC_checker_report  

    global_check_OK=True      

    if amf_host_interface_list:
        for i in range(0, len(list_AMF_workers)):
            CPC_checker_report+=level2*' '+"node: "+str(list_AMF_workers[i])+'\n'
            #### get value:        
            for interface in range(0, len(amf_host_interface_list)):
                # check 1: interface up and running?
                ####################################
                #cmd_to_exec='"sudo /usr/sbin/ifconfig "' + cmg_sriov_interface_list[interface] + '" |grep \'UP,BROADCAST,RUNNING\'"'
                cmd_to_exec='"sudo /usr/sbin/ifconfig "' + amf_host_interface_list[interface]
                if login_worker_nodes_with_SSHKEY:
                    my_info=get_Popen_info('ssh -q -i '+sshkey+' '+worker_node_username+'@'+str(list_AMF_workers[i])+' '+cmd_to_exec,True)
                else:
                    if skip_username_worker_node_to_ssh:        
                        my_info=get_Popen_info('ssh -q '+str(list_AMF_workers[i])+' '+cmd_to_exec,True)
                    else:
                        my_info=get_Popen_info('ssh -q '+worker_node_username+'@'+str(list_AMF_workers[i])+' '+cmd_to_exec,True)
                #print(' -> my info:',str(my_info)+'FFFFFFF')
                if my_info.startswith("ERROR:"):
                    global_check_OK=False
                    failure_reason = str(my_info)
                    CPC_checker_report+=level3*' '+failure_reason.ljust(dotline_length-level3+level2,'.')+' FAILED\n'
                    if not create_report:
                        return("NOK","node: "+str(list_AMF_workers[i])+' '+failure_reason)                
                elif my_info=="ERROR":
                    global_check_OK=False
                    failure_reason = ' -> SSH error occurred?'
                    CPC_checker_report+=level3*' '+failure_reason.ljust(dotline_length-level3+level2,'.')+' FAILED\n'
                    if not create_report:
                        return("NOK","node: "+str(list_AMF_workers[i])+' '+failure_reason)
                else:
                    # check whether interface is UP and RUNNING:
                    if not "UP,BROADCAST,RUNNING" in my_info:
                        failure_reason = 'does not have interface: ' + amf_host_interface_list[interface] + " UP & RUNNING"
                        global_check_OK=False
                        CPC_checker_report+=level3*' '+failure_reason.ljust(dotline_length-level3+level2,'.')+' FAILED\n'
                        if not create_report:
                            return("NOK","node: "+str(list_AMF_workers[i])+' '+failure_reason)
                    else:
                        # sriov interface is up and running
                        msg_ok = 'has interface: ' + amf_host_interface_list[interface]+' -> UP & RUNNING'
                        CPC_checker_report+=level3*' '+msg_ok.ljust(dotline_length-level3+level2,'.')+' OK\n'   
    else:
        global_check_OK=False
        failure_reason="amf_host_interface_list is empty in CPC_checker_parms.py"
        CPC_report(level2,failure_reason,check_failed)
        if not create_report:
            return("NOK",failure_reason)        
            
    if global_check_OK:
        return('OK')
    else:
        return("NOK",failure_reason)
    
def check_worker_node_udp_tnl_segmentation_off():

    # setting when using GCP + Intel NICs + Cillium CNI (eg: Telenet)

    apply_to=list_workers
    cmd_to_exec='ethtool -k bond0 |grep "tx-udp_tnl-segmentation: "|awk \'{printf $2}\''
    criteria_ok='matches value in list'
    msg_ok='has correct setting'
    to_printValue=' -> tx-udp_tnl-segmentation: '
    matchOneOfTheseValues=['off']
    msg_nok='does not have tx-udp_tnl-segmentation: '+ " or ".join(matchOneOfTheseValues)

    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,list_to_match=matchOneOfTheseValues,text_printValue=to_printValue,printValue=True,rightStrip=True)
    return(check_my_test)

def check_worker_node_udp_tnl_csum_off():

    # setting when using GCP + Intel NICs + Cillium CNI (eg: Telenet)

    apply_to=list_workers
    cmd_to_exec='ethtool -k bond0 |grep "tx-udp_tnl-csum-segmentation: "|awk \'{printf $2}\''
    criteria_ok='matches value in list'
    msg_ok='has correct setting'
    to_printValue=' -> tx-udp_tnl-csum-segmentation: '
    matchOneOfTheseValues=['off']
    msg_nok='does not have tx-udp_tnl-csum-segmentation: '+ " or ".join(matchOneOfTheseValues)

    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,list_to_match=matchOneOfTheseValues,text_printValue=to_printValue,printValue=True,rightStrip=True)
    return(check_my_test)

def check_CMG_CPU_pinning():

    #### NCS or GCP or ECCD ####
    if target_platform  in ['ncs','gcp','eccd']:      
        # check: sudo cat /var/lib/kubelet/cpu_manager_state |grep -- '"policyName":"static"'
        # -> ps -ef|grep kubelet     will give you the config file used for kubelet, eg: --config=/var/lib/kubelet/config.yaml    
        apply_to=list_CMG_workers
        cmd_to_exec='"sudo cat /var/lib/kubelet/cpu_manager_state |grep static"'
        criteria_ok='info returned not empty'
        msg_ok='has policyName: static'
        msg_nok='does not have policyName: static'
    #### OpenShift ####
    if target_platform == 'os':
        # check: https://docs.openshift.com/container-platform/4.5/nodes/nodes/nodes-nodes-managing.html
        apply_to=['local']
        cmd_to_exec=cmd_start_kubectl+" get machineconfigpool --show-labels|grep worker|grep cpumanager-enabled"
        criteria_ok='info returned not empty'        
        msg_ok='cpumanager-enabled set in machineconfigpool'
        msg_nok='cpu pinning NOK -> no cpu-manager on the worker nodes?'
        
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok)
    return(check_my_test)

def check_CMG_HugePages():
    # only to be checked if using DPDK:
    apply_to=list_CMG_workers
    cmd_to_exec='"sudo cat /proc/meminfo |grep HugePages_Total|awk \'{printf \$2}\'"'
    criteria_ok='above min value'
    msg_ok='has HugePages enabled'
    to_printValue=' -> HugePages_Total: '
    msg_nok='does not have HugePages enabled (HugePage_Total: 0)'          
   
    # if HugePage_Total is above 0 (eg: 1), we can assume HugePages have been enabled
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,min_value=1,text_printValue=to_printValue,printValue=True)
    return(check_my_test)

def check_CMG_worker_nodes_rmem_max_socket_buffer():

    # CMG needs: 4GB of socket buffer size
    # net.core.rmem_max => Specifies the maximum size (in bytes) of the window for receiving TCP data.
    # net.core.wmem_max => Specifies the maximum size (in bytes) of the window for transmitting TCP data. 
    # 
    # to set: echo "net.core.rmem_max=4194304" | tee -a /etc/sysctl.conf -> check: sudo sysctl -a |grep net.core.rmem_max |awk '{print $3}'
    #         echo "net.core.wmem_max=4194304" | tee -a /etc/sysctl.conf -> check sudo sysctl -a |grep net.core.wmem_max |awk '{print $3}'
    apply_to=list_CMG_workers
    cmd_to_exec='"sudo sysctl -a |grep net.core.rmem_max |awk \'{print \$3}\'"'
    criteria_ok='lower max value'
    msg_ok='net.core.rmem_max OK'
    to_printValue=' -> net.core.rmem_max = '
    msg_nok='does not have net.core.rmem_max below: '+str(cmg_worker_node_rmem_max)          
   
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,max_value=cmg_worker_node_rmem_max,text_printValue=to_printValue,printValue=True,rightStrip=True)
    return(check_my_test)

def check_CMG_worker_nodes_wmem_max_socket_buffer():

    # CMG needs: 4GB of socket buffer size
    # net.core.rmem_max => Specifies the maximum size (in bytes) of the window for receiving TCP data.
    # net.core.wmem_max => Specifies the maximum size (in bytes) of the window for transmitting TCP data. 
    # 
    # to set: echo "net.core.rmem_max=4194304" | tee -a /etc/sysctl.conf -> check: sudo sysctl -a |grep net.core.rmem_max |awk '{print $3}'
    #         echo "net.core.wmem_max=4194304" | tee -a /etc/sysctl.conf -> check sudo sysctl -a |grep net.core.wmem_max |awk '{print $3}'
    apply_to=list_CMG_workers
    cmd_to_exec='"sudo sysctl -a |grep net.core.wmem_max |awk \'{print \$3}\'"'
    criteria_ok='lower max value'
    msg_ok='net.core.wmem_max OK'
    to_printValue=' -> net.core.wmem_max = '
    msg_nok='does not have net.core.wmem_max below: '+str(cmg_worker_node_wmem_max)          
   
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,max_value=cmg_worker_node_wmem_max,text_printValue=to_printValue,printValue=True,rightStrip=True)
    return(check_my_test)

def check_CMG_worker_nodes_udp_rmem_min_socket_buffer():

    apply_to=list_CMG_workers
    cmd_to_exec='"sudo sysctl -a |grep net.ipv4.udp_rmem_min |awk \'{print \$3}\'"'
    criteria_ok='above min value'
    msg_ok='net.ipv4.udp_rmem_min OK'
    to_printValue=' -> net.ipv4.udp_rmem_min = '
    msg_nok='does not have net.ipv4.udp_rmem_min above: '+str(cmg_worker_node_udp_rmem_min)          
   
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,min_value=cmg_worker_node_udp_rmem_min,text_printValue=to_printValue,printValue=True,rightStrip=True)
    return(check_my_test)

def check_CMG_worker_nodes_udp_wmem_min_socket_buffer():

    apply_to=list_CMG_workers
    cmd_to_exec='"sudo sysctl -a |grep net.ipv4.udp_wmem_min |awk \'{print \$3}\'"'
    criteria_ok='above min value'
    msg_ok='net.ipv4.udp_wmem_min OK'
    to_printValue=' -> net.ipv4.udp_wmem_min = '
    msg_nok='does not have net.ipv4.udp_wmem_min above: '+str(cmg_worker_node_udp_wmem_min)          
   
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,min_value=cmg_worker_node_udp_wmem_min,text_printValue=to_printValue,printValue=True,rightStrip=True)
    return(check_my_test)

def check_CMG_worker_nodes_rmem_default():

    # net.core.rmem_default = 1048576

    apply_to=list_CMG_workers
    cmd_to_exec='"sudo sysctl -a |grep net.core.rmem_default |awk \'{print \$3}\'"'
    criteria_ok='matches value in list'
    msg_ok='has correct setting'
    to_printValue=' -> net.core.rmem_default = '
    matchOneOfTheseValues=['1048576']
    msg_nok='does not have net.core.rmem_default = 1048576' 
   
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,list_to_match=matchOneOfTheseValues,text_printValue=to_printValue,printValue=True,rightStrip=True)
    return(check_my_test)

def check_CMG_worker_nodes_wmem_default():

    # net.core.wmem_default = 1048576

    apply_to=list_CMG_workers
    cmd_to_exec='"sudo sysctl -a |grep net.core.wmem_default |awk \'{print \$3}\'"'
    criteria_ok='matches value in list'
    msg_ok='has correct setting'
    to_printValue=' -> net.core.wmem_default = '
    matchOneOfTheseValues=['1048576']
    msg_nok='does not have net.core.wmem_default = 1048576' 
   
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,list_to_match=matchOneOfTheseValues,text_printValue=to_printValue,printValue=True,rightStrip=True)
    return(check_my_test)

def check_CMG_net_ipv6_conf_all_forwarding():

    # CMG R21.8.R1:
    apply_to=list_CMG_workers
    cmd_to_exec='"sudo sysctl -a |grep ipv6.conf.all.forwarding |awk \'{print \$3}\'"'
    criteria_ok='matches value in list'
    msg_ok='has correct setting'
    to_printValue=' -> ipv6.conf.all.forwarding = '
    matchOneOfTheseValues=['1']
    msg_nok='does not ipv6.conf.all.forwarding = 1'          
   
    check_my_test=do_the_check(apply_to,cmd_to_exec,criteria_ok,msg_ok,msg_nok,list_to_match=matchOneOfTheseValues,text_printValue=to_printValue,printValue=True,rightStrip=True)
    return(check_my_test)

def check_CMG_worker_nodes_sriov_interfaces():

    # errors: interface does not exist, or state is not UP
    # /usr/sbin/ifconfig "+sriovitf+" | grep 'UP,BROADCAST,RUNNING'                       else FAIL
    # /usr/sbin/ifconfig "+sriovitf+" | grep mtu | tr -s ' ' | cut -d ' ' -f 4"           > 8900 else FAIL
    # /usr/sbin/ip link show "+sriovitf+" | grep '   vf' | wc -l"                         > 0
    # /usr/sbin/ip link show "+sriovitf+" | grep '   vf' | grep 'trust off' | wc -l       should be 'trust on'    
    
    global CPC_checker_report  

    global_check_OK=True      

    if cmg_sriov_interface_list:
        for i in range(0, len(list_CMG_workers)):
            CPC_checker_report+=level2*' '+"node: "+str(list_CMG_workers[i])+'\n'
            #### get value:        
            for interface in range(0, len(cmg_sriov_interface_list)):
                # check 1: interface up and running?
                ####################################
                #cmd_to_exec='"sudo /usr/sbin/ifconfig "' + cmg_sriov_interface_list[interface] + '" |grep \'UP,BROADCAST,RUNNING\'"'
                cmd_to_exec='"sudo /usr/sbin/ifconfig "' + cmg_sriov_interface_list[interface]
                if login_worker_nodes_with_SSHKEY:
                    my_info=get_Popen_info('ssh -q -i '+sshkey+' '+worker_node_username+'@'+str(list_CMG_workers[i])+' '+cmd_to_exec,True)
                else:
                    if skip_username_worker_node_to_ssh:        
                        my_info=get_Popen_info('ssh -q '+str(list_CMG_workers[i])+' '+cmd_to_exec,True)
                    else:
                        my_info=get_Popen_info('ssh -q '+worker_node_username+'@'+str(list_CMG_workers[i])+' '+cmd_to_exec,True)
                #print(' -> my info:',str(my_info)+'FFFFFFF')
                if my_info.startswith("ERROR:"):
                    global_check_OK=False
                    failure_reason = str(my_info)
                    CPC_checker_report+=level3*' '+failure_reason.ljust(dotline_length-level3+level2,'.')+' FAILED\n'
                    if not create_report:
                        return("NOK","node: "+str(list_CMG_workers[i])+' '+failure_reason)                
                elif my_info=="ERROR":
                    global_check_OK=False
                    failure_reason = ' -> SSH error occurred?'
                    CPC_checker_report+=level3*' '+failure_reason.ljust(dotline_length-level3+level2,'.')+' FAILED\n'
                    if not create_report:
                        return("NOK","node: "+str(list_CMG_workers[i])+' '+failure_reason)
                else:
                    # check whether interface is UP and RUNNING:
                    if not "UP,BROADCAST,RUNNING" in my_info:
                        failure_reason = 'does not have interface: ' + cmg_sriov_interface_list[interface] + " UP & RUNNING"
                        global_check_OK=False
                        CPC_checker_report+=level3*' '+failure_reason.ljust(dotline_length-level3+level2,'.')+' FAILED\n'
                        if not create_report:
                            return("NOK","node: "+str(list_CMG_workers[i])+' '+failure_reason)
                    else:
                        # sriov interface is up and running
                        CPC_checker_report+=level3*' '+'has interface: ' + cmg_sriov_interface_list[interface]+' \n'
                        CPC_checker_report+=level4*' '+'UP & RUNNING'.ljust(dotline_length-level4+level2,'.')+' OK\n'
                        # check 2: mtu size ok?
                        #######################
                        interface_mtu_size=my_info.split()[my_info.split().index("mtu")+1]
                        if not int(interface_mtu_size) > cmg_sriov_interface_mtu_min:
                            global_check_OK=False
                            failure_reason = 'mtu = ' + str(interface_mtu_size) + ' (NOK: is NOT above: '+str(cmg_sriov_interface_mtu_min)+')'
                            CPC_checker_report+=level4*' '+failure_reason.ljust(dotline_length-level4+level2,'.')+' FAILED\n'
                            if not create_report:
                                return("NOK","node: "+str(list_CMG_workers[i])+' '+failure_reason)
                        else:
                            # mtu size is OK
                            msg_ok = 'mtu = ' + str(interface_mtu_size) + ' (OK: is above: '+str(cmg_sriov_interface_mtu_min)+')'
                            CPC_checker_report+=level4*' '+msg_ok.ljust(dotline_length-level4+level2,'.')+' OK\n'
                            # check 3: number of vf's > 0 ?
                            ###############################
                            #cmd_to_exec='"sudo /usr/sbin/ip link show "' + cmg_sriov_interface_list[interface] + '" | grep \'   vf\' | wc -l"'
                            cmd_to_exec='"sudo /usr/sbin/ip link show "' + cmg_sriov_interface_list[interface]
                            if login_worker_nodes_with_SSHKEY:
                                my_info=get_Popen_info('ssh -q -i '+sshkey+' '+worker_node_username+'@'+str(list_CMG_workers[i])+' '+cmd_to_exec,True)
                            else:
                                if skip_username_worker_node_to_ssh:        
                                    my_info=get_Popen_info('ssh -q '+str(list_CMG_workers[i])+' '+cmd_to_exec,True)
                                else:
                                    my_info=get_Popen_info('ssh -q '+worker_node_username+'@'+str(list_CMG_workers[i])+' '+cmd_to_exec,True)
                            number_of_vf=my_info.count('vf ')
                            if not number_of_vf > 0:
                                global_check_OK=False
                                failure_reason = 'number of VF functions = '+str(number_of_vf)+' (NOK: is not above 0)'
                                CPC_checker_report+=level4*' '+failure_reason.ljust(dotline_length-level4+level2,'.')+' FAILED\n'
                                if not create_report:
                                    return("NOK","node: "+str(list_CMG_workers[i])+' '+failure_reason)                            
                            else:
                                # at least 1x vf: vf 0:
                                msg_ok='number of VF functions = '+str(number_of_vf)+' (OK: is above 0)'
                                CPC_checker_report+=level4*' '+msg_ok.ljust(dotline_length-level4+level2,'.')+' OK\n'
                                # check 4: vf ->  all trust on? 
                                ###############################
                                if 'trust off' in my_info:
                                    global_check_OK=False
                                    failure_reason = 'trust off for some VFs (NOK: trust must be on for all VFs)'
                                    CPC_checker_report+=level4*' '+failure_reason.ljust(dotline_length-level4+level2,'.')+' FAILED\n'
                                    if not create_report:
                                        return("NOK","node: "+str(list_CMG_workers[i])+' '+failure_reason)                            
                                else:
                                    msg_ok='trust mode is on for the VFs'
                                    CPC_checker_report+=level4*' '+msg_ok.ljust(dotline_length-level4+level2,'.')+' OK\n'      
    else:
        global_check_OK=False
        failure_reason="cmg_sriov_interface_list is empty in CPC_checker_parms.py"
        CPC_report(level2,failure_reason,check_failed)
        if not create_report:
            return("NOK",failure_reason)        
            
    if global_check_OK:
        return('OK')
    else:
        return("NOK",failure_reason)
    
def print_list_overview(list_to_print,list_description):

    descr='-> '+list_description+': '
    if not list_to_print:    # empty list
        print(descr.ljust(30)+'None')
    else:
        print(descr.ljust(30)+list_to_print[0])
        if len(list_to_print)>1:
            for node in range(1, len(list_to_print)):
                print(' '*30+list_to_print[node])
       
def progressbar(it, prefix="", size=40, file=sys.stdout):
    count = len(it)
    def show(j):
        x = int(size*j/count)
        #file.write("%s[%s%s] %i/%i\r" % (prefix, "#"*x, "."*(size-x), j, count))
        #file.write("%s[%s%s] %i/%i %s\r" % (prefix, "#"*x, "."*(size-x), j, count,str(it[j].__name__).ljust(70)))
        file.write("%s[%s%s] %i/%i %s\r" % (prefix, "#"*x, "."*(size-x), j, count,str(it[j-1].__name__).ljust(70)))
        file.flush()        
    #show(0)
    for i, item in enumerate(it):
        yield item
        show(i+1)
    # remove last called check from progress bar:
    file.write("%s[%s] %i/%i %s\r" % (prefix, "#"*size, count, count,''.ljust(70)))
    file.write("\n")
    file.flush()

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-i","--sshkey",     help= "provide ssh key to access the cluster nodes")
    parser.add_argument("-v","--verbose",    help= "Add output verbosity -> report with details will be shown", action="store_true")
    parser.add_argument("-p","--platform",   choices=['ncs', 'os', 'gcp','eccd'], help="Add target platform: ncs, os (openshift), gcp (Google Cloud Platform Anthos) or eccd (E// CCD)")
    parser.add_argument("-l","--listchecks", help= "Get an overview of implemented checks", action="store_true")
    parser.add_argument("-c","--check",      help= "Give 1x check to be performed (only 1x check!)")
    parser.add_argument("-n","--nodeinfo",   help= "Give overview of nodes (capacity cpu, mem, versions, OS, ...)", action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-s","--skipnode",   help= "Skip 1x node when running checks")
    group.add_argument("-o","--onlynode",   help= "Only run checks on 1x specific node")
    #parser.add_argument("-d","--debug",   help= "Enter debug mode", action="store_true")
    #parser.add_argument("-t","--table",   help= "Print cluster information", action="store_true")
    args = parser.parse_args()
    
    if args.listchecks:
        list_of_checks = []
        for key, value in list(locals().items()):
            if callable(value) and value.__module__ == __name__:
                if key.startswith("check_"):
                    list_of_checks.append(key)
        list_of_checks.sort()
        # if amf_host_interface_list has not been defined, you can't do the check... so remove it from the list:
        if not amf_host_interface_list:
            list_of_checks.remove('check_AMF_worker_nodes_ipvlan_interfaces')
        # remove this dummy test
        list_of_checks.remove('check_test')    
        print('\nOverview of checks that can be performed:')
        print('*****************************************')
        for i in range(0,len(list_of_checks)):
            print('  '+list_of_checks[i])
        print('')
        sys.exit()
    
    if args.sshkey == None:
        # login to worker nodes with SSH key:
        login_worker_nodes_with_SSHKEY = False     
    else:
        login_worker_nodes_with_SSHKEY = True
        sshkey = args.sshkey

    if args.platform is not None:
        target_platform = args.platform

    CPC_checker_report = ''
    if args.verbose:
        create_report = True
        CPC_checker_report = 'CPC platform checker report:\n'
        CPC_checker_report += '****************************\n'
        CPC_checker_report += 'CPC checker version:'.ljust(25)+CPC_PLATFORM_CHECKER_VERSION+'\n'
        if target_platform == 'ncs':
            CPC_checker_report += 'Platform:'.ljust(25)+'NCS\n'
        elif target_platform == 'os':
            CPC_checker_report += 'Platform:'.ljust(25)+'OpenShift\n'
        elif target_platform == 'gcp':
            # no ANTHOS version:
            # CPC_checker_report += 'Platform:'.ljust(25)+'Google Cloud Platform (Anthos)\n'
            # also show ANTHOS version:
            cmd="CLUSTERNAME=`kubectl config view -o=jsonpath='{.clusters[0].name}'`;FIRSTHEALTHYNODE=`kubectl get nodes|grep Ready|head -n1|cut -d' ' -f1`;CLUSTERNAMESPACE=`kubectl get node $FIRSTHEALTHYNODE --show-labels |grep -oP 'namespace=\K.*'|cut -d',' -f1`;kubectl get cluster $CLUSTERNAME -n $CLUSTERNAMESPACE -o yaml| awk '/^  anthosBareMetalVersion:/ {print $2}'|head -n1"
            ANTHOS_VERSION=get_Popen_info(cmd,True)
            CPC_checker_report += 'Platform:'.ljust(25)+'Google Cloud Platform (Anthos) - version: '+str(ANTHOS_VERSION)+'\n'
        elif target_platform == 'eccd':
            CPC_checker_report += 'Platform:'.ljust(25)+'Ericsson CCD platform\n'
        # get K8s version:
        my_info = get_Popen_info(cmd_start_kubectl+"version --short")
        k8s_version = my_info.splitlines()
        CPC_checker_report += 'K8s version:'.ljust(25)+k8s_version[0]+'\n'.ljust(26)+k8s_version[1]+'\n'
        CPC_checker_report += 'Start time:'.ljust(25) + time.strftime("%Y-%b-%d %H:%M:%S") + '\n\n'
    else:
        create_report = False

    # GLOBAL CHECKS:
    ################

    # check_globals=[check_istio,check_glusterFS,check_multus]
    # check_NRD=[check_NRD_labels,check_NRD_docker_images]
    # check_CMG=[check_CMG_CPU_pinning]
    # check_AMF=[check_AMF_CPU_pinning]
    
    #check_globals=[check_istio,check_glusterFS,check_cephFS]
    check_globals=[check_istio,check_glusterFS,check_multus]
    
    # TELENET !!!: Intel NICS + cilium:
    if nic_brand=='Intel' and k8s_cni=='cilium':
        check_globals+=[check_worker_node_udp_tnl_segmentation_off,check_worker_node_udp_tnl_csum_off]
    
    # AMF:
    #  - CPU pinning: cpu-manager-policy field must be set to static
    #      -> K8s: /var/lib/kubelet/cpu_manager_state file is present?
    #  - sys/kernel/mm/transparent_hugepage/enabled must be set to madvise
    # 
    
    # OpenShift?: or RHEL:
    #  - do not blacklist SCTP:
    #      -> following files should not be present:
    #                /etc/modprobe.d/sctp-blacklist.conf
    #                /etc/modprobe.d/sctp_diag-blacklist.conf
    
    # only NCS + Openshift:
    #  - CPU pinning
    #  - only for RHEL/CentOS: sysctl -w kernel.sched_rt_runtime_us=-1
    #                          SELinux must be set as disabled or permissive.

    # TODO:
    # K8s:  label kube-system with permission=talk-to-all
    # nokia@workstation-anthos:~/opstalj/CMM$ k get namespace/kube-system --show-labels |grep 'permission=talk-to-all'
    # kube-system   Active   16d   permission=talk-to-all


    # NRD CHECKS:
    #############    
    check_NRD=[check_NRD_labels]
    
    # NRD performance checks:
    if check_NRD_performance:
        check_NRD+=[check_NRD_performance_tcp_slow_start,check_NRD_performance_nf_conntrack_tcp_timeout_unacknowledged,check_NRD_performance_nf_conntrack_tcp_timeout_max_retrans]

    # AMF CHECKS:
    ############# 
    # AMF global checks:
    check_AMF=[check_AMF_CPU_pinning,check_AMF_worker_nodes_ipv6_enabled,check_AMF_worker_nodes_ipsec_enabled,check_AMF_worker_nodes_rmem_max_socket_buffer,check_AMF_worker_nodes_wmem_max_socket_buffer,check_AMF_worker_nodes_containerd_msgqueue_unlimited,check_AMF_worker_nodes_docker_msgqueue_unlimited,check_AMF_whereabouts_plugin_installed]
    #check_AMF=[check_AMF_worker_nodes_ipv6_enabled]
    
    # Redhat or CentOS host OS:
    check_AMF+=[check_AMF_worker_nodes_kernel_sched_rt_runtime,check_AMF_worker_nodes_transparent_hugepage_madvise,check_AMF_worker_nodes_sctp_enabled]
    check_AMF+=[check_AMF_worker_nodes_selinux_permissive]
    
    #    
    # AMF_CPU_pinning -> on NCS BM:           cpu pooler will be used (TODO)
    #                 -> on NCS on OpenStack: check flavor of worker nodes hw:cpu_policy='dedicated' + sudo cat /var/lib/kubelet/cpu_manager_state
        
    # if amf-host-interface-list has been defined, check interfaces exist & are UP on the AMF worker nodes
    if amf_host_interface_list:
        check_AMF+=[check_AMF_worker_nodes_ipvlan_interfaces]
        
    # CMG CHECKS:
    #############    
    check_CMG=[check_CMG_CPU_pinning,check_CMG_worker_nodes_rmem_max_socket_buffer,check_CMG_worker_nodes_wmem_max_socket_buffer,check_CMG_net_ipv6_conf_all_forwarding,check_CMG_worker_nodes_udp_rmem_min_socket_buffer,check_CMG_worker_nodes_udp_wmem_min_socket_buffer,check_CMG_worker_nodes_rmem_default,check_CMG_worker_nodes_wmem_default]
    
    if deploy_cmg_with_dpdk:
        check_CMG+=[check_CMG_HugePages]

    # if cmg_sriov_interface_list has been defined, check sriov interfaces on the CMG worker nodes
    if cmg_sriov_interface_list:
        check_CMG+=[check_CMG_worker_nodes_sriov_interfaces]

    # SRIOV interfaces checken?    
    # -> config map describes SRIOV implementation:   k describe -n kube-system cm sriovdp-config 

    # {
        # "resourceList": [
            # {
                # "resourceName": "sriov_iavf_1",
                # "resourcePrefix": "gke",
                # "selectors": {
                    # "pfNames": ["ens2f0", "ens5f0"]
                # }
            # }
            # ,
            # {
                # "resourceName": "sriov_iavf_2",
                # "resourcePrefix": "gke",
                # "selectors": {
                    # "pfNames": ["ens2f1","ens5f1"]
                # }
            # }
            # ,
            # {
                # "resourceName": "sriov_iavf_3",
                # "resourcePrefix": "gke",
                # "selectors": {
                    # "pfNames": ["ens3f0"]
                # }
            # }
            # ,
            # {
                # "resourceName": "sriov_iavf_4",
                # "resourcePrefix": "gke",
                # "selectors": {
                    # "pfNames": ["ens3f1"]
                # }
            # }
        # ]
    # }
        
    # -> nodes should have at least 1 of the selectors, eg: interface name, pci name, ...
    # -> then check:
        
    # /usr/sbin/ifconfig "+sriovitf+" | grep 'UP,BROADCAST,RUNNING'                       else FAIL
    # /usr/sbin/ifconfig "+sriovitf+" | grep mtu | tr -s ' ' | cut -d ' ' -f 4"           > 8900 else FAIL
    # /usr/sbin/ip link show "+sriovitf+" | grep '   vf' | wc -l"                         > 0
    # /usr/sbin/ip link show "+sriovitf+" | grep '   vf' | grep 'trust off' | wc -l       should be 'trust on'    



    # RESULT:
    #########
    to_check=check_globals+check_NRD+check_AMF+check_CMG
    
    # remove duplicates:
    to_check = list(dict.fromkeys(to_check))
    
    # 1.13: SKIP CHECKS:
    ####################
    # checks_to_skip=['glusterFS']

    # build list of functions from list of checks (in CPC parms file) to skip:
    funclist_checks_to_skip=[]
    for i in range(0,len(checks_to_skip)):
        try:
            funclist_checks_to_skip.append(eval(checks_to_skip[i]))
        except NameError:
            print('\nWARNING: check = '+str(checks_to_skip[i])+' not found as valid check')

    #checks_to_skip=[check_glusterFS,check_AMF_worker_nodes_docker_msgqueue_unlimited]

    #print('-> to_check: '+str(to_check))

    # remove unwanted checks out of the list:
    if funclist_checks_to_skip:
        for i in range(0,len(funclist_checks_to_skip)):
            while (to_check.count(funclist_checks_to_skip[i])):
                to_check.remove(funclist_checks_to_skip[i])

    #print('\n-> to_check: '+str(to_check))    

    # only want node info:
    if args.nodeinfo:
        #cmd=cmd_start_kubectl+'get nodes -o custom-columns=NAME:.metadata.name,CAP_CPU:.status.capacity.cpu,CAP_MEM:.status.capacity.memory,HUGE_1Gi:.status.capacity.hugepages-1Gi,HUGE_2Mi:.status.capacity.hugepages-2Mi,ARCH:.status.nodeInfo.architecture,ContRunTime:.status.nodeInfo.containerRuntimeVersion,kernelVers:.status.nodeInfo.kernelVersion,kubeProxyVers:.status.nodeInfo.kubeProxyVersion,kubeletVers:.status.nodeInfo.kubeletVersion,OSImage:.status.nodeInfo.osImage'
        cmd=cmd_start_kubectl+'get nodes -o custom-columns=NAME:.metadata.name,CAP_CPU:.status.capacity.cpu,CAP_MEM:.status.capacity.memory,HUGE_1Gi:.status.capacity.hugepages-1Gi,ARCH:.status.nodeInfo.architecture,ContRunTime:.status.nodeInfo.containerRuntimeVersion,kernelVers:.status.nodeInfo.kernelVersion,kubeletVers:.status.nodeInfo.kubeletVersion,OSImage:.status.nodeInfo.osImage'
        my_nodeInfo=get_Popen_info(cmd)
        print('\n'+my_nodeInfo)
        #
        # extra SRIOV info
        #
        # better check:     k describe node worker0 |sed -n -e '/Allocatable/,/System Info:/ p' |grep sriov
        #                   kubectl get node worker2 -o json | jq '.status.allocatable' |grep sriov
        #
        #cmd=cmd_start_kubectl+'get nodes -o custom-columns=NAME:.metadata.name,CAP_SRIOV_IAVF_1:.status.capacity.gke/sriov_iavf_1,CAP_SRIOV_IAVF_2:.status.capacity.gke/sriov_iavf_2,CAP_SRIOV_IAVF_3:.status.capacity.gke/sriov_iavf_3,CAP_SRIOV_IAVF_4:.status.capacity.gke/sriov_iavf_4'
        print('\nAllocatable SRIOV interfaces:')
        cmd='for i in `'+cmd_start_kubectl+'get node --selector=\'!node-role.kubernetes.io/master\' -o custom-columns=NAME:.metadata.name --no-headers`;do echo $i;'+cmd_start_kubectl+'describe node $i |sed -n -e \'/Allocatable/,/System Info:/ p\' |grep sriov|awk \'{ print "\\t" $1" \\t" $2 }\';done'       
        my_nodeInfo=get_Popen_info(cmd)
        print('\n'+my_nodeInfo)
        sys.exit()

    # only perform 1x particular check?:
    if args.check:
        to_check = []
        list_of_checks = []
        for key, value in list(locals().items()):
            if callable(value) and value.__module__ == __name__:
                if key.startswith("check_"):
                    list_of_checks.append(key)
        list_of_checks.sort()
        if args.check in list_of_checks:
            # use function name to append function itself to 'to_check':
            to_check.append(getattr(sys.modules[__name__], args.check))
        else:
            print("\n ERROR: can't find this check ? Do: "+sys.argv[0]+" -l to get a list of possible checks...\n")
            sys.exit()

    checks_OK=[]
    checks_NOK=[]

    print("")

    # build list of worker nodes
    ############################
    # get_all_workers = Popen("kubectl get node --selector='!node-role.kubernetes.io/master' -o custom-columns=NAME:.metadata.name --no-headers",shell=True, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)    
    # list_workers = get_all_workers.stdout.read().decode('utf-8').splitlines()
    my_info = get_Popen_info(cmd_start_kubectl+"get node --selector='!node-role.kubernetes.io/master' -o custom-columns=NAME:.metadata.name --no-headers")
    list_workers = my_info.splitlines()
    
    # build list of NRD worker nodes
    my_info = get_Popen_info(cmd_start_kubectl+"get node --show-labels|grep -e '"+label_nrdnode+"'|awk '{print $1}'")
    list_NRD_workers = my_info.splitlines() 
    
    # build list of AMF worker nodes
    #get_all_AMF_workers = Popen("kubectl get node --show-labels|grep '"+label_amf+"'|awk '{print $1}'",shell=True, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #list_AMF_workers = get_all_AMF_workers.stdout.read().decode('utf-8').splitlines()
    my_info = get_Popen_info(cmd_start_kubectl+"get node --show-labels|grep -e '"+label_amfnode+"'|awk '{print $1}'")
    list_AMF_workers = my_info.splitlines() 
    
    # build list of CMG worker nodes
    my_info = get_Popen_info(cmd_start_kubectl+"get node --show-labels|grep -e '"+label_cmgnode+"'|awk '{print $1}'")
    list_CMG_workers = my_info.splitlines()  

    if args.skipnode:
        nodes_to_skip.append(args.skipnode)

    # skip certain node(s) if given:
    if nodes_to_skip:
        list_workers=[x for x in list_workers if (x not in nodes_to_skip)]
        list_NRD_workers=[x for x in list_NRD_workers if (x not in nodes_to_skip)]
        list_AMF_workers=[x for x in list_AMF_workers if (x not in nodes_to_skip)]
        list_CMG_workers=[x for x in list_CMG_workers if (x not in nodes_to_skip)]
    
    # do all checks only on 1 node:
    if args.onlynode:
        list_workers=[args.onlynode]
        list_NRD_workers=[x for x in list_workers if (x in list_NRD_workers)]
        list_AMF_workers=[args.onlynode]
        list_CMG_workers=[args.onlynode]

    # for ECCD: get the node IPs instead of the hostnames:
    # kubectl describe node worker-pool1-6jvz816e-ccd0-mmt3-tenant1-testing | grep 'InternalIP'|awk '{print $2}'
    # replace in the lists the hostnames by its IP
    if target_platform=='eccd':
        # list_workers:
        for i in range(0,len(list_workers)):
            # get IP of node:
            my_node_IP = get_Popen_info("kubectl describe node "+list_workers[i]+" | grep InternalIP|awk '{print $2}'")
            list_workers[list_workers.index(list_workers[i])] = str(my_node_IP).rstrip('\n')
        # nrd_workers:
        for i in range(0,len(list_NRD_workers)):
            # get IP of node:
            my_node_IP = get_Popen_info("kubectl describe node "+list_NRD_workers[i]+" | grep InternalIP|awk '{print $2}'")
            list_NRD_workers[list_NRD_workers.index(list_NRD_workers[i])] = str(my_node_IP).rstrip('\n')        
        # amf_workers:
        for i in range(0,len(list_AMF_workers)):
            # get IP of node:
            my_node_IP = get_Popen_info("kubectl describe node "+list_AMF_workers[i]+" | grep InternalIP|awk '{print $2}'")
            list_AMF_workers[list_AMF_workers.index(list_AMF_workers[i])] = str(my_node_IP).rstrip('\n')        
        # cmg_workers:
        for i in range(0,len(list_CMG_workers)):
            # get IP of node:
            my_node_IP = get_Popen_info("kubectl describe node "+list_CMG_workers[i]+" | grep InternalIP|awk '{print $2}'")
            list_CMG_workers[list_CMG_workers.index(list_CMG_workers[i])] = str(my_node_IP).rstrip('\n')
            
    if len(list_AMF_workers)==0:
        print("!! ABORTING -> I could not find any AMF worker nodes? Please check the amf_label parameter?\n")
        sys.exit()

    if run_checks_alphabetically:
        # order checks alphabetically:
        # first back to strings, order them and then back to functions:
        temp_list=[]
        for i in range(0,len(to_check)):
            temp_list.append(to_check[i].__name__)
        
        temp_list.sort()

        to_check=[]
        for i in range(0,len(temp_list)):
            to_check.append(eval(temp_list[i]))

    for test in progressbar(to_check, "Progress: ", 40):
        #print("-> checking: "+str(test.__name__))
        if create_report:
            CPC_report(level1,str(test.__name__))
        result_test=test()
        if result_test=='OK':
            checks_OK.append(test.__name__)
        else:
            checks_NOK.append(test.__name__)
            checks_NOK.append(result_test[1])

    print("")    
    #print("Succesfull tests: "+str(checks_OK))
    total_tests=len(checks_OK)+len(checks_NOK)//2
    print("Successful tests ["+str(len(checks_OK))+'/'+str(total_tests)+']:')
    for i in range(0,len(checks_OK)):
        print(' - '+checks_OK[i])
        
    if len(checks_NOK)>1:    
        print("\nFailing tests    ["+str(len(checks_NOK)//2)+'/'+str(total_tests)+']:')
        
        # print failing tests in nicer output:
        temp_checks_NOK=[]
        for i in range(0,len(checks_NOK),2):
            temp_checks_NOK.append(checks_NOK[i])
        # longest check:
        longest_check=len(max(temp_checks_NOK, key=len))
        
        for i in range(0,len(checks_NOK),2):
            print(' - '+checks_NOK[i].ljust(longest_check)+' : '+checks_NOK[i+1])
    
    print("")  

    if create_report:
        print(CPC_checker_report)
        if not args.onlynode:
            print('Some extra info:')
            print_list_overview(list_workers,'Worker nodes')
            print_list_overview(list_NRD_workers,'NRD worker nodes')
            print_list_overview(list_AMF_workers,'AMF worker nodes')
            print_list_overview(list_CMG_workers,'CMG worker nodes')
            print('')
            print_list_overview(nodes_to_skip,'skipped nodes')
            if checks_to_skip:  # list not empty:
                print_list_overview(checks_to_skip,'skipped checks')           
        print('')

    # print("")
    # get only worker nodes:
    # kubectl get node -l node-role.kubernetes.io/worker
    # kubectl get node --selector='!node-role.kubernetes.io/master' -o custom-columns=NAME:.metadata.name --no-headers
    
    # get current cpu/mem of worker nodes:
    # kubectl adm top nodes -l node-role.kubernetes.io/worker
    # kubectl get nodes -o custom-columns=NAME:.metadata.name,CAPACITY_CPU:.status.capacity.cpu,CAPACITY_MEM:.status.capacity.memory
    
    # get node info:
    # kubectl get nodes -o custom-columns=NAME:.metadata.name,CAPACITY_CPU:.status.capacity.cpu,CAPACITY_MEM:.status.capacity.memory,ARCH:.status.nodeInfo.architecture,ContRunTime:.status.nodeInfo.containerRuntimeVersion,kernelVers:.status.nodeInfo.kernelVersion,kubeProxyVers:.status.nodeInfo.kubeProxyVersion,kubeletVers:.status.nodeInfo.kubeletVersion,OS:.status.nodeInfo.operatingSystem,OSImage:.status.nodeInfo.osImage
        
    # get nbr of CPU & MEM of all nodes:
    # kubectl get nodes -o custom-columns=NODE:.metadata.name,CPU:.status.capacity.cpu,MEM:.status.capacity.memory
    
    # get all PODs on ALL worker nodes:
    # for i in `k get nodes --selector='!node-role.kubernetes.io/master' -o custom-columns=NAME:.metadata.name --no-headers`;do echo "Node: $i";kubectl get pods --all-namespaces -o wide --field-selector spec.nodeName=$i;echo "";done

    # get RedHat ServiceMesh version:
    # kubectl get csv -n openshift-operators `kubectl get csv -n openshift-operators |grep servicemeshoperator|awk '{print $1}'` -o custom-columns=vers:spec.version|tail -1
    
    # check Hugepage size on nodes:
    # cat /proc/meminfo | grep Hugepagesize
    
    # CPU pinning:
    # cat /proc/<pid>/status

    # Telenet SRIOV info:
    #####################
    # kubectl get nodes -o custom-columns=NAME:.metadata.name,CAP_SRIOV_IAVF_1:.status.capacity.gke/sriov_iavf_1,CAP_SRIOV_IAVF_2:.status.capacity.gke/sriov_iavf_2,CAP_SRIOV_IAVF_3:.status.capacity.gke/sriov_iavf_3,CAP_SRIOV_IAVF_4:.status.capacity.gke/sriov_iavf_4
    #kubectl get nodes -o custom-columns=NAME:.metadata.name,ALLOC_SRIOV_IAVF_1:.status.allocatable.gke/sriov_iavf_1,ALLOC_SRIOV_IAVF_2:.status.allocatable.gke/sriov_iavf_2,ALLOC_SRIOV_IAVF_3:.status.allocatable.gke/sriov_iavf_3,ALLOC_SRIOV_IAVF_4:.status.allocatable.gke/sriov_iavf_4  
    
    # check Intel & cilium:
    # -> turn off segmentation:
    #       ethtool -K bond0 tx-udp_tnl-csum-segmentation off;ethtool -K bond0 tx-udp_tnl-segmentation off
    #       ethtool -K bond0 tx-udp_tnl-segmentation off
    #       sudo ethtool -K bond0 tx-udp_tnl-csum-segmentation off;sudo ethtool -K bond0 tx-udp_tnl-segmentation off
    # -> check segmentation:
    #       ethtool -k bond0 |grep "tx-udp_tnl-segmentation: off"|awk \'{printf $2}\'
    #       ethtool -k bond0 |grep "tx-udp_tnl-csum-segmentation: off"|awk \'{printf $2}\'
    
    


    
    # SRIOV interfaces checken?    
    ###########################
    #
    # NCS:
    #  - op top of OpenStack -> host device plugin (it can't use the SRIOV device plugin)
    #  - baremetal           -> SRIOV device plugin
    #
    # https://confluence-app.ext.net.nokia.com/pages/viewpage.action?spaceKey=CSFDEV&title=Multus+examples+for+NCS#MultusexamplesforNCS-3.MultusexamplesforNCSclustersrunningonbaremetalwithSR-IOV(VLANtaggingisrequired)
    #
    # kubectl describe nodes | egrep "Name:|sriov_"
    #   gives per node the number of sriov or number of sriov dpdk driver:
    #
    #   kubectl describe nodes | egrep "Name:|sriov_"
    #       Name: baremetal-airframe-sut2-allinone-0
    #       nokia.k8s.io/sriov_ens1f0: 8
    #       nokia.k8s.io/sriov_ens1f1: 8
    #       nokia.k8s.io/sriov_vfio_ens1f0: 2           <-- dpdk driver -> only for Intel NICs (Mellanox supports both, so it won't have sriov_vfio pools)
    #       nokia.k8s.io/sriov_vfio_ens1f1: 2
    #
    #   kubectl get node <nodename> -o custom-columns=NAME:.metadata.name,ALLOC:.status.allocatable
    #
    #
    
    
    # -> config map describes SRIOV implementation:   k describe -n kube-system cm sriovdp-config 
    
    # -> https://github.com/k8snetworkplumbingwg/sriov-network-device-plugin (eg: overview of possible selectors)

    # {
        # "resourceList": [
            # {
                # "resourceName": "sriov_iavf_1",
                # "resourcePrefix": "gke",
                # "selectors": {
                    # "pfNames": ["ens2f0", "ens5f0"]
                # }
            # }
            # ,
            # {
                # "resourceName": "sriov_iavf_2",
                # "resourcePrefix": "gke",
                # "selectors": {
                    # "pfNames": ["ens2f1","ens5f1"]
                # }
            # }
            # ,
            # {
                # "resourceName": "sriov_iavf_3",
                # "resourcePrefix": "gke",
                # "selectors": {
                    # "pfNames": ["ens3f0"]
                # }
            # }
            # ,
            # {
                # "resourceName": "sriov_iavf_4",
                # "resourcePrefix": "gke",
                # "selectors": {
                    # "pfNames": ["ens3f1"]
                # }
            # }
        # ]
    # }
        
    # -> nodes should have at least 1 of the selectors, eg: interface name, pci name, ...
    
    # k get cm sriovdp-config -n kube-system -o 'go-template={{index .data "config.json" }}' | awk -F"[][]" '/pfNames/ { printf "["$2"]\n"}'
    # ["ens2f0", "ens5f0"]
    # ["ens2f1","ens5f1"]
    # ["ens3f0"]
    # ["ens3f1"]
    #
    # k get cm sriovdp-config -n kube-system -o 'go-template={{index .data "config.json" }}' | awk '/pfNames/ { printf $2 }'
    # ["eno5"]["eno6"]["ens2f0"]["ens2f1"]
    #
    # k get cm -n kube-system sriovdp-config -o yaml |grep pfNames\":|awk '{ print $2 }'
    # ["eno5"]
    # ["eno6"]
    # ["ens2f0"]
    # ["ens2f1"]
    #
    # -> then check:
    #
    # check sriov enabled interfaces 
    # eg: Mellanox  ->  cat /sys/class/net/ens2f0/device/sriov_numvfs        
    #    
    # /usr/sbin/ifconfig "+sriovitf+" | grep 'UP,BROADCAST,RUNNING'                       else FAIL
    # /usr/sbin/ifconfig "+sriovitf+" | grep mtu | tr -s ' ' | cut -d ' ' -f 4"           > 8900 else FAIL
    # /usr/sbin/ip link show "+sriovitf+" | grep '   vf' | wc -l"                         > 0
    # /usr/sbin/ip link show "+sriovitf+" | grep '   vf' | grep 'trust off' | wc -l       should be 'trust on'       
