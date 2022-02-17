from chorecoral import Builder


class TestBuilder:
    def test_basic(self, aws_iam, aws_batch, service_role, security_group, subnets):

        Builder().build(
            service_role, security_group, subnets, "alpine", "3.15.0", "test"
        )
