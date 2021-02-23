# Serialized Interface Library

This libraries enables its user to create serialized and validated Juju Operator interfaces.

An interface Schema will be defined through YAML e.g:

```
type: object
properties:
  service:
    type: string
  port:
    type: number
  access-key:
    type: string
  secret-key:
    type: string
```

When our charms interchange data, this library will validate the data through the schema on both ends.

# TODO

* Figure out a clean way of distributing interfaces which use this library with their specific schemas.
* Currently only provides data to App relations, should also support unit relations.
