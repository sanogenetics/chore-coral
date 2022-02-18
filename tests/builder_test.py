import datetime

from chorecoral import Builder


class TestBuilder:
    def test_basic(self, aws_iam, aws_batch, service_role, security_group, subnets):
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        """
        GIVEN a basic alpine image
        """
        manager = Builder().build(
            service_role, security_group, subnets, "alpine", "3.15.0"
        )
        """
        WHEN a single sleep job is submitted
        """
        job_id = manager.submit("Test job 1", ["sleep", "10"])
        """
        THEN it should report as a single job
        """
        jobs = tuple(manager.get_all(now))
        assert len(jobs) == 1
        assert jobs[0]["jobId"] == job_id

    # TODO with many compute environments for pagination
    # TODO with many job queues for pagination
    # TODO with invalid compute environment vCPU for errors
    # TODO with invalid compute environment memory for errors
    # TODO with invalid compute environment existing already for errors
    # TODO with invalid job queues existing already for errors
