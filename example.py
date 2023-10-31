from soaper import TestSuite, test, expect


class MyTestSuite(TestSuite):
	"""An example testing suite"""

	@test
	def my_first_test():
		expect(True).to_not_equal(False)


if __name__ == "__main__":
	MyTestSuite.run()