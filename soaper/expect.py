from .context import context


from dataclasses import dataclass
import io
import sys
import difflib


def _diff_strings(a: str, b: str):
	a_res = ""
	b_res = ""

	for i, s in enumerate(difflib.ndiff(a, b)):
		if s.startswith('- '):
			a_res += "\x1b[7m" + s[2:] + "\x1b[27m"
		elif s.startswith('+ '):
			b_res += "\x1b[7m" + s[2:] + "\x1b[27m"
		elif s.startswith('  '):
			a_res += s[2:]
			b_res += s[2:]

	return a_res, b_res


def _diff_sets(a: set, b: set):
	intersection = list(sorted(map(str, a.intersection(b))))
	a_diff = list(sorted(map(str, a.difference(b))))
	b_diff = list(sorted(map(str, b.difference(a))))
	
	a_res = "{"
	b_res = "{"

	if len(intersection) > 0:
		a_res += ", ".join(intersection)
		if len(a_diff) > 0:
			a_res += ", "
		
		b_res += ", ".join(intersection)
		if len(b_diff) > 0:
			b_res += ", "
	
	if len(a_diff) > 0:
		a_res += "\x1b[7m" + ", ".join(a_diff)
	
	if len(b_diff) > 0:
		b_res += "\x1b[7m" + ", ".join(b_diff)
	
	a_res += "\x1b[27m" + "}"
	b_res += "\x1b[27m" + "}"

	return a_res, b_res


def _diff_lists(a: list, b: list):
	a_res = []
	b_res = []

	for A, B in zip(a, b):
		if A == B:
			a_res.append(str(A))
			b_res.append(str(B))
		else:
			a_res.append("\x1b[7m" + str(A) + "\x1b[27m")
			b_res.append("\x1b[7m" + str(B) + "\x1b[27m")

	return "[" + ", ".join(a_res) + "]", "[" + ", ".join(b_res) + "]"


def _diff_dicts(cfg, plus_color, minus_color, a: dict, b: dict):
	res = "{\n"

	for key in a.keys():
		if not key in b.keys():
			res += f"{plus_color}+ {' ' * (cfg.tab_width - 2)}{key}: {a.get(key)}\x1b[m\n"
		elif a.get(key) != b.get(key):
			res += f"{plus_color}+ {' ' * (cfg.tab_width - 2)}{key}: {a.get(key)}\x1b[m\n"
			res += f"{minus_color}- {' ' * (cfg.tab_width - 2)}{key}: {b.get(key)}\x1b[m\n"
		else:
			res += f"{' ' * cfg.tab_width}{key}: {b.get(key)}\n"
	
	for key in b.keys():
		if key in a.keys(): continue

		res += f"{minus_color}- {' ' * (cfg.tab_width - 2)}{key}: {b.get(key)}\x1b[m\n"

	res += "}"
	
	return res


@dataclass
class TestFailException(Exception):
	"Signifies that a test has failed. For internal use only."

	ctx: context
	msg: str


class call_with:
	def __init__(self, *args, **kwargs):
		self.args = args
		self.kwargs = kwargs

	def returns(self, value):
		self.returns = value
		return self


_primitive_types = (bool, str, int, float, type(None))
def _get_frame_func(frame, max_depth: int = 15):
	from .soaper import TestSuite
	# put together a dict of objects to check
	# priority goes to test suites, then locals, then globals
	children = {suite.__name__: suite for suite in TestSuite.suites}
	children.update(frame.f_locals)
	children.update(frame.f_globals)

	current_layer = [{
		'parent': None,
		'children': {k: v for k, v in children.items() if not k.startswith("_")}
	}]

	for _ in range(max_depth):
		if len(current_layer) == 0: break

		new_layer = []
		for entry in current_layer:
			parent = entry['parent']
			children = entry['children']

			for key, val in children.items():
				# ignore primitives, saves a MASSIVE amount of time
				if type(val) in _primitive_types:
					continue

				# if we found the function, return it
				if callable(val) and key == frame.f_code.co_name:
					return parent, val

				# add the children of this object to the next layer
				children = {a: getattr(val, a) for a in dir(val) if hasattr(val, a) and not a.startswith("_")}
				new_layer.append({
					'parent': val,
					'children': children
				})

		# step down to the next layer
		current_layer = new_layer

	# didn't find anything
	return None, None


class expect:
	def __init__(self, value: any, _frame = None, _parent = None):
		self.value = value
		self._frame = _frame or sys._getframe().f_back
		self._parent = _parent

	@property
	def parent(self):
		"""Get the parent class of the method that called `expect.__init__`.
		"""
		if self._parent is None:
			self._parent, _ = _get_frame_func(self._frame)

		return self._parent

	@property
	def _ctx(self):
		"""Get the current context of this expect object.
		"""
		assert self.parent is not None
		return context.from_frame(self.parent, self._frame)
	
	def _fail(self, msg: str):
		"""Fail the current test.
		"""
		frame = self._frame

		positions = list(frame.f_code.co_positions())
		underline = positions[frame.f_lasti // 2]

		raise TestFailException(
			context.from_frame(self.parent, frame, frame.f_lineno, underline),
			msg or "Internal failure",
		)

	@classmethod
	def fail(cls, msg: str = "Explicit failure"):
		"""Fail the current test.
		"""
		raise expect._get_fail(sys._getframe().f_back, msg)

	@classmethod
	def _get_fail(cls, frame, msg: str = None):
		"""Return an exception that will fail the current test if raised.
		"""
		parent = _get_frame_func(frame)

		positions = list(frame.f_code.co_positions())
		underline = positions[frame.f_lasti // 2]

		return TestFailException(
			context.from_frame(parent[0], frame, frame.f_lineno, underline),
			msg,
		)

	@classmethod
	def fail_if(condition: bool, msg: str = "Explicit failure"):
		"""Fail the current test if a condition is true.
		"""
		if condition:
			expect.fail(msg)

	class function:
		"""Used with `call_with` to run several test cases on a function.
		"""

		def __init__(self, fn: callable):
			self.fn = fn

		def describe(self, desc: str):
			"""Give a description of the function using {} to take arguments.
			"""
			self.desc = desc
			return self

		def run_with_cases(self, *cases: list[call_with]):
			"""Runs a set of test cases on the given function.
			"""
			fails = []

			for c in cases:
				try:
					res = self.fn(*c.args, **c.kwargs)

					if res != c.returns:
						msg = self.desc.format(*c.args, c.returns)
						fails.append(expect._get_fail(sys._getframe(), msg))
				except TestFailException as test_fail:
					fails.append(test_fail)
				except BaseException as err:
					traceback = err.__traceback__

					msg = err.__class__.__name__ + ": " + err.args[0]

					fail = expect._get_fail(sys._getframe(), msg)
					fail.ctx._line_num = traceback.tb_lineno - 1
					fails.append(fail)

			if fails:
				raise Exception(fails)

	class with_stdin:
		"""Use inside a with statement to simulate stdin.
		"""
		def __init__(self, text: str):
			self.buffer = io.StringIO(text)
		def __enter__(self):
			sys.stdin = self.buffer
		def __exit__(self, err_type, err_value, traceback):
			sys.stdin = sys.__stdin__
	
	class to_give_stdout:
		"""Use inside a with statement to capture stdout.
		"""
		def __init__(self, text: str):
			self.buffer = io.StringIO()
			self.expected = text

			self._frame = sys._getframe().f_back
			self._parent, _ = _get_frame_func(self._frame)
		def __enter__(self):
			sys.stdout = self.buffer
		def __exit__(self, err_type, err_value, traceback):
			sys.stdout = sys.__stdout__
			buf = self.buffer.getvalue()
			if self.expected != buf:
				frame = self._frame

				positions = list(frame.f_code.co_positions())
				underline = positions[frame.f_lasti // 2]

				a, b = _diff_strings(repr(self.expected)[1:-1], repr(buf)[1:-1])
				raise TestFailException(
					context.from_frame(self._parent, frame, frame.f_lineno, underline),
					"expected stdout to equal\n\n"
					f"\x1b[22m{self._parent.color.expected}+ {a}\n"
					f"\x1b[22m{self._parent.color.received}- {b}"
				)
	
	class to_raise:
		"""Use inside a with statement.
		"""
		def __init__(self, exception):
			self.exc = exception

			frame = sys._getframe().f_back
			parent, _ = _get_frame_func(frame)
			self.expect = expect(None, frame, parent)
		def __enter__(self): pass
		def __exit__(self, err_type, err_value, traceback):
			if err_type != self.exc:
				self.expect._fail(f"expected to raise {self.exc.__name__}")
			else:
				return True
	
	class to_not_raise:
		"""Use inside a with statement.
		"""
		def __init__(self, exception):
			self.exc = exception

			frame = sys._getframe().f_back
			parent, _ = _get_frame_func(frame)
			self.expect = expect(None, frame, parent)
		def __enter__(self): pass
		def __exit__(self, err_type, err_value, traceback):
			if self.err_type == self.exc:
				err_name = self.exc.__class__.__name__
				self.expect._fail(f"expected not to raise {err_name}")
	
	def truthy(self):
		if self.value: return
		self._fail("expected a truthy value")
	
	def falsy(self):
		if not self.value: return
		self._fail("expected a falsy value")
	
	def to_equal(self, value):
		if self.value == value: return
		match self.value:
			case str():
				name = "strings"
				a, b = _diff_strings(repr(self.value)[1:-1], repr(value)[1:-1])
			case set():
				name = "sets"
				a, b = _diff_sets(self.value, value)
			case list():
				name = "lists"
				a, b = _diff_lists(self.value, value)
			case dict():
				self._fail(
					f"expected dicts to equal\n\n"
					+ "dict " + _diff_dicts(
						self.parent.config,
						self.parent.color.expected + "\x1b[22m",
						self.parent.color.received + "\x1b[22m",
						self.value,
						value
					)
				)
			case _:
				name = "values"
				a = self.value
				b = value
		self._fail(
			f"expected {name} to equal\n\n"
			f"\x1b[22m{self.parent.color.expected}+ {a}\n"
			f"\x1b[22m{self.parent.color.received}- {b}"
		)
	
	def to_not_equal(self, value):
		if self.value != value: return
		self._fail(
			"expected values to not equal\n\n"
			f"expected: \x1b[22m{self.parent.color.expected}not {self.value}\n"
			f"received: \x1b[22m{self.parent.color.received}{value}"
		)
	
	def to_be(self, value):
		if self.value is value: return
		self._fail(
			"expected values to be the same\n\n"
			f"\x1b[22m{self.parent.color.expected}+ {self.value}\n"
			f"\x1b[22m{self.parent.color.received}- {value}"
		)
	
	def to_not_be(self, value):
		if self.value is not value: return
		self._fail(
			"expected values to not be the same\n\n"
			f"expected: \x1b[22m{self.parent.color.expected}not {self.value}\n"
			f"received: \x1b[22m{self.parent.color.received}{value}"
		)
	
	def less_than(self, value):
		if self.value < value: return
		self._fail(
			f"expected: \x1b[22m{self.parent.color.expected}< {self.value}\n"
			f"received: \x1b[22m{self.parent.color.received} {value}"
		)
	
	def less_than_or_equal(self, value):
		if self.value <= value: return
		self._fail(
			f"expected: \x1b[22m{self.parent.color.expected}<= {self.value}\n"
			f"received: \x1b[22m{self.parent.color.received} {value}"
		)
	
	def greater_than(self, value):
		if self.value > value: return
		self._fail(
			f"expected: \x1b[22m{self.parent.color.expected}> {self.value}\n"
			f"received: \x1b[22m{self.parent.color.received} {value}"
		)
	
	def greater_than_or_equal(self, value):
		if self.value >= value: return
		self._fail(
			f"expected: \x1b[22m{self.parent.color.expected}>= {self.value}\n"
			f"received: \x1b[22m{self.parent.color.received} {value}"
		)
	
	def close_to(self, value, precision: int = 2):
		diff = float(abs(self.value - value))
		max_diff = float((10 ** -precision) / 2)
		if diff < max_diff: return
		self._fail(
			f"expected: \x1b[22m{self.parent.color.expected}{self.value}\x1b[m\n"
			f"received: \x1b[22m{self.parent.color.received}{value}\x1b[m\n"
			"\n"
			f"expected precision: \x1b[22m{precision}\x1b[m\n"
			f"expected difference: \x1b[22m< {self.parent.color.expected}{max_diff}\x1b[m\n"
			f"received difference: \x1b[22m{self.parent.color.received}{diff}\x1b[m"
		)

	def to_be_type(self, value):
		if isinstance(self.value, value): return
		self._fail(
			f"expected type: \x1b[22m{self.parent.color.expected}{type(self.value)}\n"
			f"received type: \x1b[22m{self.parent.color.received}{value}"
		)
	
	def to_have_attr(self, name: str, value = None):
		if not hasattr(self.value, name):
			self._fail(
				f"expected attribute: {name}\n"
				f"recieved attributes: {dir(self.value)}]"
			)
		if value is not None and getattr(self.value, name, None) != value:
			self._fail(
				"\n"
				f"expected value: {value}\n"
				f"recieved value: {getattr(self.value, name, None)}"
			)
