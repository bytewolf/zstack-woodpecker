'''

New Integration Test for hybrid.

@author: Legion
'''

import zstackwoodpecker.test_util as test_util
import zstackwoodpecker.test_lib as test_lib
import zstackwoodpecker.test_state as test_state
import time


test_obj_dict = test_state.TestStateDict()
test_stub = test_lib.lib_get_test_stub()
hybrid = test_stub.HybridObject()

def test():
    hybrid.create_ecs_instance(allocate_eip=True, connect=True)
    hybrid.get_eip(in_use=True)
    hybrid.check_eip_accessibility()
    test_util.test_pass('Create Ecs Instance with Public IP Test Success')

def env_recover():
    hybrid.del_ecs_instance()
    hybrid.del_eip()

    if hybrid.sg_create:
        time.sleep(30)
        hybrid.del_sg()

#Will be called only if exception happens in test().
def error_cleanup():
    global test_obj_dict
    test_lib.lib_error_cleanup(test_obj_dict)
