__author__ = 'yennaco'

import testify
from pycons3rt.deployment import Deployment


class DeploymentTestCase(testify.TestCase):
    @testify.setup
    def create_deployment(self):
        self.dep = Deployment()

    @testify.teardown
    def clear_deployment(self):
        self.dep = None

    def test_default_state(self):
        testify.assert_equal(self.dep.cons3rt_role_name, None,
                             'incorrect default state')
