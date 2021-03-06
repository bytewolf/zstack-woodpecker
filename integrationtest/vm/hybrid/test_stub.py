'''

Create an unified test_stub to share test operations

@author: Youyk
'''

import os
import sys
import time
import random
import commands
import threading
import urllib2
import zstacklib.utils.ssh as ssh
import zstackwoodpecker.test_lib as test_lib
import zstackwoodpecker.test_util as test_util
import zstackwoodpecker.zstack_test.zstack_test_vm as zstack_vm_header
import zstackwoodpecker.zstack_test.zstack_test_vip as zstack_vip_header
import zstackwoodpecker.test_state as test_state
import zstackwoodpecker.operations.net_operations as net_ops
import zstackwoodpecker.operations.account_operations as acc_ops
import zstackwoodpecker.operations.resource_operations as res_ops
import zstackwoodpecker.operations.hybrid_operations as hyb_ops
import zstackwoodpecker.operations.ipsec_operations as ipsec_ops


Port = test_state.Port

rule1_ports = Port.get_ports(Port.rule1_ports)
rule2_ports = Port.get_ports(Port.rule2_ports)
rule3_ports = Port.get_ports(Port.rule3_ports)
rule4_ports = Port.get_ports(Port.rule4_ports)
rule5_ports = Port.get_ports(Port.rule5_ports)
denied_ports = Port.get_denied_ports()
#rule1_ports = [1, 22, 100]
#rule2_ports = [9000, 9499, 10000]
#rule3_ports = [60000, 60010, 65535]
#rule4_ports = [5000, 5501, 6000]
#rule5_ports = [20000, 28999, 30000]
#test_stub.denied_ports = [101, 4999, 8990, 15000, 30001, 49999]
target_ports = rule1_ports + rule2_ports + rule3_ports + rule4_ports + rule5_ports + denied_ports

postfix = time.strftime('%m%d-%H%M%S', time.localtime())


class HybridObject(object):
    def __init__(self):
        self.ks = None
        self.datacenter = None
        self.region_id = None
        self.iz = None
        self.vpc = None
        self.vswitch = None
        self.vpn = None
        self.eip = None
        self.sg = None
        self.sg_rule = None
        self.vm = None
        self.vr = None
        self.vr_name = 'zstack-test-vrouter-%s' % postfix
        self.route_entry = None
        self.oss_bucket = None
        self.oss_bucket_create = None
        self.ecs_instance = None
        self.ecs_image = None
        self.vpn_gateway = None
        self.user_vpn_gateway = None
        self.user_gw_ip = None
        self.dst_cidr_block = None
        self.prepaid_ecs = None
        self.vpn_connection = None


    def add_ks(self):
        ks_existed = hyb_ops.query_aliyun_key_secret()
        if ks_existed:
            self.ks = ks_existed[0]
        else:
            self.ks = hyb_ops.add_aliyun_key_secret('test_hybrid', 'test for hybrid', os.getenv('aliyunKey'), os.getenv('aliyunSecret'))

    def add_datacenter_iz(self, add_datacenter_only=False, check_vpn_gateway=False, region_id=None, check_ecs=False, check_prepaid_ecs=False):
        self.add_ks()
        datacenter_type = os.getenv('datacenterType')
        # Clear datacenter remained in local
        datacenter_local = hyb_ops.query_datacenter_local()
        if datacenter_local:
            for d in datacenter_local:
                hyb_ops.del_datacenter_in_local(d.uuid)
        if region_id:
            self.datacenter = hyb_ops.add_datacenter_from_remote(datacenter_type, region_id, 'datacenter for test')
            self.region_id = region_id
            return
        datacenter_list = hyb_ops.get_datacenter_from_remote(datacenter_type)
        regions = [dc.regionId for dc in datacenter_list]
        err_list = []
        for r in regions:
            if r == 'cn-beijing':
                continue
            try:
                datacenter = hyb_ops.add_datacenter_from_remote(datacenter_type, r, 'datacenter for test')
            except hyb_ops.ApiError, e:
                err_list.append(e)
            if datacenter and add_datacenter_only:
                self.datacenter = datacenter
                self.region_id = r
                return
            elif len(err_list) == len(regions):
                raise hyb_ops.ApiError("Failed to add DataCenter: %s" % err_list)
            # Add Identity Zone
            iz_list = hyb_ops.get_identity_zone_from_remote(datacenter_type, r)
            vpn_gateway_list = []
            prepaid_ecs_list = []
            for iz in iz_list:
                if not iz.availableInstanceTypes:
                    continue
                iz_inv = hyb_ops.add_identity_zone_from_remote(datacenter_type, datacenter.uuid, iz.zoneId)
                if check_vpn_gateway:
                    vpn_gateway_list = hyb_ops.sync_vpc_vpn_gateway_from_remote(datacenter.uuid)
                    if iz_inv and vpn_gateway_list:
                        self.datacenter = datacenter
                        self.iz = iz_inv
                        self.vpn_gateway = vpn_gateway_list[0]
                        return
                    else:
                        self.del_iz(iz_inv.uuid)
                elif check_ecs:
                    ecs_list = hyb_ops.sync_ecs_instance_from_remote(datacenter.uuid)
                    if ecs_list:
                        self.datacenter = datacenter
                        self.iz = iz_inv
                        self.ecs_instance = ecs_list[0]
                        return
                    else:
                        self.del_iz(iz_inv.uuid)
                elif iz_inv and check_prepaid_ecs:
                    ecs_list = hyb_ops.sync_ecs_instance_from_remote(datacenter.uuid, only_zstack='false')
                    prepaid_ecs_list = [ep for ep in ecs_list if ep.chargeType == 'PrePaid']
                    if prepaid_ecs_list:
                        self.datacenter = datacenter
                        self.iz = iz_inv
                        self.prepaid_ecs = prepaid_ecs_list[0]
                        return
                    else:
                        self.del_iz(iz_inv.uuid)
                elif iz_inv:
                    self.datacenter = datacenter
                    self.iz = iz_inv
                    return
            if check_vpn_gateway and vpn_gateway_list:
                break
            elif check_prepaid_ecs and prepaid_ecs_list:
                break
            else:
                hyb_ops.del_datacenter_in_local(datacenter.uuid)
        if check_vpn_gateway and not vpn_gateway_list:
            test_util.test_fail("VpnGate for ipsec vpn connection was not found in all available dataCenter")
        elif check_prepaid_ecs and not prepaid_ecs_list:
            test_util.test_fail("Prepaid ECS was not found in all available dataCenter")
 
    def del_datacenter(self):
        hyb_ops.del_datacenter_in_local(self.datacenter.uuid)
        condition = res_ops.gen_query_conditions('regionId', '=', self.region_id)
        assert not hyb_ops.query_datacenter_local(condition)
 
    def del_iz(self, iz_uuid=None):
        if iz_uuid:
            hyb_ops.del_identity_zone_in_local(iz_uuid)
        else:
            hyb_ops.del_identity_zone_in_local(self.iz.uuid)
            condition = res_ops.gen_query_conditions('zoneId', '=', self.iz.zoneId)
            assert not hyb_ops.query_iz_local(condition)

    def check_resource(self, ops, cond_name, cond_val, query_method):
        condition = res_ops.gen_query_conditions(cond_name, '=', cond_val)
        query_create = 'hyb_ops.%s(condition)' % query_method
        query_delete = 'hyb_ops.%s(condition)' % query_method
        if ops == 'create':
            assert eval(query_create)
        elif ops == 'delete':
            assert not eval(query_delete)

    def create_bucket(self):
        self.bucket_name = 'zstack-test-oss-bucket-%s-%s' % (postfix, self.region_id)
        self.oss_bucket = hyb_ops.create_oss_bucket_remote(self.datacenter.uuid, self.bucket_name, 'created-by-zstack-for-test')
        self.oss_bucket_create = True
        self.check_resource('create', 'bucketName', self.bucket_name, 'query_oss_bucket_file_name')

    def add_bucket(self):
        bucket_remote = hyb_ops.get_oss_bucket_name_from_remote(self.datacenter.uuid)
        if bucket_remote:
            self.bucket_name = bucket_remote[0].bucketName
            self.oss_bucket = hyb_ops.add_oss_bucket_from_remote(self.datacenter.uuid, self.bucket_name)
        else:
            self.create_bucket()
        bucket_local = hyb_ops.query_oss_bucket_file_name()
        bucket_name_local = [bk.bucketName for bk in bucket_local]
        assert self.bucket_name in bucket_name_local

    def attach_bucket(self):
        hyb_ops.attach_oss_bucket_to_ecs_datacenter(self.oss_bucket.uuid)
        bucket_local = hyb_ops.query_oss_bucket_file_name()
        bucket_attached = [bk for bk in bucket_local if bk.uuid==self.oss_bucket.uuid]
        assert bucket_attached[0].current == 'true'

    def detach_bucket(self):
        hyb_ops.detach_oss_bucket_from_ecs_datacenter(self.oss_bucket.uuid)
        bucket_local = hyb_ops.query_oss_bucket_file_name()
        bucket_attached = [bk for bk in bucket_local if bk.uuid==self.oss_bucket.uuid]
        assert bucket_attached[0].current == 'false'

    def del_bucket(self, remote=True):
        if remote:
            condition = res_ops.gen_query_conditions('bucketName', '=', self.bucket_name)
            if not hyb_ops.query_oss_bucket_file_name(condition):
                self.oss_bucket = hyb_ops.add_oss_bucket_from_remote(self.datacenter.uuid, self.bucket_name)
            bucket_file = hyb_ops.get_oss_bucket_file_from_remote(self.oss_bucket.uuid).files
            if bucket_file:
                time.sleep(20)
                for i in bucket_file:
                    hyb_ops.del_oss_bucket_file_remote(self.oss_bucket.uuid, i)
            time.sleep(10)
            hyb_ops.del_oss_bucket_remote(self.oss_bucket.uuid)
        else:
            if self.oss_bucket:
                hyb_ops.del_oss_bucket_name_in_local(self.oss_bucket.uuid)
            elif self.oss_bucket_create:
                hyb_ops.del_oss_bucket_name_in_local(self.oss_bucket_create.uuid)
        self.check_resource('delete', 'bucketName', self.bucket_name, 'query_oss_bucket_file_name')

    def del_vpn_gateway(self):
        hyb_ops.del_vpc_vpn_gateway_local(self.vpn_gateway.uuid)
        hyb_ops.sync_vpc_vpn_gateway_from_remote(self.datacenter.uuid)
        self.check_resource('delete', 'vpnGatewayId', self.vpn_gateway.vpnGatewayId, 'query_vpc_vpn_gateway_local')

    def create_eip(self):
        self.eip = hyb_ops.create_hybrid_eip(self.datacenter.uuid, 'zstack-test-eip', '1')
        self.eip_create = True
        self.check_resource('create', 'eipId', self.eip.eipId, 'query_hybrid_eip_local')

    def del_eip(self, remote=True):
        if remote:
            hyb_ops.del_hybrid_eip_remote(self.eip.uuid)
            hyb_ops.sync_hybrid_eip_from_remote(self.datacenter.uuid)
        else:
            hyb_ops.del_hybrid_eip_local(self.eip.uuid)
        self.check_resource('delete', 'eipId', self.eip.eipId, 'query_hybrid_eip_local')

    def get_eip(self, in_use=False, sync_eip=False):
        hyb_ops.sync_hybrid_eip_from_remote(self.datacenter.uuid)
        eip_all = hyb_ops.query_hybrid_eip_local()
        if sync_eip:
            self.eip = [eip for eip in eip_all if eip.eipId == self.eip.eipId][0]
        elif in_use:
            self.eip = [e for e in eip_all if e.allocateResourceUuid == self.ecs_instance.uuid][0]
        else:
            eip_available = [eip for eip in eip_all if eip.status.lower() == 'available']
            if eip_available:
                self.eip = eip_available[0]
            else:
                self.create_eip()

    def attach_eip_to_ecs(self):
        hyb_ops.attach_hybrid_eip_to_ecs(self.eip.uuid, self.ecs_instance.uuid)
        self.get_eip(sync_eip=True)
        assert self.eip.allocateResourceUuid == self.ecs_instance.uuid

    def detach_eip_from_ecs(self):
        hyb_ops.detach_hybrid_eip_from_ecs(self.eip.uuid)
        self.get_eip(sync_eip=True)
        assert self.eip.status.lower() == 'available'

    def check_eip_accessibility(self):
        self.get_eip(in_use=True)
        cmd = "sshpass -p Password123 ssh -o StrictHostKeyChecking=no root@%s 'ls /'" % self.eip.eipAddress
        for _ in xrange(60):
            cmd_status = commands.getstatusoutput(cmd)[0]
            if cmd_status == 0:
                break
            else:
                time.sleep(3)
        assert cmd_status == 0, "Login Ecs via public ip failed!"

    def create_vpc(self):
        self.vpc_name = 'zstack-test-vpc-%s' % postfix
        self.vpc = hyb_ops.create_ecs_vpc_remote(self.datacenter.uuid, self.vpc_name, self.vr_name, '172.16.0.0/12')
        time.sleep(20)
        self.check_resource('create', 'ecsVpcId', self.vpc.ecsVpcId, 'query_ecs_vpc_local')

    def del_vpc(self, remote=True):
        if remote:
            hyb_ops.del_ecs_vpc_remote(self.vpc.uuid)
            hyb_ops.sync_ecs_vpc_from_remote(self.datacenter.uuid)
        else:
            hyb_ops.del_ecs_vpc_local(self.vpc.uuid)
        self.check_resource('delete', 'ecsVpcId', self.vpc.ecsVpcId, 'query_ecs_vpc_local')

    def get_vpc(self, has_vpn_gateway=False):
        hyb_ops.sync_ecs_vpc_from_remote(self.datacenter.uuid)
        vpc_all = hyb_ops.query_ecs_vpc_local()
        if has_vpn_gateway:
            hyb_ops.sync_ecs_vswitch_from_remote(self.datacenter.uuid)
            cond_vs = res_ops.gen_query_conditions('uuid', '=', self.vpn_gateway.vSwitchUuid)
            vs = hyb_ops.query_ecs_vswitch_local(cond_vs)[0]
            ecs_vpc = [vpc for vpc in vpc_all if vpc.uuid == vs.ecsVpcUuid]
        else:
            ecs_vpc = [vpc for vpc in vpc_all if vpc.status.lower() == 'available']
        if ecs_vpc:
            self.vpc = ecs_vpc[0]
        else:
            self.create_vpc()

    def create_vswitch(self):
        hyb_ops.sync_ecs_vswitch_from_remote(self.datacenter.uuid)
        cond_vpc_vs = res_ops.gen_query_conditions('ecsVpcUuid', '=', self.vpc.uuid)
        vpc_vs = hyb_ops.query_ecs_vswitch_local(cond_vpc_vs)
        if vpc_vs:
            vs_cidr = [vs.cidrBlock.split('.')[-2] for vs in vpc_vs]
            cidr_val = list(set(str(i) for i in xrange(255)).difference(set(vs_cidr)))
        else:
            cidr_val = [str(i) for i in xrange(200, 255)]
        vpc_cidr_list = self.vpc.cidrBlock.split('.')
        vpc_cidr_list[2] = random.choice(cidr_val)
        vpc_cidr_list[3] = '0/24'
        vswitch_cidr = '.'.join(vpc_cidr_list)
        self.vs_name = 'zstack-test-vswitch-%s' % postfix
        self.vswitch = hyb_ops.create_ecs_vswtich_remote(self.vpc.uuid, self.iz.uuid, self.vs_name, vswitch_cidr)
        time.sleep(10)
        self.check_resource('create', 'vSwitchId', self.vswitch.vSwitchId, 'query_ecs_vswitch_local')

    def del_vswitch(self, remote=True):
        if remote:
            hyb_ops.del_ecs_vswitch_remote(self.vswitch.uuid)
            hyb_ops.sync_ecs_vswitch_from_remote(self.datacenter.uuid)
        else:
            hyb_ops.del_ecs_vswitch_in_local(self.vswitch.uuid)
        self.check_resource('delete', 'vSwitchId', self.vswitch.vSwitchId, 'query_ecs_vswitch_local')

    def get_vswitch(self):
        hyb_ops.sync_ecs_vswitch_from_remote(self.datacenter.uuid)
        condition = res_ops.gen_query_conditions('ecsVpcUuid', '=', self.vpc.uuid)
        vswitch = hyb_ops.query_ecs_vswitch_local(condition)
        if vswitch:
            self.vswitch = vswitch[0]
        else:
            self.create_vswitch()

    def create_sg(self):
        sg_name = 'zstack-test-ecs-security-group-%s' % postfix
        self.sg = hyb_ops.create_ecs_security_group_remote(sg_name, self.vpc.uuid)
        time.sleep(20)
        self.check_resource('create', 'securityGroupId', self.sg.securityGroupId, 'query_ecs_security_group_local')
        self.sg_create = True

    def del_sg(self, remote=True):
        if remote:
            hyb_ops.sync_ecs_security_group_from_remote(self.vpc.uuid)
            condition = res_ops.gen_query_conditions('securityGroupId', '=', self.sg.securityGroupId)
            self.sg = hyb_ops.query_ecs_security_group_local(condition)[0]
            hyb_ops.del_ecs_security_group_remote(self.sg.uuid)
        else:
            hyb_ops.del_ecs_security_group_in_local(self.sg.uuid)
        self.check_resource('delete', 'securityGroupId', self.sg.securityGroupId, 'query_ecs_security_group_local')

    def get_sg(self):
        hyb_ops.sync_ecs_security_group_from_remote(self.vpc.uuid)
        sg_local = hyb_ops.query_ecs_security_group_local()
        ecs_security_group = [sg for sg in sg_local if sg.ecsVpcUuid == self.vpc.uuid]
        if ecs_security_group:
            self.sg = ecs_security_group[0]
        else:
            self.create_sg()

    def create_sg_rule(self):
        self.sg_rule_ingress = hyb_ops.create_ecs_security_group_rule_remote(self.sg.uuid, 'ingress', 'TCP', '445/445', '0.0.0.0/0', 'drop', 'intranet', '1')
        self.sg_rule_egress = hyb_ops.create_ecs_security_group_rule_remote(self.sg.uuid, 'egress', 'TCP', '80/80', '0.0.0.0/0', 'accept', 'intranet', '10')
        time.sleep(10)
        self.check_resource('create', 'ecsSecurityGroupUuid', self.sg.uuid, 'query_ecs_security_group_rule_local')

    def del_sg_rule(self):
        hyb_ops.del_ecs_security_group_rule_remote(self.sg_rule_ingress.uuid)
        hyb_ops.del_ecs_security_group_rule_remote(self.sg_rule_egress.uuid)
        time.sleep(10)
        hyb_ops.sync_ecs_security_group_rule_from_remote(self.sg.uuid)
        self.check_resource('delete', 'ecsSecurityGroupUuid', self.sg.uuid, 'query_ecs_security_group_rule_local')

    def get_sg_rule(self):
        hyb_ops.sync_ecs_security_group_rule_from_remote(self.sg.uuid)
        cond_sg_rule = res_ops.gen_query_conditions('ecsSecurityGroupUuid', '=', self.sg.uuid)
        sg_rule = hyb_ops.query_ecs_security_group_rule_local(cond_sg_rule)
        if not sg_rule:
            hyb_ops.create_ecs_security_group_rule_remote(self.sg.uuid, 'ingress', 'ALL', '-1/-1', '0.0.0.0/0', 'accept', 'intranet', '10')
            hyb_ops.create_ecs_security_group_rule_remote(self.sg.uuid, 'egress', 'ALL', '-1/-1', '0.0.0.0/0', 'accept', 'intranet', '10')
        assert hyb_ops.query_ecs_security_group_rule_local(cond_sg_rule)

    def get_vr(self):
        hyb_ops.sync_aliyun_virtual_router_from_remote(self.vpc.uuid)
        vr_local = hyb_ops.query_aliyun_virtual_router_local()
        self.vr = [v for v in vr_local if v.vrId == self.vpc.vRouterId][0]
        assert self.vr

    def create_user_vpn_gateway(self):
        if not self.user_gw_ip:
            self.user_gw_ip = '192.168.%s.%s' % (random.randint(1,254), random.randint(1,254))
        self.user_vpn_gateway = hyb_ops.create_vpc_user_vpn_gateway(self.datacenter.uuid, gw_ip=self.user_gw_ip, gw_name="zstack-test-user-vpn-gateway")
        time.sleep(10)
        self.check_resource('create', 'gatewayId', self.user_vpn_gateway.gatewayId, 'query_vpc_user_vpn_gateway_local')

    def get_user_vpn_gateway(self, vip):
        hyb_ops.sync_vpc_user_vpn_gateway_from_remote(self.datacenter.uuid)
        user_vpn_gw_local = hyb_ops.query_vpc_user_vpn_gateway_local()
        user_vpn_gw = [gw for gw in user_vpn_gw_local if gw.ip == vip.ip]
        if user_vpn_gw:
            self.user_vpn_gateway = user_vpn_gw[0]
        else:
            self.user_gw_ip = vip.ip
            self.create_user_vpn_gateway()

    def del_user_vpn_gateway(self, remote=True):
        if remote:
            hyb_ops.del_vpc_user_vpn_gateway_remote(self.user_vpn_gateway.uuid)
            hyb_ops.sync_vpc_user_vpn_gateway_from_remote(self.datacenter.uuid)
        else:
            hyb_ops.del_vpc_user_vpn_gateway_local(self.user_vpn_gateway.uuid)
        self.check_resource('delete', 'gatewayId', self.user_vpn_gateway.gatewayId, 'query_vpc_user_vpn_gateway_local')

    def create_ecs_image(self, check_progress=False):
        cond_image = res_ops.gen_query_conditions('name', '=', os.getenv('imageName_s'))
        image =  res_ops.query_resource(res_ops.IMAGE, cond_image)[0]
        bs_uuid = image.backupStorageRefs[0].backupStorageUuid
        hyb_ops.update_image_guestOsType(image.uuid, guest_os_type='CentOS')
        if check_progress:
            create_image_pid = os.fork()
            if create_image_pid == 0:
                self.ecs_image = hyb_ops.create_ecs_image_from_local_image(bs_uuid, self.datacenter.uuid, image.uuid, name='zstack-test-ecs-image')
                sys.exit(0)
            for _ in xrange(600):
                    image_progress = hyb_ops.get_create_ecs_image_progress(self.datacenter.uuid, image.uuid)
                    if image_progress.progress.progress == "100%":
                        break
                    else:
                        time.sleep(1)
            os.waitpid(create_image_pid, 0)
            assert image_progress.progress.progress == "100%"
        else:
            self.ecs_image = hyb_ops.create_ecs_image_from_local_image(bs_uuid, self.datacenter.uuid, image.uuid, name='zstack-test-ecs-image')
            self.check_resource('create', 'ecsImageId', self.ecs_image.ecsImageId, 'query_ecs_image_local')
        time.sleep(30)

    def sync_ecs_image(self):
        hyb_ops.sync_ecs_image_from_remote(self.datacenter.uuid, image_type='system')
        condition = res_ops.gen_query_conditions('type', '=', 'system')
        assert hyb_ops.query_ecs_image_local(condition)

    def del_ecs_image(self, remote=True, system=False):
        if remote:
            hyb_ops.del_ecs_image_remote(self.ecs_image.uuid)
            hyb_ops.sync_ecs_image_from_remote(self.datacenter.uuid)
        else:
            if system:
                image_local = hyb_ops.query_ecs_image_local()
                for i in image_local:
                    hyb_ops.del_ecs_image_in_local(i.uuid)
                cond_image_system = res_ops.gen_query_conditions('type', '=', 'system')
                assert not hyb_ops.query_ecs_image_local(cond_image_system)
                return
            else:
                hyb_ops.del_ecs_image_in_local(self.ecs_image.uuid)
        self.check_resource('delete', 'ecsImageId', self.ecs_image.ecsImageId, 'query_ecs_image_local')

    def create_route_entry(self):
        self.get_vr()
        self.dst_cidr_block = '172.27.%s.0/24' % random.randint(1,254)
        self.route_entry = hyb_ops.create_aliyun_vpc_virtualrouter_entry_remote(self.dst_cidr_block, self.vr.uuid, vrouter_type='vrouter', next_hop_type='VpnGateway', next_hop_uuid=self.vpn_gateway.uuid)
        time.sleep(30)
        self.check_resource('create', 'destinationCidrBlock', self.dst_cidr_block, 'query_aliyun_route_entry_local')

    def del_route_entry(self, remote=True):
        if remote:
            hyb_ops.del_aliyun_route_entry_remote(self.route_entry.uuid)
            hyb_ops.sync_route_entry_from_remote(self.vr.uuid, vrouter_type='vrouter')
        else:
            pass
        self.check_resource('delete', 'destinationCidrBlock', self.dst_cidr_block, 'query_aliyun_route_entry_local')

    def sync_route_entry(self):
        hyb_ops.sync_route_entry_from_remote(self.vr.uuid, vrouter_type='vrouter')
        condition = res_ops.gen_query_conditions('virtualRouterUuid', '=', self.vr.uuid)
        assert hyb_ops.query_aliyun_route_entry_local(condition)

    def create_ecs_instance(self, need_vpn_gateway=False, allocate_eip=False, region_id=None, connect=False):
        if need_vpn_gateway:
            self.add_datacenter_iz(check_vpn_gateway=True)
            self.get_vpc(has_vpn_gateway=True)
        elif region_id:
            self.add_datacenter_iz(region_id=region_id)
        else:
            self.add_datacenter_iz()
            self.get_vpc()
        self.get_vswitch()
        if connect:
            self.create_sg()
        else:
            self.get_sg()
        self.get_sg_rule()
        # Get ECS Instance Type
        ecs_instance_type = hyb_ops.get_ecs_instance_type_from_remote(self.iz.uuid)
        # Get ECS Image
        hyb_ops.sync_ecs_image_from_remote(self.datacenter.uuid)
        hyb_ops.sync_ecs_image_from_remote(self.datacenter.uuid, image_type='system')
        cond_image_centos = res_ops.gen_query_conditions('platform', '=', 'CentOS')
        cond_image_self = cond_image_centos[:]
        cond_image_system = cond_image_centos[:]
        cond_image_self.extend(res_ops.gen_query_conditions('type', '=', 'self'))
        cond_image_system.extend(res_ops.gen_query_conditions('type', '=', 'system'))
        ecs_image_centos_all = hyb_ops.query_ecs_image_local(cond_image_centos)
        ecs_image_centos_64 = [i for i in ecs_image_centos_all if '64' in i.name]
        ecs_image_self = hyb_ops.query_ecs_image_local(cond_image_self)
        ecs_image_system_all = hyb_ops.query_ecs_image_local(cond_image_system)
        ecs_image_system_64 = [i for i in ecs_image_system_all if '64' in i.name]
        if not allocate_eip:
            image = ecs_image_self[0] if ecs_image_self else ecs_image_centos_64[0]
            self.ecs_instance = hyb_ops.create_ecs_instance_from_ecs_image('Password123', image.uuid, self.vswitch.uuid, ecs_bandwidth=1, ecs_security_group_uuid=self.sg.uuid, 
                                                                 instance_type=ecs_instance_type[0].typeId, name='zstack-test-ecs-instance', ecs_console_password='A1B2c3')
        else:
            image = ecs_image_system_64[0]
            self.ecs_instance = hyb_ops.create_ecs_instance_from_ecs_image('Password123', image.uuid, self.vswitch.uuid, ecs_bandwidth=1, ecs_security_group_uuid=self.sg.uuid, 
                                                                 instance_type=ecs_instance_type[0].typeId, allocate_public_ip='true', name='zstack-test-ecs-instance', ecs_console_password='a1B2c3')
        time.sleep(10)
        self.ecs_create = True

    def get_ecs_instance(self):
        self.add_datacenter_iz(check_ecs=True)
        if not self.ecs_instance:
            self.create_ecs_instance()

    def stop_ecs(self):
        hyb_ops.stop_ecs_instance(self.ecs_instance.uuid)
        for _ in xrange(600):
            hyb_ops.sync_ecs_instance_from_remote(self.datacenter.uuid)
            ecs = [e for e in hyb_ops.query_ecs_instance_local() if e.ecsInstanceId == self.ecs_instance.ecsInstanceId][0]
            if ecs.ecsStatus.lower() == "stopped":
                break
            else:
                time.sleep(1)

    def wait_ecs_running(self):
        for _ in xrange(600):
            hyb_ops.sync_ecs_instance_from_remote(self.datacenter.uuid)
            ecs_local = hyb_ops.query_ecs_instance_local()
            ecs_inv = [e for e in ecs_local if e.ecsInstanceId == self.ecs_instance.ecsInstanceId][0]
            if ecs_inv.ecsStatus.lower() == "running":
                break
            else:
                time.sleep(1)

    def start_ecs(self):
        hyb_ops.start_ecs_instance(self.ecs_instance.uuid)
        time.sleep(5)
        self.wait_ecs_running()

    def reboot_ecs(self):
        hyb_ops.reboot_ecs_instance(self.ecs_instance.uuid)
        time.sleep(5)
        self.wait_ecs_running()

    def del_ecs_instance(self, remote=True):
        if remote:
#             self.stop_ecs()
            hyb_ops.sync_ecs_instance_from_remote(self.datacenter.uuid)
            condition = res_ops.gen_query_conditions('ecsInstanceId', '=', self.ecs_instance.ecsInstanceId)
            self.ecs_instance = hyb_ops.query_ecs_instance_local(condition)[0]
            hyb_ops.del_ecs_instance(self.ecs_instance.uuid)
            hyb_ops.sync_ecs_instance_from_remote(self.datacenter.uuid)
        else:
            hyb_ops.del_ecs_instance_local(self.ecs_instance.uuid)
        self.check_resource('delete', 'ecsInstanceId', self.ecs_instance.ecsInstanceId, 'query_ecs_instance_local')

    def create_ipsec(self, pri_l3_uuid, vip):
        ipsec_conntion = hyb_ops.query_ipsec_connection()
        if ipsec_conntion:
            self.ipsec = ipsec_conntion[0]
        else:
            self.ipsec = ipsec_ops.create_ipsec_connection('ipsec', pri_l3_uuid, self.vpn_gateway.publicIp, 'ZStack.Hybrid.Test123789', vip.uuid, [self.vswitch.cidrBlock],
                                                          ike_dh_group=2, ike_encryption_algorithm='3des', policy_encryption_algorithm='3des', pfs='dh-group2')

    def create_vpn_connection(self, auth_alg_1='sha1', auth_alg_2='sha1'):
        vpn_ike_config = hyb_ops.create_vpn_ike_ipsec_config(name='zstack-test-vpn-ike-config', psk='ZStack.Hybrid.Test123789', local_ip=self.vpn_gateway.publicIp, remote_ip=self.user_vpn_gateway.ip, auth_alg=auth_alg_1)
        vpn_ipsec_config = hyb_ops.create_vpn_ipsec_config(name='zstack-test-vpn-ike-config', auth_alg=auth_alg_2)
        self.vpn_connection = hyb_ops.create_vpc_vpn_connection(self.user_vpn_gateway.uuid, self.vpn_gateway.uuid, 'zstack-test-ipsec-vpn-connection', self.vswitch.cidrBlock,
                                                  self.zstack_cidrs, vpn_ike_config.uuid, vpn_ipsec_config.uuid)
        time.sleep(10)
        self.check_resource('create', 'connectionId', self.vpn_connection.connectionId, 'query_vpc_vpn_connection_local')

    def create_ipsec_vpn_connection(self, check_connectivity=True, check_status=False):
        self.vm = create_vlan_vm(os.environ.get('l3VlanNetworkName1'))
#     test_obj_dict.add_vm(self.vm)
        self.vm.check()
        vm_ip = self.vm.vm.vmNics[0].ip
        pri_l3_uuid = self.vm.vm.vmNics[0].l3NetworkUuid
        vr = test_lib.lib_find_vr_by_l3_uuid(pri_l3_uuid)[0]
        l3_uuid = test_lib.lib_find_vr_pub_nic(vr).l3NetworkUuid
        vip_existed = res_ops.query_resource(res_ops.VIP)
        # Create Vip
        if vip_existed:
            vip = vip_existed[0]
        else:
            vip = create_vip('ipsec_vip', l3_uuid).get_vip()
        cond = res_ops.gen_query_conditions('uuid', '=', pri_l3_uuid)
        self.zstack_cidrs = res_ops.query_resource(res_ops.L3_NETWORK, cond)[0].ipRanges[0].networkCidr
        self.dst_cidr_block = self.zstack_cidrs.replace('1/', '0/')
    #     _vm_ip = zstack_cidrs.replace('1/', '254/')
    #     cmd = 'ip a add dev br_eth0_1101 %s' % _vm_ip
        time.sleep(10)
        if check_connectivity:
            self.create_ecs_instance(need_vpn_gateway=True, allocate_eip=True, connect=True)
            self.get_eip(in_use=True)
        else:
            self.add_datacenter_iz(check_vpn_gateway=True)
            self.get_vpc(has_vpn_gateway=True)
            self.get_vswitch()
        self.get_vr()
        self.get_user_vpn_gateway(vip)
        self.create_vpn_connection()
        if check_status:
            condition = res_ops.gen_query_conditions('connectionId', '=', self.vpn_connection.connectionId)
            vpn_conn = hyb_ops.query_vpc_vpn_connection_local(condition)[0]
            assert vpn_conn.status == 'ike_sa_not_established'
        self.create_ipsec(pri_l3_uuid, vip)
        if check_connectivity:
            # Add route entry
            self.route_entry = hyb_ops.create_aliyun_vpc_virtualrouter_entry_remote(self.dst_cidr_block, self.vr.uuid, vrouter_type='vrouter', next_hop_type='VpnGateway', next_hop_uuid=self.vpn_gateway.uuid)
            ping_ecs_cmd = "sshpass -p password ssh -o StrictHostKeyChecking=no root@%s 'ping %s -c 5 | grep time='" % (vm_ip, self.ecs_instance.privateIpAddress)
            # ZStack VM ping Ecs
            ping_ecs_cmd_status = commands.getstatusoutput(ping_ecs_cmd)[0]
            assert ping_ecs_cmd_status == 0
            ping_vm_cmd = "sshpass -p Password123 ssh -o StrictHostKeyChecking=no root@%s 'ping %s -c 5 | grep time='" % (self.eip.eipAddress, vm_ip)
            # Ecs ping ZStack VM
            ping_vm_cmd_status = commands.getstatusoutput(ping_vm_cmd)[0]
            assert ping_vm_cmd_status == 0
            test_util.test_pass('Create hybrid IPsec Vpn Connection Test Success')

    def sync_vpn_connection(self):
        hyb_ops.sync_vpc_vpn_connection_from_remote(self.datacenter.uuid)
        condition = res_ops.gen_query_conditions('connectionId', '=', self.vpn_connection.connectionId)
        self.vpn_connection = hyb_ops.query_vpc_vpn_connection_local(condition)[0]

    def del_vpn_connection(self, remote=True):
        if remote:
            self.sync_vpn_connection()
            hyb_ops.del_vpc_vpn_connection_remote(self.vpn_connection.uuid)
            hyb_ops.sync_vpc_vpn_connection_from_remote(self.datacenter.uuid)
        else:
            hyb_ops.del_vpc_vpn_connection_local(self.vpn_connection.uuid)
        self.check_resource('delete', 'connectionId', self.vpn_connection.connectionId, 'query_vpc_vpn_connection_local')

    def get_ecs_vnc_url(self):
        vnc_url = hyb_ops.get_ecs_instance_vnc_url(self.ecs_instance.uuid).vncUrl
        req = urllib2.Request(vnc_url)
        response = urllib2.urlopen(req)
        assert response.code == 200

def create_vlan_vm(l3_name=None, disk_offering_uuids=None, system_tags=None, session_uuid = None, instance_offering_uuid = None):
    image_name = os.environ.get('imageName_net')
    image_uuid = test_lib.lib_get_image_by_name(image_name).uuid
    if not l3_name:
        l3_name = os.environ.get('l3VlanNetworkName1')

    l3_net_uuid = test_lib.lib_get_l3_by_name(l3_name).uuid
    return create_vm([l3_net_uuid], image_uuid, 'vlan_vm', \
            disk_offering_uuids, system_tags=system_tags, \
            instance_offering_uuid = instance_offering_uuid,
            session_uuid = session_uuid)

# parameter: vmname; l3_net: l3_net_description, or [l3_net_uuid,]; image_uuid:
def create_vm(l3_uuid_list, image_uuid, vm_name = None, \
        disk_offering_uuids = None, default_l3_uuid = None, \
        system_tags = None, instance_offering_uuid = None, session_uuid = None, ps_uuid=None):
    vm_creation_option = test_util.VmOption()
    conditions = res_ops.gen_query_conditions('type', '=', 'UserVm')
    if not instance_offering_uuid:
        instance_offering_uuid = res_ops.query_resource(res_ops.INSTANCE_OFFERING, conditions)[0].uuid
    vm_creation_option.set_instance_offering_uuid(instance_offering_uuid)
    vm_creation_option.set_l3_uuids(l3_uuid_list)
    vm_creation_option.set_image_uuid(image_uuid)
    vm_creation_option.set_name(vm_name)
    vm_creation_option.set_data_disk_uuids(disk_offering_uuids)
    vm_creation_option.set_default_l3_uuid(default_l3_uuid)
    vm_creation_option.set_system_tags(system_tags)
    vm_creation_option.set_session_uuid(session_uuid)
    vm_creation_option.set_ps_uuid(ps_uuid)
    vm = zstack_vm_header.ZstackTestVm()
    vm.set_creation_option(vm_creation_option)
    vm.create()
    return vm

def create_vr_vm(test_obj_dict, l3_name, session_uuid = None):
    '''
    '''
    vr_l3_uuid = test_lib.lib_get_l3_by_name(l3_name).uuid
    vrs = test_lib.lib_find_vr_by_l3_uuid(vr_l3_uuid)
    temp_vm = None
    if not vrs:
        #create temp_vm1 for getting vlan1's vr for test pf_vm portforwarding
        temp_vm = create_vlan_vm(l3_name, session_uuid = session_uuid)
        test_obj_dict.add_vm(temp_vm)
        vr = test_lib.lib_find_vr_by_vm(temp_vm.vm)[0]
        temp_vm.destroy(session_uuid)
        test_obj_dict.rm_vm(temp_vm)
    else:
        vr = vrs[0]
        if not test_lib.lib_is_vm_running(vr):
            test_lib.lib_robot_cleanup(test_obj_dict)
            test_util.test_skip('vr: %s is not running. Will skip test.' % vr.uuid)

    return vr

def create_vip(vip_name=None, l3_uuid=None, session_uuid = None):
    if not vip_name:
        vip_name = 'test vip'
    if not l3_uuid:
        l3_name = os.environ.get('l3PublicNetworkName')
        l3_uuid = test_lib.lib_get_l3_by_name(l3_name).uuid

    vip_creation_option = test_util.VipOption()
    vip_creation_option.set_name(vip_name)
    vip_creation_option.set_l3_uuid(l3_uuid)
    vip_creation_option.set_session_uuid(session_uuid)

    vip = zstack_vip_header.ZstackTestVip()
    vip.set_creation_option(vip_creation_option)
    vip.create()

    return vip
