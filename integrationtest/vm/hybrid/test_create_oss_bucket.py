'''

New Integration Test for hybrid.

@author: Quarkonics
'''

import zstackwoodpecker.test_util as test_util
import zstackwoodpecker.test_lib as test_lib
import zstackwoodpecker.test_state as test_state
import zstackwoodpecker.operations.hybrid_operations as hyb_ops
import zstackwoodpecker.operations.resource_operations as res_ops
import time
import os

test_obj_dict = test_state.TestStateDict()
ks_inv = None
bucket_inv = None

def test():
    global ks_inv
    global bucket_inv
    datacenter_type = os.getenv('datacenterType')
    ks_inv = hyb_ops.add_aliyun_key_secret('test_hybrid', 'test for hybrid', os.getenv('aliyunKey'), os.getenv('aliyunSecret'))
    datacenter_list = hyb_ops.get_datacenter_from_remote(datacenter_type)
    region_id = datacenter_list.inventories[0].regionId
    bucket_inv = hyb_ops.create_oss_bucket_remote(region_id, 'zstack-%s' % region_id, 'created-by-zstack-for-test')
    test_util.test_pass('Create OSS bucket Test Success')


def env_recover():
    global bucket_inv
    if bucket_inv:
        hyb_ops.del_oss_bucket_remote(bucket_inv.uuid)
        #hyb_ops.del_oss_file_bucket_name_in_local(bucket_inv.uuid)

    global ks_inv
    if ks_inv:
        hyb_ops.del_aliyun_key_secret(ks_inv.uuid)

#Will be called only if exception happens in test().
def error_cleanup():
    global test_obj_dict
    test_lib.lib_error_cleanup(test_obj_dict)