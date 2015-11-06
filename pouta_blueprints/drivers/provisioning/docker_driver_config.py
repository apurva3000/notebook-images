CONFIG = {
    'schema': {
        'type': 'object',
        'title': 'Comment',
        'description': 'Description',
        'required': [
            'name',
        ],
        'properties': {
            'name': {
                'type': 'string'
            },
            'description': {
                'type': 'string'
            },
            'docker_image': {
                'type': 'string',
                'enum': [
                ]
            },
            'internal_port': {
                'type': 'integer'
            },
            'launch_command': {
                'type': 'string',
            },
            'memory_limit': {
                'type': 'string',
                'default': '512m',
            },
            'consumed_slots': {
                'type': 'integer',
                'default': '1',
            },
            'maximum_instances_per_user': {
                'type': 'integer',
                'title': 'Maximum instances per user',
                'default': 1,
            },
            'maximum_lifetime': {
                'type': 'string',
                'title': 'Maximum life-time (days hours mins secs)',
                'default': '0d0h0m0s',
                'pattern': '^(\d+d\s?)?(\d{1,2}h\s?)?(\d{1,2}m\s?)?(\d{1,2}s\s?)?$',
                'validationMessage': 'Value should be in format -d-h-m-s'
            },
            'cost_multiplier': {
                'type': 'number',
                'title': 'Cost multiplier (default 1.0)',
                'default': 1.0,
            },
            'needs_ssh_keys': {
                'type': 'boolean',
                'title': 'Needs ssh-keys to access',
                'default': False,
            },
            'proxy_no_rewrite': {
                'type': 'boolean',
                'title': 'Skip rewriting and redirecting the proxy url',
                'default': False,
            },
            'environment_vars': {
                'type': 'string',
                'title': 'environment variables for docker, separated by space',
                'default': '',
            },
        }
    },
    'form': [
        {
            'type': 'help',
            'helpvalue': '<h4>Docker instance config</h4>'
        },
        'name',
        'description',
        'docker_image',
        'internal_port',
        'launch_command',
        'environment_vars',
        'memory_limit',
        'consumed_slots',
        'maximum_instances_per_user',
        'maximum_lifetime',
        'cost_multiplier',
        'proxy_no_rewrite',
    ],
    'model': {
        'name': 'docker-rstudio',
        'description': 'docker blueprint',
        'docker_image': 'rocker.rstudio.img',
        'internal_port': 8787,
        'memory_limit': '512m',
        'cost_multiplier': 0.0,
        'consumed_slots': 1,
        'needs_ssh_keys': False,
        'proxy_no_rewrite': False,
    }
}
