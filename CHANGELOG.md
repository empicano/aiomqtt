# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- No longer logs exception in `Client.__aexit__`. It's perfectly valid
  to exit due to, e.g., `asyncio.CancelledError` so let's not treat it as an
  error.

## [0.5.0] - 2020-06-08
### Added
- Add support for python 3.6.
  Contributed by [@pallas](https://github.com/gluap) in [#7](https://github.com/sbtinstruments/asyncio-mqtt/pull/7) (1/2).
- Add `client_id` and `tls_context` keyword arguments to the `Client` constructor.
  Contributed by [@pallas](https://github.com/gluap) in [#7](https://github.com/sbtinstruments/asyncio-mqtt/pull/7) (2/2).
- Add `timeout` keyword argument to both `Client.connect` and `Client.disconnect`. Default value of `10` seconds (like the other functions).

### Changed
- Propagate disconnection errors to subscribers. This enables user code to detect if a disconnect occurs. E.g., due to network errors.

## [0.4.0] - 2020-05-06
### Changed
- **BREAKING CHANGE:** Forward the [MQTTMessage](https://github.com/eclipse/paho.mqtt.python/blob/1eec03edf39128e461e6729694cf5d7c1959e5e4/src/paho/mqtt/client.py#L355)
  class from paho-mqtt instead of just the `payload`. This applies to both
  `Client.filtered_messages` and `Client.unfiltered_messages`.

  This way, user code not only gets the message `payload` but also the `topic`, `qos` level, `retain` flag, etc.

  Contributed by [Matthew Bradbury (@MBradbury)](https://github.com/MBradbury) in [#3](https://github.com/sbtinstruments/asyncio-mqtt/pull/3).

## [0.3.0] - 2020-04-13
### Added
- Add `username` and `password` keyword arguments to the `Client` constructor.
  Contributed by [@gluap](https://github.com/gluap) in [#1](https://github.com/sbtinstruments/asyncio-mqtt/pull/1).

### Fixed
- Fix log message context for `Client.filtered_messages`.

## [0.2.1] - 2020-04-07
### Fixed
- Fix regression with the `Client._wait_for` helper method introduced in the latest
  release.

## [0.2.0] - 2020-04-07
### Changed
- **BREAKING CHANGE:** Replace all uses of `asyncio.TimeoutError` with `MqttError`.
  
  Calls to `Client.subscribe`/`unsubscribe`/`publish` will no longer raise `asyncio.TimeoutError.`
    
  The new behaviour makes it easier to reason about, which exceptions the library
  throws:
  - Wrong input parameters? Raise `ValueError`.
  - Network or protocol failures? `MqttError`.
  - Broken library state? `RuntimeError`.

## [0.1.3] - 2020-04-07
### Fixed
- Fix how keyword arguments are forwarded in `Client.publish` and `Client.subscribe`.

## [0.1.2] - 2020-04-06
### Fixed
- Remove log call that was erroneously put in while debugging the latest release.

## [0.1.1] - 2020-04-06
### Fixed
- Add missing parameters to `Client.publish`.
- Fix error in `Client.publish` when paho-mqtt publishes immediately.

## [0.1.0] - 2020-04-06
Initial release.