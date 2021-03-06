'''

New Integration Test for License.

@author: Quarkonics
'''

import zstackwoodpecker.test_util as test_util
import zstackwoodpecker.test_state as test_state
import zstackwoodpecker.test_lib as test_lib
import zstackwoodpecker.operations.license_operations as lic_ops
import time
import datetime
import os

test_stub = test_lib.lib_get_test_stub()

def test():
    test_stub.reload_default_license()
    test_util.test_logger('Check default community license')
    test_stub.check_license(None, None, 2147483647, False, 'Community')

    test_util.test_logger('Load and Check Hybrid license with 2 day and 1 HOST')
    file_path = test_stub.gen_license('woodpecker', 'woodpecker@zstack.io', '2', 'Hybrid', '', '1')
    test_stub.load_license(file_path)
    issued_date = test_stub.get_license_info().issuedDate
    expired_date = test_stub.license_date_cal(issued_date, 86400 * 2)
    test_stub.check_license("woodpecker@zstack.io", None, 1, False, 'Hybrid', issued_date=issued_date, expired_date=expired_date)

    test_util.test_logger('Load and Check Hybrid license with 1 day and 1 CPU')
    file_path = test_stub.gen_license('woodpecker', 'woodpecker@zstack.io', '1', 'Hybrid', '1', '')
    test_stub.load_license(file_path)
    issued_date = test_stub.get_license_info().issuedDate
    expired_date = test_stub.license_date_cal(issued_date, 86400 * 1)
    test_stub.check_license("woodpecker@zstack.io", 1, None, False, 'Hybrid', issued_date=issued_date, expired_date=expired_date)


    test_util.test_logger('Load and Check Hybrid license with 2 day and 10 HOST')
    file_path = test_stub.gen_license('woodpecker', 'woodpecker@zstack.io', '2', 'Hybrid', '', '10')
    test_stub.load_license(file_path)
    issued_date = test_stub.get_license_info().issuedDate
    expired_date = test_stub.license_date_cal(issued_date, 86400 * 2)
    test_stub.check_license("woodpecker@zstack.io", None, 10, False, 'Hybrid', issued_date=issued_date, expired_date=expired_date)

    test_util.test_logger('Load and Check Hybrid license with 3 day and 10 CPU')
    file_path = test_stub.gen_license('woodpecker', 'woodpecker@zstack.io', '3', 'Hybrid', '10', '')
    test_stub.load_license(file_path)
    issued_date = test_stub.get_license_info().issuedDate
    expired_date = test_stub.license_date_cal(issued_date, 86400 * 3)
    test_stub.check_license("woodpecker@zstack.io", 10, None, False, 'Hybrid', issued_date=issued_date, expired_date=expired_date)

    test_util.test_logger('Load and Check Hybrid license with 2 day and 5 CPU')
    file_path = test_stub.gen_license('woodpecker', 'woodpecker@zstack.io', '2', 'Hybrid', '5', '')
    test_stub.load_license(file_path)
    issued_date = test_stub.get_license_info().issuedDate
    expired_date = test_stub.license_date_cal(issued_date, 86400 * 2)
    test_stub.check_license("woodpecker@zstack.io", 5, None, False, 'Hybrid', issued_date=issued_date, expired_date=expired_date)

    test_util.test_logger('Load and Check Hybrid license with 2 day and 2 HOST')
    file_path = test_stub.gen_license('woodpecker', 'woodpecker@zstack.io', '2', 'Hybrid', '', '2')
    test_stub.load_license(file_path)
    issued_date = test_stub.get_license_info().issuedDate
    expired_date = test_stub.license_date_cal(issued_date, 86400 * 2)
    test_stub.check_license("woodpecker@zstack.io", None, 2, False, 'Hybrid', issued_date=issued_date, expired_date=expired_date)

    test_util.test_logger('Load and Check Hybrid license with 3 day and 2 HOST')
    file_path = test_stub.gen_license('woodpecker', 'woodpecker@zstack.io', '3', 'Hybrid', '', '1')
    test_stub.load_license(file_path)
    issued_date = test_stub.get_license_info().issuedDate
    expired_date = test_stub.license_date_cal(issued_date, 86400 * 3)
    test_stub.check_license("woodpecker@zstack.io", None, 1, False, 'Hybrid', issued_date=issued_date, expired_date=expired_date)

    test_util.test_pass('Check License Test Success')

#Will be called only if exception happens in test().
def error_cleanup():
    test_lib.lib_error_cleanup(test_obj_dict)
