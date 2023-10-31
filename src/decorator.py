class TestDecorator:
	TEST = "_test"
	FAILING = "_failing"
	SKIP = "_skip"

	def __call__(self, func):
		setattr(func, self.TEST, True)
		return func

	def failing(self, func):
		setattr(func, self.FAILING, True)
		return self(func)

	def skip(self, func):
		setattr(func, self.SKIP, True)
		return self(func)


test = TestDecorator()