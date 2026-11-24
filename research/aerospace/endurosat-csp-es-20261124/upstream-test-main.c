#include <check.h>
#include <stdlib.h>
Suite *dedup_suite(void);
int main(void)
{
	SRunner *runner = srunner_create(dedup_suite());
	srunner_run_all(runner, CK_VERBOSE);
	int failed = srunner_ntests_failed(runner);
	srunner_free(runner);
	return failed ? EXIT_FAILURE : EXIT_SUCCESS;
}
