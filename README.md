# Serialized Data Interface Library

https://pypi.org/project/serialized-data-interface/

This libraries enables its user to create serialized and validated Juju Operator interfaces.

An interface Schema will be defined through YAML e.g:

```yaml
v1:
  provides:
    type: object
    properties:
      access-key:
        type: string
      namespace:
        type: ['string', 'null']
      port:
        type: number
      secret-key:
        type: string
      secure:
        type: boolean
      service:
        type: string
    required:
      - access-key
      - port
      - secret-key
      - secure
      - service
```

When our charms interchange data, this library will validate the data through the schema on both ends.

# Usage
In our charm metadata we would add the following lines to define our schema and the supported versions:

```yaml
provides:
  oidc-client:
    interface: oidc-client
    schema: https://raw.githubusercontent.com/canonical/operator-schemas/oidc-schemas/oidc-client.yaml
    versions: [v1]
```

In this case SDI will pull the schema from Github during deployment. If we want to deploy our charm in environments where Github isn't available we can pull the schemas during our build process by adding some lines like this in our `tox.ini` file:

```
[testenv:build]
commands =
    charmcraft build
    python3 -m serialized_data_interface.local_sdi
```

# Real World Example

* Minio with Provider Interface
  * https://github.com/canonical/minio-operator/
* Argo Controller with Requirer Interface:
  * https://github.com/canonical/argo-operators/

# TODO

* Currently only provides data to App relations, should also support unit relations.
