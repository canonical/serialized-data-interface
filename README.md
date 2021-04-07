# Serialized Interface Library

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

# Real World Example

* Minio with Provider Interface
  * https://github.com/canonical/minio-operator/
* Argo Controller with Requirer Interface:
  * https://github.com/canonical/argo-operators/

# TODO

* Currently only provides data to App relations, should also support unit relations.
