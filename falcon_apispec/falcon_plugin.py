import copy
import logging
from typing import Dict, Any, Callable

from apispec import BasePlugin, yaml_utils, APISpec
from apispec.exceptions import APISpecError

log = logging.getLogger(__name__)

# Typing
Resource = object
URI = str
HTTPMethod = str
MethodMap = Dict[HTTPMethod, Callable[..., None]]


class FalconPlugin(BasePlugin):
    """APISpec plugin for Falcon"""

    def __init__(self, app, cache_enabled: bool = True):
        super(FalconPlugin, self).__init__()
        self._app = app
        self._cache_enabled = cache_enabled
        log.debug(f"cache_enabled={cache_enabled} for the parsing of the falcon's router")
        self._mapping_cached = None

    def _get_uri_falcon_details_mapping(self) -> Dict[URI, Dict[str, Any]]:
        if self._cache_enabled and self._mapping_cached:
            return self._mapping_cached
        log.info("Processing the falcon's router's tree")
        nodes = copy.copy(self._app._router._roots)  # noqa using the internal implementation of falcon

        node_processed = 0
        mapping: Dict[URI, Dict[str, Any]] = dict()
        for node in nodes:
            node_processed += 1
            log.debug(f"Processing node={node}")  # TODO remove me
            if _node_without_resource(node):
                log.debug(f"Reached a node without any resource associated to it, adding its children to the processing queue")
                nodes.extend(node.children)
                continue
            else:
                uri = node.uri_template
                resource = node.resource
                method_map = node.method_map
                nodes.extend(node.children)
            log.debug(f"Found URI='{uri}' to process")
            # FIXME Resources can have several uri and methods - this is not good.
            mapping[uri] = {
                "resource": resource,
                "methods": dict()
            }
            assert method_map
            for http_method, python_method in method_map.items():
                if python_method.__dict__.get("__module__") == "falcon.responders":
                    # Skipping the built-in method of falcon
                    continue
                mapping[uri]["methods"][http_method.lower()] = python_method
        log.debug(f"Processed count={node_processed} falcon's router node")
        self._mapping_cached = mapping
        return self._mapping_cached

    def path_helper(self, path=None, operations: dict = None, parameters: list = None, **kwargs):
        """Path helper that allows passing a Falcon resource instance."""
        uri_to_method_map = self._get_uri_falcon_details_mapping()

        if path not in uri_to_method_map:
            raise APISpecError(f"Could not find handlers for path='{path}'")
        falcon_routing_details = uri_to_method_map[path]
        resource = falcon_routing_details["resource"]
        operations.update(yaml_utils.load_operations_from_docstring(resource.__doc__) or {})

        methods = falcon_routing_details["methods"]

        for method_name, method_handler in methods.items():
            docstring_yaml = yaml_utils.load_yaml_from_docstring(method_handler.__doc__)
            operations[method_name] = docstring_yaml or dict()
        return path

    def auto_build_spec(self, spec: APISpec) -> APISpec:
        uri_to_method_map = self._get_uri_falcon_details_mapping()
        log.info("Scanning and adding all the routes known by the falcon app")
        for uri in uri_to_method_map:
            spec.path(path=uri)
        return spec


def _node_without_resource(node) -> bool:
    """Return if the falcon router's node is representing a valid falcon route"""
    # The 3 conditions seems to be overkilled because of the falcon's implementation:
    #  the assignation of these 3 attributes are tangled together in the trees construction
    return node.method_map is None or node.uri_template is None or node.resource is None
