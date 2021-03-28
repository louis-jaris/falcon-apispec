import logging

import falcon
import pytest
from apispec import APISpec
from apispec.exceptions import APISpecError

from falcon_apispec import FalconPlugin

logging.basicConfig(level="DEBUG")


@pytest.fixture()
def spec_factory():
    def _spec(app):
        return APISpec(
            title="Swagger Petstore",
            version="1.0.0",
            openapi_version="3.0.2",
            info={"description": "This is a sample Petstore server.  You can find out "
                                 'more about Swagger at <a href="https://swagger.io"> '
                                 "http://swagger.wordnik.com</a> or on irc.freenode.net, #swagger."
                                 'For this sample, you can use the api key "special-key" to test '
                                 "the authorization filters"
                  },
            plugins=[FalconPlugin(app)],
        )

    return _spec


@pytest.fixture()
def app():
    falcon_app = falcon.API()
    return falcon_app


class TestPathHelpers:
    def test_gettable_resource(self, app, spec_factory):
        class HelloResource:
            def on_get(self, req, resp):
                """A greeting endpoint.
                ---
                description: get a greeting
                responses:
                    200:
                        description: said hi
                """
                return "dummy"

        expected = {
            "description": "get a greeting",
            "responses": {"200": {"description": "said hi"}},
        }
        hello_resource = HelloResource()
        app.add_route("/hi", hello_resource)
        spec = spec_factory(app)
        spec.path("/hi")

        assert spec._paths["/hi"]["get"] == expected

    def test_posttable_resource(self, app, spec_factory):
        class HelloResource:
            def on_post(self, req, resp):
                """A greeting endpoint.
                ---
                description: get a greeting
                responses:
                    201:
                        description: posted something
                """
                return "hi"

        expected = {
            "description": "get a greeting",
            "responses": {"201": {"description": "posted something"}},
        }
        hello_resource = HelloResource()
        app.add_route("/hi", hello_resource)
        spec = spec_factory(app)
        spec.path("/hi")

        assert spec._paths["/hi"]["post"] == expected

    def test_resource_with_metadata(self, app, spec_factory):
        class HelloResource:
            """Greeting API.
            ---
            x-extension: global metadata
            """

        hello_resource = HelloResource()
        app.add_route("/hi", hello_resource)
        spec = spec_factory(app)
        spec.path("/hi")

        assert spec._paths["/hi"]["x-extension"] == "global metadata"

    def test_path_with_suffix(self, app, spec_factory):
        class HelloResource:
            def on_get_hello(self):
                """A greeting endpoint.
                ---
                description: get a greeting
                responses:
                    200:
                        description: said hi
                """
                return "dummy"

            def on_get(self):
                """An invalid method.
                ---
                description: this should not pass
                responses:
                    200:
                        description: said hi
                """
                return "invalid"

        expected = {
            "description": "get a greeting",
            "responses": {"200": {"description": "said hi"}},
        }

        hello_resource_with_suffix = HelloResource()
        app.add_route("/hi", hello_resource_with_suffix, suffix="hello")

        spec = spec_factory(app)
        spec.path("/hi")

        assert spec._paths["/hi"]["get"] == expected

    def test_path_with_suffix_multiple_route(self, app, spec_factory):
        class HelloResource:
            def on_get_hello(self):
                """A greeting endpoint.
                ---
                description: get a greeting
                responses:
                    200:
                        description: said hi
                """
                return "dummy"

            def on_get(self):
                """An invalid method.
                ---
                description: this should not pass
                responses:
                    200:
                        description: said hi
                """
                return "invalid"

        expected_hello = {
            "description": "get a greeting",
            "responses": {"200": {"description": "said hi"}},
        }

        expected = {
            "description": "this should not pass",
            "responses": {"200": {"description": "said hi"}},
        }

        hello_resource_with_suffix = HelloResource()
        app.add_route("/", hello_resource_with_suffix)
        app.add_route("/hello", hello_resource_with_suffix, suffix="hello")

        spec = spec_factory(app)
        spec.path("/hello")
        spec.path("/")

        assert spec._paths["/"]["get"] == expected
        assert spec._paths["/hello"]["get"] == expected_hello

    def test_resource_without_endpoint(self, app, spec_factory):
        class HelloResource:
            def on_get(self, req, resp):
                """A greeting endpoint.
                ---
                description: get a greeting
                responses:
                    200:
                        description: said hi
                """
                return "dummy"

        hello_resource = HelloResource()
        spec = spec_factory(app)

        with pytest.raises(APISpecError):
            spec.path("/hi")

        with pytest.raises(APISpecError):
            spec.path("")
