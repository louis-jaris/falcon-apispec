import logging

import falcon
import pytest
from apispec import APISpec
from apispec.exceptions import APISpecError

from falcon_apispec import FalconPlugin

logging.basicConfig(level="DEBUG")


def build_spec(falcon_plugin):
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
        plugins=[falcon_plugin],
    )


@pytest.fixture()
def app():
    falcon_app = falcon.API()
    return falcon_app


class TestPathHelpers:
    def test_gettable_resource(self, app):
        falcon_plugin = FalconPlugin(app)

        class HelloResource:
            def on_get(self, req, resp):
                """A greeting endpoint.
                ---
                description: get a greeting
                summary: greeting
                responses:
                    200:
                        description: said hi
                """
                return "dummy"

        expected = {
            "summary": "greeting",
            "description": "get a greeting",
            "responses": {"200": {"description": "said hi"}},
        }
        hello_resource = HelloResource()
        app.add_route("/hi", hello_resource)
        spec = build_spec(falcon_plugin)
        falcon_plugin.auto_build_spec(spec)

        assert spec._paths["/hi"]["get"] == expected

    def test_posttable_resource(self, app):
        falcon_plugin = FalconPlugin(app)

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
        spec = build_spec(falcon_plugin)
        falcon_plugin.auto_build_spec(spec)

        assert spec._paths["/hi"]["post"] == expected

    def test_resource_with_metadata(self, app):
        falcon_plugin = FalconPlugin(app)

        class HelloResource:
            """Greeting API.
            ---
            x-extension: global metadata
            """

        hello_resource = HelloResource()
        app.add_route("/hi", hello_resource)
        spec = build_spec(falcon_plugin)
        falcon_plugin.auto_build_spec(spec)

        assert spec._paths["/hi"]["x-extension"] == "global metadata"

    def test_path_with_suffix(self, app):
        falcon_plugin = FalconPlugin(app)

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

            def on_post(self):
                """Some post method to save stuff
                ---
                summary: it does save stuff
                description: this is saving stuff somewhere
                responses:
                    200:
                        description: Everything went well
                """
                return "Ok, the stuff is being saved"

        expected = {
            "description": "get a greeting",
            "responses": {"200": {"description": "said hi"}},
        }

        hello_resource_with_suffix = HelloResource()
        app.add_route("/hi", hello_resource_with_suffix, suffix="hello")
        app.add_route("/something", hello_resource_with_suffix)

        spec = build_spec(falcon_plugin)
        falcon_plugin.auto_build_spec(spec)

        assert spec._paths["/hi"]["get"] == expected
        print(" ")
        print(spec.to_yaml())

    def test_path_with_suffix_multiple_route(self, app):
        falcon_plugin = FalconPlugin(app)

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

        spec = build_spec(falcon_plugin)
        falcon_plugin.auto_build_spec(spec)

        assert spec._paths["/"]["get"] == expected
        assert spec._paths["/hello"]["get"] == expected_hello

    def test_resource_without_endpoint(self, app):
        falcon_plugin = FalconPlugin(app)

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
        spec = build_spec(falcon_plugin)
        falcon_plugin.auto_build_spec(spec)

        with pytest.raises(APISpecError):
            spec.path("/hi")

        with pytest.raises(APISpecError):
            spec.path("")
