# Copyright 2021 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging
from itertools import chain

import werkzeug

from odoo import http, models, tools

from ..registry import EndpointRegistry

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _endpoint_route_registry(cls, env):
        return EndpointRegistry.registry_for(env.cr)

    def _generate_routing_rules(self, modules, converters):
        # Override to inject custom endpoint rules.
        return chain(
            super()._generate_routing_rules(modules, converters),
            self._endpoint_routing_rules(),
        )

    @classmethod
    def _endpoint_routing_rules(cls):
        """Yield custom endpoint rules"""
        e_registry = cls._endpoint_route_registry(http.request.env)
        for endpoint_rule in e_registry.get_rules():
            _logger.debug("LOADING %s", endpoint_rule)
            endpoint = endpoint_rule.endpoint
            
            # append PATCH method in to endpoint.routing.methods
            if "PATCH" not in endpoint.routing["methods"]:
                endpoint.routing["methods"].append("PATCH")

            for url in endpoint_rule.routing["routes"]:
                yield (url, endpoint)

    # @tools.ormcache('key', cache='routing')
    # def routing_map(self, key=None):
    #     last_version = self._get_routing_map_last_version(http.request.env)
    #     if not hasattr(self, "_routing_map"):
    #         # routing map just initialized, store last update for this env
    #         _logger.error(self)
    #         setattr(self, '_endpoint_route_last_version', last_version)
    #         # self._endpoint_route_last_version = last_version
    #     elif self._endpoint_route_last_version < last_version:
    #         _logger.info("Endpoint registry updated, reset routing map")
    #         self._routing_map = {}
    #         self._rewrite_len = {}
    #         self._endpoint_route_last_version = last_version
    #     return super().routing_map(key=key)

    @classmethod
    def _get_routing_map_last_version(cls, env):
        return cls._endpoint_route_registry(env).last_version()

    @classmethod
    def _clear_routing_map(cls):
        res = super()._clear_routing_map()
        if hasattr(cls, "_endpoint_route_last_version"):
            cls._endpoint_route_last_version = 0
        return res

    @classmethod
    def _auth_method_user_endpoint(cls):
        """Special method for user auth which raises Unauthorized when needed.

        If you get an HTTP request (instead of a JSON one),
        the standard `user` method raises `SessionExpiredException`
        when there's no user session.
        This leads to a redirect to `/web/login`
        which is not desiderable for technical endpoints.

        This method makes sure that no matter the type of request we get,
        a proper exception is raised.
        """
        try:
            cls._auth_method_user()
        except http.SessionExpiredException as err:
            raise werkzeug.exceptions.Unauthorized() from err
