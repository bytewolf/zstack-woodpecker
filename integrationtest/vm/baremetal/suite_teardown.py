'''

Integration Test Teardown case

@author: Youyk
'''

from zstackwoodpecker import test_util
from zstackwoodpecker import clean_util
import zstacklib.utils.shell as shell
import suite_setup
import zstackwoodpecker.test_lib as test_lib

def test():
    clean_util.cleanup_all_vms_violently()
    clean_util.cleanup_none_vm_volumes_violently()
    clean_util.umount_all_primary_storages_violently()
    clean_util.cleanup_backup_storage()
    clean_util.delete_pxe()
    shell.call('pkill vbmc')
    test_lib.setup_plan.stop_node()
    test_util.test_pass('Test Teardown Success')
