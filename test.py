from pysoaper import TestSuite, test, expect, call_with
import math


class MathTestSuite(TestSuite):
	"""math utility"""

	class config:
		tab_arrows = True
		autorun_tests = True

	@test
	def test_addition():
		"""add two numbers"""

		add = lambda a, b: a + b

		(expect.function(add)
			.describe("given {} and {} as arguments, returns {}")
			.run_with_cases(
				call_with(0, 0).returns(0),
				call_with(1, 1).returns(2),
				call_with(1, 1).returns(3),
			))
	
	@test
	def to_raise():
		with expect.to_raise(Exception):
			raise Exception()
		
	@test
	def stdin_stdout():
		s_in = expect.with_stdin("Hello, world")
		s_out = expect.to_give_stdout("Hello, world!\n")
		with (s_in, s_out):
			print(input() + "!")

	@test
	def test_mult():
		"""multiply two numbers"""

		expect(3.14).close_to(math.pi)

	@test.skip
	def test_skip():
		"""get skipped lmao"""

		expect.fail()

	@test
	def jest():
		"""Show the diff between two strings"""

		(expect("Testing with Jest is good for you.\n")
			.to_equal("Testing your luck is bad for you."))

	@test
	def int_test():
		""""""

		expect(1).to_be_type(int)
	
	@test
	def dict_test():
		""""""

		expect({
			"x": 1,
			"y": 1,
		}).to_equal({
			"x": 1,
			"y": 1,
			"z": 1
		})

