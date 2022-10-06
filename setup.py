from setuptools import setup

setup(name='autosbatch',
      version='0.0.1',
      description='Submit slurm job in python',
      url='https://github.com/luptior/pysbatch',
      author='Jianhua Wang',
      author_email='jianhua.mert@gmail.com',
      license='MIT',
      packages=['autosbatch'],
      zip_safe=False,
      classifiers=[
          # How mature is this project?
          'Development Status :: 4 - Beta',

          # Indicate who your project is intended for
          'Intended Audience :: Science/Research',
          'Topic :: Scientific/Engineering',

          # Pick your license as you wish (should match "license" above)
           'License :: OSI Approved :: MIT License',

          # Specify the Python versions you support here. In particular, ensure
          # that you indicate whether you support Python 2, Python 3 or both.
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',],
      keywords='slurm batch job submit',
      python_requires='>=3.5',
      install_requires=['pandas>=1.3.4']
     )