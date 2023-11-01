from setuptools import setup


with open("README.md", "r") as f
	long_description = f.read()


setup(
	name='soaper',
	version='0.1',
	description='A clean testing framework for python.',
	long_description=long_description,
	author='BlueishSapphire',
	author_email='blueishsapphire1@gmail.com',
	packages=['soaper'],
	install_requires=[]
)