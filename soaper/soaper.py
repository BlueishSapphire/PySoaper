from .expect import TestFailException
from .context import context
from .decorator import TestDecorator


from functools import partial
from dataclasses import dataclass


class TestSuite:
	"""
	Testing suite parent class.

	Extend this class to make a new test suite, example:
	```py
	class MyTestSuite(TestSuite):
		"describe this test suite"

		...
	```

	You can change your subclass's config by doing the following:
	```py
	class MyTestSuite(TestSuite):
		"describe this test suite"

		class config:
			# set your config values here
			autorun_tests = True
			...
		
		...
	```
	"""

	suites = []
	is_done = False

	class color:
		"""
		Global config for the colors of the testing output.
		"""

		reset = "\x1b[m"
		test_pass = "\x1b[42m\x1b[32m"
		test_fail = "\x1b[41m\x1b[31m"
		test_skip = "\x1b[43m\x1b[33m"
		context = "\x1b[39m\x1b[2m" # "\x1b[90m"
		docstring = "\x1b[39m\x1b[2m" # "\x1b[90m"
		suite_name = "\x1b[1m\x1b[47m\x1b[37m"
		expected = "\x1b[32m"
		received = "\x1b[31m"
		line_num = "\x1b[90m"

		# round 
		result_prefix = "\x1b[49m\uE0B6"
		result_suffix = "\x1b[49m\uE0B4"

		# # sharp
		# result_prefix = "\x1b[49m\uE0B2"
		# result_suffix = "\x1b[49m\uE0B0"

		# # brackets
		# result_prefix = "\x1b[30m["
		# result_suffix = "\x1b[30m]"

		# # blank
		# result_prefix = " "
		# result_suffix = " "

	class config:
		"""
		Per-suite config to modify functionality and change the output format.
		"""

		autorun_tests = True

		show_suites = True
		show_suite_docstring = True
		show_results = True
		show_test_docstrings = False
		max_docstring_len = 70
		max_test_name_len = 40

		show_passes = True
		show_skips = True

		show_fails = True
		show_fail_docstring = True
		show_fail_message = True
		show_fail_context = True
		show_context_line_nums = True
		tab_arrows = False
		tab_width = 4

	
	def __init_subclass__(cls):
		_verify_config(cls)
		_default_config(cls)

		cls.is_done = False
		
		TestSuite.suites.append(cls)

		cls.run = partial(_run_test_suite, cls)
		
		if cls.config.autorun_tests:
			cls.run()

	@classmethod
	def run(cls, target):
		"""Run the given test suite.
		"""

		target.run()

	@classmethod
	def run_all(cls):
		"""Run all currently loaded test suites.
		"""

		[t.run() for t in cls.suites]


@dataclass
class TestResultKind:
	name: str
	color: str


class TestResult:
	Pass = TestResultKind(
		name="Pass",
		color=TestSuite.color.test_pass
	)
	Fail = TestResultKind(
		name="Fail",
		color=TestSuite.color.test_fail
	)
	Skip = TestResultKind(
		name="Skip",
		color=TestSuite.color.test_skip
	)


def _verify_config(cls):
	"""Throws an error if an invalid config key is found.
	"""

	for key in dir(cls.config):
		if key.startswith("_"):
			continue

		if not hasattr(TestSuite.config, key):
			raise Exception(f"Invalid config key \"{key}\"")
		
		cls_attr = getattr(cls.config, key)
		this_attr = getattr(TestSuite.config, key)
		if not isinstance(cls_attr, type(this_attr)):
			raise Exception(f"Invalid type for config key \"{key}\"")


def _default_config(cls):
	"""Fills any missing config values with the value from `TestSuite.config`.
	"""
	
	for key in dir(TestSuite.config):
		if key.startswith("_"):
			continue

		if not hasattr(cls.config, key):
			value = getattr(TestSuite.config, key)
			setattr(cls.config, key, value)


def _shorten_str(s: str, max_len: int):
	if max_len == None or len(s) <= max_len:
		return s
	
	return s[:max_len - len(s) - 4] + " ..."


def _split_lines(s: str):
	return [line.strip() for line in s.strip().split("\n")]


def _show_test_name(cfg: any, ctx: context, kind):
	"""Print the formatted name of a given test.
	"""
	test_name = _shorten_str(ctx.func_name, cfg.max_test_name_len)

	print(
		"├─"
		f"{kind.color}{TestSuite.color.result_prefix}"
		f"{kind.color}\x1b[30m{kind.name}"
		f"{kind.color}{TestSuite.color.result_suffix}\x1b[m "
		f"{test_name}",
		end=""
	)

	if not cfg.show_test_docstrings or len(ctx.docstring) == 0:
		print()
		return

	docstring = _shorten_str(ctx.docstring, cfg.max_docstring_len).strip()
	docstring = " / ".join([line.strip() for line in docstring.split("\n")])
	print(f"{TestSuite.color.docstring}\"{docstring}\"\x1b[m")


def _skip_test(cfg: any, ctx: context):
	_show_test_name(cfg, ctx, TestResult.Skip)


def _pass_test(cfg: any, ctx: context):
	_show_test_name(cfg, ctx, TestResult.Pass)


def _fail_test(cfg: any, ctx: context, msg: str):
	_show_test_name(cfg, ctx, TestResult.Fail)

	if cfg.show_fail_docstring and len(ctx.docstring) > 0:
		docstring = "\n   ".join(_split_lines(ctx.docstring))
		print(f"│ {TestSuite.color.context}└─\u2192 {docstring}\x1b[m")
		print("│ ")

	if cfg.show_fail_context:
		if cfg.tab_arrows:
			tab_replacement = (
				TestSuite.color.line_num
				+ "\u2192"
				+ TestSuite.color.context
				+ " " * (cfg.tab_width - 1)
			)
		else:
			tab_replacement = " " * cfg.tab_width
		
		# remove any blank lines at the end
		lines = "\n".join(ctx.lines).rstrip().split("\n")

		new_lines = []
		prev_tab_level = 0
		for l in lines:
			if len(l.strip()) == 0:
				new_lines.append(tab_replacement * prev_tab_level)
			else:
				prev_tab_level = len(l) - len(l.lstrip())
				new_lines.append(l.replace("\t", tab_replacement))
		
		if cfg.show_context_line_nums:
			for i, line in enumerate(new_lines):
				line_num = ctx.first_line_num + i + 1
				new_lines[i] = f"{TestSuite.color.line_num}{line_num: 3}|{TestSuite.color.context}{line}"

		lines_str = f"\n\x1b[m│ {TestSuite.color.context}".join(new_lines)

		print(f"│ {TestSuite.color.context}in file: ./{ctx.rel_name}:{ctx.line_num}\x1b[m")
		print(f"│ {TestSuite.color.context}{lines_str}\x1b[m")
		print("│ ")

	if cfg.show_fail_message and msg:
		msg = f"\n\x1b[m│ {TestSuite.color.context}".join(msg.split("\n"))
		print(f"\x1b[m│ {TestSuite.color.context}{msg}\x1b[m")
		print("│ ")


def _run_test(cls: any, test: callable) -> tuple[TestResultKind, bool]:
	ctx = context.from_func(cls, test)
	msg = ""
	passed = False

	# if marked as skip, then skip
	if getattr(test, TestDecorator.SKIP, False):
		if cls.config.show_skips:
			_skip_test(cls.config, ctx)
		return TestResult.Skip, False

	# run the test
	try:
		test()
		passed = True
	except TestFailException as test_fail:
		ctx = test_fail.ctx
		msg = test_fail.msg
	except BaseException as err:
		traceback = err.__traceback__.tb_next

		positions = list(traceback.tb_frame.f_code.co_positions())
		underline = positions[traceback.tb_lasti // 2]

		ctx = context.from_func(cls, test, traceback.tb_lineno, underline)
		err_name = err.__class__.__name__
		if not err.args:
			msg = f"threw \x1b[22m{TestSuite.color.received}{err_name}"
		elif isinstance(err.args[0], list):
			msg = "\n".join([e.msg for e in err.args[0]])
		else:
			msg = f"threw \x1b[22m{TestSuite.color.received}{err_name}: {err.args[0]}"

	# if marked as failing
	marked = getattr(test, TestDecorator.FAILING, False)
	if marked:
		passed = not passed

	if passed:
		if cls.config.show_passes:
			_pass_test(cls.config, ctx)
		
		return TestResult.Pass, marked
	else:
		if cls.config.show_fails:
			_fail_test(cls.config, ctx, msg)
		
		return TestResult.Fail, marked


def _run_test_suite(cls: any):
	if cls.config.show_suites:
		print(
			f"{TestSuite.color.suite_name}"
			f"{TestSuite.color.result_prefix}"
			f"{TestSuite.color.suite_name}"
			f"\x1b[30m{cls.__name__}"
			f"{TestSuite.color.suite_name}"
			f"{TestSuite.color.result_suffix}"
			"\x1b[m"
		)
		if cls.config.show_suite_docstring:
			docstring = " / ".join(_split_lines(cls.__doc__))
			print(f"│ {TestSuite.color.context}└─\u2192 {docstring}\x1b[m")

		print("│ ")

	num_passes = 0
	num_fails = 0
	num_skips = 0
	num_marked = 0

	# get all attributes of cls that do not start with an underscore
	attrs = [getattr(cls, key) for key in dir(cls) if not key.startswith("_")]
	# filter the attributes to only include functions that have the TEST attribute
	tests = [a for a in attrs if callable(a) and getattr(a, TestDecorator.TEST, False)]

	for test in tests:
		result, marked = _run_test(cls, test)

		if marked:
			num_marked += 1
		
		match result:
			case TestResult.Pass:
				num_passes += 1
			case TestResult.Fail:
				num_fails += 1
			case TestResult.Skip:
				num_skips += 1

	cls.is_done = True

	passes_str = "passes" if num_passes != 1 else "pass"
	fails_str = "fails" if num_fails != 1 else "fail"
	skips_str = "tests skipped" if num_skips != 1 else "test skipped"

	results = []

	dim_fails = "\x1b[2m" if num_fails == 0 else ""
	passes_check = "\u2713 " if num_fails == 0 else ""

	results.append(
		f"{TestSuite.color.test_pass}\x1b[49m\u2713 {num_passes} {passes_str}\x1b[m  "
		f"{dim_fails}{TestSuite.color.test_fail}\x1b[49m\u2717 {num_fails} {fails_str}\x1b[m"
	)

	if num_skips > 0:
		results.append(
			f"\x1b[2m{TestSuite.color.test_skip}\x1b[49m"
			f"! {num_skips} {skips_str}"
			"\x1b[m"
		)
	if num_marked > 0:
		results.append(
			f"\x1b[2m{TestSuite.color.test_skip}\x1b[49m"
			f"! {num_marked} test marked as failing"
			"\x1b[m"
		)
	
	print("│ ")
	print("├─ " + "\n├─ ".join(results[:-1]) + "\n╰─ " + results[-1])
	print()


