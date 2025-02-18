#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#
import pytest
from connector_ops.utils import Connector
from pipelines.bases import StepResult
from pipelines.builds.python_connectors import BuildConnectorImages
from pipelines.contexts import ConnectorContext
from pipelines.tests.python_connectors import UnitTests

pytestmark = [
    pytest.mark.anyio,
]


class TestUnitTests:
    @pytest.fixture
    def connector_with_setup(self):
        return Connector("source-faker")

    @pytest.fixture
    def connector_with_poetry(self):
        return Connector("destination-duckdb")

    @pytest.fixture
    def context_for_connector_with_setup(self, connector_with_setup, dagger_client):
        context = ConnectorContext(
            pipeline_name="test unit tests",
            connector=connector_with_setup,
            git_branch="test",
            git_revision="test",
            report_output_prefix="test",
            is_local=True,
            use_remote_secrets=True,
        )
        context.dagger_client = dagger_client
        context.connector_secrets = {}
        return context

    @pytest.fixture
    async def container_with_setup(self, context_for_connector_with_setup, current_platform):
        result = await BuildConnectorImages(context_for_connector_with_setup, current_platform).run()
        return result.output_artifact[current_platform]

    @pytest.fixture
    def context_for_connector_with_poetry(self, connector_with_poetry, dagger_client):
        context = ConnectorContext(
            pipeline_name="test unit tests",
            connector=connector_with_poetry,
            git_branch="test",
            git_revision="test",
            report_output_prefix="test",
            is_local=True,
            use_remote_secrets=True,
        )
        context.dagger_client = dagger_client
        context.connector_secrets = {}
        return context

    @pytest.fixture
    async def container_with_poetry(self, context_for_connector_with_poetry, current_platform):
        result = await BuildConnectorImages(context_for_connector_with_poetry, current_platform).run()
        return result.output_artifact[current_platform]

    async def test__run_for_setup_py(self, context_for_connector_with_setup, container_with_setup):
        # Assume that the tests directory is available
        result = await UnitTests(context_for_connector_with_setup)._run(container_with_setup)
        assert isinstance(result, StepResult)
        assert "test session starts" in result.stdout or "test session starts" in result.stderr
        pip_freeze_output = await result.output_artifact.with_exec(["pip", "freeze"], skip_entrypoint=True).stdout()
        assert (
            context_for_connector_with_setup.connector.technical_name in pip_freeze_output
        ), "The connector should be installed in the test environment."
        assert "pytest" in pip_freeze_output, "The pytest package should be installed in the test environment."

    async def test__run_for_poetry(self, context_for_connector_with_poetry, container_with_poetry):
        # Assume that the tests directory is available
        result = await UnitTests(context_for_connector_with_poetry).run(container_with_poetry)
        assert isinstance(result, StepResult)
        # We only check for the presence of "test session starts" because we have no guarantee that the tests will pass
        assert "test session starts" in result.stdout or "test session starts" in result.stderr, "The pytest tests should have started."
        pip_freeze_output = await result.output_artifact.with_exec(["poetry", "run", "pip", "freeze"], skip_entrypoint=True).stdout()

        assert (
            context_for_connector_with_poetry.connector.technical_name in pip_freeze_output
        ), "The connector should be installed in the test environment."
        assert "pytest" in pip_freeze_output, "The pytest package should be installed in the test environment."
