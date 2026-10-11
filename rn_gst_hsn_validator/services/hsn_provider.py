# -*- coding: utf-8 -*-
"""Level 3: authoritative HSN/SAC provider abstraction.

Default: no provider configured. Never fabricate verification results.
Do not hard-code API URLs, keys or credentials here.
"""


class HsnClassificationProvider:
    """Interface for optional external classification providers."""

    name = 'none'

    def verify_code(self, code, context=None):
        del code, context
        return {
            'success': False,
            'externally_verified': False,
            'status': 'unavailable',
            'message': 'No authoritative HSN/SAC verification provider configured.',
            'source': self.name,
            'reference': False,
            'error_code': 'provider_unavailable',
            'error_message': 'No authoritative HSN/SAC verification provider configured.',
        }


def get_provider(env=None):
    """Return the configured provider (default: unavailable)."""
    del env
    return HsnClassificationProvider()
