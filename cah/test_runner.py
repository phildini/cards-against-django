from django.test.simple import DjangoTestSuiteRunner
from django.conf import settings


class TestSuiteRunner(DjangoTestSuiteRunner):
    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        """Runs local app tests only.

        Will still run tests provided from the command line.
        """

        if not test_labels:
            test_labels = settings.LOCAL_APPS

        return super(TestSuiteRunner, self).run_tests(
            test_labels,
            extra_tests,
            **kwargs
        )
