# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing so far.

## [0.8.1] - 2021-02-23

#### Fixed

- Fix `AttributeError` when you use WebSockets.
  Contributed by [Robert Chmielowiec (@chmielowiec)](https://github.com/chmielowiec) in [#36](https://github.com/sbtinstruments/asyncio-mqtt/pull/36)

- Fix `asyncio.InvalidStateError` in the `_on_connect` callback.
  Contributed by [Maxim Shmalovsky (@vitalalerter)](https://github.com/vitalalerter) in [#31](https://github.com/sbtinstruments/asyncio-mqtt/pull/31)

- Fix "Future exception was never retrieved" on disconnect.
  Contributed by [Martin Hjelmare (@martinhjelmare)](https://github.com/martinhjelmare) in [#25](https://github.com/sbtinstruments/asyncio-mqtt/pull/25)

- Fix `connect` so it no longer blocks the event loop.
  Contributed by [Øystein Haug Olsen (@oholsen)](https://github.com/oholsen) in [#23](https://github.com/sbtinstruments/asyncio-mqtt/pull/23)

## [0.8.0] - 2020-11-09

### Added

- Add `transport` argument to `Client` 
  Contributed by [@opengs](https://github.com/opengs) in [#21](https://github.com/sbtinstruments/asyncio-mqtt/pull/21)
- Add `clean_session` argument to `Client` 
  Contributed by [@nadyka](https://github.com/madnadyka) in [#17](https://github.com/sbtinstruments/asyncio-mqtt/pull/17)


## [0.7.0] - 2020-08-04

I've tested the library for production use at SBT Instruments.
This uncovered a bunch of bugs and missing features that I've adressed
in this release. We are approaching a 1.0.0 release. Let me know
if you want something changed before that via the issue tracker on GitHub.

### Added
- Add support for MQTTv5.
- Add `will` keyword argument to `Client`.
- Add `MqttConnectError` with specific error messages for connection failures.
- Add `Client.id` property that returns the client ID (or `None` if 
  the client ID was not specified during construction).

### Fixed
- Fix unhandled exception error.
- Fix "Task was destroyed but it is pending" error.
- Fix compatibility with `asyncqt`'s event loop.
- Fix race condition in `Client.connect` that raised an `AttributeError`.
- Fix "[asyncio] Future exception was never retrieved" debug message.
- Fix support for python 3.6.
  Contributed by [Derrick Lyndon Pallas (@pallas)](https://github.com/pallas) in [#12](https://github.com/sbtinstruments/asyncio-mqtt/pull/12)

## [0.6.0] - 2020-06-26
### Changed
- No longer logs exception in `Client.__aexit__`. It's perfectly valid
  to exit due to, e.g., `asyncio.CancelledError` so let's not treat it as an
  error.

## [0.5.0] - 2020-06-08
### Added
- Add support for python 3.6.
  Contributed by [Derrick Lyndon Pallas (@pallas)](https://github.com/pallas) in [#7](https://github.com/sbtinstruments/asyncio-mqtt/pull/7) (1/2).
- Add `client_id` and `tls_context` keyword arguments to the `Client` constructor.
  Contributed by [Derrick Lyndon Pallas (@pallas)](https://github.com/pallas) in [#7](https://github.com/sbtinstruments/asyncio-mqtt/pull/7) (2/2).
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
