from setuptools import setup, find_packages

setup(
    name="rl62m02",
    version="0.1.0",
    description="RL Mesh 設備配置與控制套件",
    author="RichLink",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "pyserial>=3.5",
    ],
    entry_points={
        'console_scripts': [
            'rl62m02=rl62m02.cli:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Software Development :: Libraries",
    ],
)