from chorecoral import Builder


class TestBuilder:
    def test_basic(self, aws_iam, aws_batch, service_role, security_group, subnets):

        Builder().build(
            service_role, security_group, subnets, "alpine", "3.15.0", "test"
        )

    # TODO with many compute environments for pagination
    # TODO with many job queues for pagination
    # TODO with invalid compute environment existing already for errors
    # TODO with invalid job queues existing already for errors
