"""Setup script for bq-analytics-agent."""
from setuptools import setup, find_packages

setup(
    name="bq-analytics-agent",
    version="1.0.0",
    description="BigQuery Data Analytics Agent System using Google Cloud Conversational Analytics API",
    author="Data Engineering Team",
    python_requires=">=3.11",
    packages=find_packages(where="."),
    package_dir={"": "."},
    install_requires=[
        "google-cloud-geminidataanalytics>=0.1.0",
        "google-cloud-storage>=2.14.0",
        "google-cloud-dataplex>=1.12.0",
        "proto-plus>=1.22.0",
        "protobuf>=4.25.0",
        "google-auth>=2.27.0",
        "streamlit>=1.31.0",
        "pandas>=2.1.0",
        "altair>=5.2.0",
        "pyyaml>=6.0",
        "pydantic>=2.5.0",
        "pygments>=2.17.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-mock>=3.12.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "provision-agents=scripts.provision_agents:main",
        ],
    },
)
