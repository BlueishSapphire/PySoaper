from dataclasses import dataclass
from os.path import basename, relpath


def _highlight_section(
	lines: list[str],
	start_line: int,
	start_col: int,
	end_line: int,
	end_col: int
) -> None:
	start_highlight = "\x1b[31m"
	end_highlight = "\x1b[39m"

	if start_line == end_line:
		lines[start_line] = (
			end_highlight
			+ lines[start_line][:start_col]
			+ start_highlight
			+ lines[start_line][start_col:end_col]
			+ end_highlight
			+ lines[start_line][end_col:]
		)
	else:
		for i in range(len(lines)):
			if i == start_line:
				lines[i] = (
					end_highlight
					+ lines[i][:start_col]
					+ start_highlight
					+ lines[i][start_col:]
					+ end_highlight
				)
			elif i == end_line:
				lines[i] = (
					start_highlight
					+ lines[i][:end_col]
					+ end_highlight
					+ lines[i][end_col:]
					+ end_highlight
				)
			elif i > start_line and i < end_line:
				lines[i] = start_highlight + lines[i] + end_highlight


@dataclass
class context:
	def __init__(self, parent: any, func: callable, line_num: int = None, underline: tuple[int, int, int, int] = None):
		assert callable(func)
		self.parent = parent
		self.func = func
		self._line_num = line_num

		self._err_start_row = underline[0] if underline else None
		self._err_start_col = underline[2] if underline else None
		self._err_end_row = underline[1] if underline else None
		self._err_end_col = underline[3] if underline else None

	# initializers

	@classmethod
	def from_frame(self, cls, frame, line_num: int = None, underline = None):
		func_name = frame.f_code.co_name
		assert frame is not None and hasattr(cls, func_name)
		return context(cls, getattr(cls, func_name), line_num or frame.f_lineno, underline)

	@classmethod
	def from_func(self, cls, func: callable, line_num: int = None, underline = None):
		assert callable(func)
		return context(cls, func, line_num, underline)

	# properties

	@property
	def func_name(self) -> str:
		return self.func.__name__

	@property
	def file_name(self) -> str:
		return self.func.__code__.co_filename

	@property
	def first_line_num(self) -> int:
		return self.func.__code__.co_firstlineno

	@property
	def line_num(self) -> int:
		return self._line_num or self.func.__code__.co_firstlineno
	
	@property
	def docstring(self) -> str:
		return getattr(self.func, "__doc__", "") or ""

	@property
	def base_name(self) -> str:
		return basename(self.file_name)
	
	@property
	def rel_name(self) -> str:
		return relpath(self.file_name)

	@property
	def lines(self) -> str:
		first_line_num = self.first_line_num
		last_line_num = self.line_num

		with open(self.file_name, "r") as f:
			lines = [l.rstrip() for l in f.readlines()]

		if self._err_start_row is not None:
			_highlight_section(
				lines,
				self._err_start_row - 1,
				self._err_start_col,
				self._err_end_row - 1,
				self._err_end_col,
			)

		lines = lines[first_line_num:last_line_num + 1]
		lines = list(map(str.rstrip, lines))

		if len(lines) > 10:
			lines = lines[-10:]

		return lines




