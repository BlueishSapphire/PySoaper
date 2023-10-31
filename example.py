from soaper import TestSuite, test


class MyTestSuite(TestSuite):
	"""An example testing suite"""

	@test
	def my_first_test():
		expect(True).to_not_equal(False)


if __name__ == "__main__":
	# because only one test suite is loaded, thsese are both the same

	MyTestSuite.run()

	TestSuite.run_all()