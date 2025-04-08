# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.3.2] - 2024-04-08

### Added

- Test for Python 3.13 (@empicano in #359)

### Fixed

- Add missing version attributes after uv switch (@empicano in #359)

## [2.3.1] - 2024-03-31

### Changed

- Switch from poetry to uv (@pavel-anchev in #350)

### Fixed

- Consistently use `sock.fileno()` to identify socket for monitoring (@airtower-luna in #357)
- Replace deprecated `get_event_loop` with `get_running_loop`

## [2.3.0] - 2024-08-07

### Added

- Implement `len(client.messages)` to return number of messages in queue (@empicano in #323)

### Changed

- Update FastAPI docs to use dependency injection (@odie5533 in #321)

## [2.2.0] - 2024-07-02

### Changed

- Bump paho-mqtt to 2.1 (@empicano in #305)
- Migrate to paho-mqtt callback v2 (@empicano in #313)

### Fixed

- Fix `Client.messages` not being reusable (@ryan-summers in #312)

## [2.1.0] - 2024-04-24

### Changed

- Migrate to paho-mqtt 2.0 (@JonathanPlasse in #286)

## [2.0.1] - 2024-03-13

## Fixed

- Configure `poetry-dynamic-versioning` to replace `__version__` and `__version_tuple__` variables (@vvanglro in #273)
- Reset internal state when connection attempt in `__aenter__` times out (@empicano in #285)

## [2.0.0] - 2024-01-15

### Added

- Test for Python 3.12 (@JonathanPlasse in #256)
- Add migration guide (@empicano in #262)

### Changed

- Switch to client-wide queue (@empicano in #262)
- Switch from black to Ruff and update dev dependencies (@JonathanPlasse in #255)
- Rename `Client.id` attribute to `identifier` (@empicano in #262)

### Removed

- Remove deprecated `connect`/`disconnect` methods (@empicano in #262)
- Remove deprecated `filtered_messages` and `unfiltered_messages` methods (@empicano in #262)
- Remove deprecated `message_retry_set` client argument (@empicano in #262)

### Fixed

- Release reusability correctly to allow consecutive calls to `__aexit__` (@spacemanspiff2007 in #263)

## [1.2.1] - 2023-09-19

### Changed

- Deprecate `connect` and `disconnect` in favor of direct calls to `__aenter__` and `__aexit__`. (@empicano in #247)

### Fixed

- Release lock in `__aexit__` only if acquired (@spacemanspiff2007 in #249)

## [1.2.0] - 2023-09-03

### Changed

- Drop support for Python 3.7. Contributed by [Felix Böhm (@empicano)](https://github.com/empicano) in [#246](https://github.com/sbtinstruments/aiomqtt/pull/246)

### Fixed

- Fix `__aenter__` failing to release lock when initial connection fails. Contributed by [Peanut (@vvanglro)](https://github.com/vvanglro) in [#245](https://github.com/sbtinstruments/aiomqtt/pull/245)

## [1.1.0] - 2023-08-03

### Added

- Expose paho's `tls_insecure` argument. Contributed by [Bob Steers (@steersbob)](https://github.com/steersbob) in [#234](https://github.com/sbtinstruments/asyncio-mqtt/pull/234)
- Add reference section generated from docstrings to documentation. Contributed by [Felix Böhm (@empicano)](https://github.com/empicano) in [#231](https://github.com/sbtinstruments/asyncio-mqtt/pull/231)

### Fixed

- Don't suppress exceptions in the client's `__aexit__`. Contributed by [Robert Resch (@edenhaus)](https://github.com/edenhaus) in [#232](https://github.com/sbtinstruments/aiomqtt/pull/232)
- Match `topic/subtopic` with `topic/subtopic/#` wildcard according to MQTT documentation. Contributed by [Bob Steers (@steersbob)](https://github.com/steersbob) in [#241](https://github.com/sbtinstruments/asyncio-mqtt/pull/241)

## [1.0.0] - 2023-06-16

### Added

- Move documentation from `README` to Sphinx. Contributed by [Felix Böhm (@empicano)](https://github.com/empicano) in [#159](https://github.com/sbtinstruments/asyncio-mqtt/pull/159)
- Add CI workflow to deploy documentation to GitHub Pages. Contributed by [Felix Böhm (@empicano)](https://github.com/empicano) in [#159](https://github.com/sbtinstruments/asyncio-mqtt/pull/159)
- Add Flow Control options to the Client-Constructor. Contributed by [Andreas Heine (@andreasheine)](https://github.com/andreasheine) in [#180](https://github.com/sbtinstruments/asyncio-mqtt/pull/180)
- Make `Client.pending_calls_threshold` public. Contributed by [Jonathan Plasse (@JonathanPlasse)](https://github.com/JonathanPlasse) in [#185](https://github.com/sbtinstruments/asyncio-mqtt/pull/185)
- Make Client a reusable (but not reentrant) context manager. Contributed by [Peanut (@vvanglro)](https://github.com/vvanglro) in [#216](https://github.com/sbtinstruments/asyncio-mqtt/pull/216)
- Make default timeout configurable. Contributed by [Scott P. (@skewty)](https://github.com/skewty) in [#192](https://github.com/sbtinstruments/asyncio-mqtt/pull/192)

### Changed

- Switch from pip to poetry for dependency management. Contributed by [Felix Böhm (@empicano)](https://github.com/empicano) in [#210](https://github.com/sbtinstruments/asyncio-mqtt/pull/210)
- Rename project from asyncio-mqtt to aiomqtt. Contributed by [Felix Böhm (@empicano)](https://github.com/empicano) in [#210](https://github.com/sbtinstruments/asyncio-mqtt/pull/210)

### Removed

- Rename `master` branch to `main`. Contributed by [Jonathan Plasse (@JonathanPlasse)](https://github.com/JonathanPlasse)

### Fixed

- Consistently use a user-provided logger. Contributed by [Roman Novatorov (@rnovatorov)](https://github.com/rnovatorov) in [#176](https://github.com/sbtinstruments/asyncio-mqtt/pull/176)

## [0.17.0] - 2023-06-12

Yanked. We recently renamed the project from asyncio-mqtt to aiomqtt. Problem is that the _old_ aiomqtt (by mossblaser) was still in use. These users suddenly experienced a breaking change when they updated from v0.1.2 to v0.17.0. Our mitigation is to yank v0.17.0 and release a v1.0.0 in it's place. It was about time for a v1.0.0 release anyhow!

## [0.16.1]

### Fixed

- Add properties in Message, the last release skipped this commit. Contributed by [Jonathan Plasse (@JonathanPlasse)](https://github.com/JonathanPlasse)

## [0.16.0]

### Added

- Add properties in Message. Contributed by [Jonathan Plasse (@JonathanPlasse)](https://github.com/JonathanPlasse) in [#166](https://github.com/sbtinstruments/asyncio-mqtt/pull/166)

### Changed

- Update Ruff and fix new lint errors. Contributed by [pre-commit-ci](https://github.com/apps/pre-commit-ci) and [Jonathan Plasse (@JonathanPlasse)](https://github.com/JonathanPlasse) in [#161](https://github.com/sbtinstruments/asyncio-mqtt/pull/161)
- Update tooling. Contributed by [pre-commit-ci](https://github.com/apps/pre-commit-ci) and [Jonathan Plasse (@JonathanPlasse)](https://github.com/JonathanPlasse) in [#184](https://github.com/sbtinstruments/asyncio-mqtt/pull/184)

### Fixed

- Fix typo in description metadata. Contributed by [(@pi-slh)](https://github.com/pi-slh) in [#162](https://github.com/sbtinstruments/asyncio-mqtt/pull/162)

## [0.15.0]

### Added

- Allow multiple message generators at the same time. Contributed by [Felix Böhm (@empicano)](https://github.com/empicano) in [#147](https://github.com/sbtinstruments/asyncio-mqtt/pull/147)

### Changed

- Simplify message filtering. Contributed by [Felix Böhm (@empicano)](https://github.com/empicano) in [#147](https://github.com/sbtinstruments/asyncio-mqtt/pull/147)
- Switch from `flake8` to `ruff` for linting. Contributed by [Jonathan Plasse (@JonathanPlasse)](https://github.com/JonathanPlasse) in [#155](https://github.com/sbtinstruments/asyncio-mqtt/pull/155)

## [0.14.0]

### Added

- Add [pre-commit](https://pre-commit.com/) for continuous integration. Contributed by [Jonathan Plasse (@JonathanPlasse)](https://github.com/JonathanPlasse) in [#144](https://github.com/sbtinstruments/asyncio-mqtt/pull/144)
- Add tests and coverage for continuous integration. Contributed by [Jonathan Plasse (@JonathanPlasse)](https://github.com/JonathanPlasse) in [#145](https://github.com/sbtinstruments/asyncio-mqtt/pull/145) and [#149](https://github.com/sbtinstruments/asyncio-mqtt/pull/149)
- Add continuous deployment to PyPI. Contributed by [Jonathan Plasse (@JonathanPlasse)](https://github.com/JonathanPlasse) in [#151](https://github.com/sbtinstruments/asyncio-mqtt/pull/151)

### Changed

- Reorder `README.md` sections in order of importance. Contributed by [Felix Böhm (@empicano)](https://github.com/empicano) in [#140](https://github.com/sbtinstruments/asyncio-mqtt/pull/140)
- Change from `setup.py` to `pyproject.toml`. Contributed by [Jonathan Plasse (@JonathanPlasse)](https://github.com/JonathanPlasse) in [#151](https://github.com/sbtinstruments/asyncio-mqtt/pull/151)

### Removed

- Drop Python 3.6 support. Contributed by [Jonathan Plasse (@JonathanPlasse)](https://github.com/JonathanPlasse) in [#146](https://github.com/sbtinstruments/asyncio-mqtt/pull/146)

### Fixed

- Fix lifespan example in `README.md`. Contributed by [Jonathan Plasse (@JonathanPlasse)](https://github.com/JonathanPlasse) and [Felix Böhm (@empicano)](https://github.com/empicano) in [#135](https://github.com/sbtinstruments/asyncio-mqtt/pull/135)

## [0.13.0]

### Added

- Add `proxy` and `tls_params` examples to `README.md`. Contributed by [Muhammad Sohaib Arshid (@Sohaib90)](https://github.com/Sohaib90) in [#128](https://github.com/sbtinstruments/asyncio-mqtt/pull/128)
- Add `proxy` option. Contributed by [Muhammad Sohaib Arshid (@Sohaib90)](https://github.com/Sohaib90) in [#127](https://github.com/sbtinstruments/asyncio-mqtt/pull/127)
- Add `tls_params` option. Contributed by [Muhammad Sohaib Arshid (@Sohaib90)](https://github.com/Sohaib90) in [#126](https://github.com/sbtinstruments/asyncio-mqtt/pull/126)
- Add WebSocket connection options. Contributed by [Dustin C. Hatch (@AdmiralNemo)](https://github.com/AdmiralNemo) in [#115](https://github.com/sbtinstruments/asyncio-mqtt/pull/115)
- Add LICENSE to tarballs produced during build. Contributed by [Stewart Haines (@stewarthaines)](https://github.com/stewarthaines) in [#107](https://github.com/sbtinstruments/asyncio-mqtt/pull/107)

### Changed

- Rework type hints of the entire project to make it compliant with mypy in strict mode. Contributed by [Jonathan Plasse (@JonathanPlasse)](https://github.com/JonathanPlasse) in [#133](https://github.com/sbtinstruments/asyncio-mqtt/pull/133)
- Rework related projects in `README.md`. Contributed by [Felix Böhm (@empicano)](https://github.com/empicano) in [#132](https://github.com/sbtinstruments/asyncio-mqtt/pull/132)
- Increase LoC count from 600 to 700 in `README.md`.

### Fixed

- Fix autocomplete for `_outgoing_call` decorator. Contributed by [Jonathan Plasse (@JonathanPlasse)](https://github.com/JonathanPlasse) in [#134](https://github.com/sbtinstruments/asyncio-mqtt/pull/134)
- Fix missing ProtocolVersion import in `README.md` and format the entire `README.md`. Contributed by [Felix Böhm (@empicano)](https://github.com/empicano) in [#130](https://github.com/sbtinstruments/asyncio-mqtt/pull/130)
- Fix 'asyncio_mqtt' has no attribute 'TLSParameters' error. Contributed by [Felix Böhm (@empicano)](https://github.com/empicano) in [#129](https://github.com/sbtinstruments/asyncio-mqtt/pull/129)
- Fix formatting in `README.md`. Contributed by [Marcelo Trylesinski (@Kludex)](https://github.com/Kludex) in [#128](https://github.com/sbtinstruments/asyncio-mqtt/pull/128)
- Fix race conditions that may cause `InvalidStateError`. Contributed by [Andreas Hangauer (@aha79)](https://github.com/aha79) in [#123](https://github.com/sbtinstruments/asyncio-mqtt/pull/123)
- Fix thread safety in socket close callback. Contributed by [Dustin C. Hatch (@AdmiralNemo)](https://github.com/AdmiralNemo) in [#114](https://github.com/sbtinstruments/asyncio-mqtt/pull/114)

## [0.12.1] - 2022-01-19

### Fixed

- Fix `TypeError` with the new `_outgoing_call` decorator.

## [0.12.0] - 2022-01-19

### Added

- Add backpressure mechanism to limit the number of concurrent outgoing calls. Contributed by [Aaron Bach (@bachya)](https://github.com/bachya) in [#101](https://github.com/sbtinstruments/asyncio-mqtt/pull/101)

## [0.11.1] - 2022-01-10

### Fixed

- Fix race condition in the "advanced example" in `README.md`. Contributed by [Steve Palmer (@steverpalmer)](https://github.com/steverpalmer) in [#93](https://github.com/sbtinstruments/asyncio-mqtt/pull/93)
- Make `password` keyword argument optional (as it always should have been). Contributed by [@Shikoruma](https://github.com/Shikoruma) in [#89](https://github.com/sbtinstruments/asyncio-mqtt/pull/89)
- Fix false positive type error from Pyright regarding `asynccontextmanager`. Contributed by [Shawn Wilsher (@sdwilsh)](https://github.com/sdwilsh) in [#87](https://github.com/sbtinstruments/asyncio-mqtt/pull/87)
- Fix type hints (mostly related to async_generator). Contributed by [@laundmo](https://github.com/laundmo) in [#86](https://github.com/sbtinstruments/asyncio-mqtt/pull/86)

## [0.11.0] - 2021-11-04

### Added

- Add link to PyPI package with a badge in `README.md`. Contributed by [Paul Barker (@pbrkr)](https://github.com/pbrkr) in [#72](https://github.com/sbtinstruments/asyncio-mqtt/pull/72)

### Changed

- Convert reason codes into English error messages. Contributed by [@CptSpaceToaster](https://github.cm/CptSpaceToaster) in [#74](https://github.com/sbtinstruments/asyncio-mqtt/pull/74)

### Fixed

- Fix event loop block caused by paho's reconnection feature. Contributed by [Martin Hjelmare (@MartinHjelmare)](https://github.cm/MartinHjelmare) in [#85](https://github.com/sbtinstruments/asyncio-mqtt/pull/85)

## [0.10.0] - 2021-07-13

### Added

- Add new parameter `socket_options` to `Client.__init__`. Contributed by [@xydan83](https://github.com/xydan83) in [#71](https://github.com/sbtinstruments/asyncio-mqtt/pull/71)
- Add new parameter `message_retry_set` to `Client.__init__`. Contributed by [@xydan83](https://github.com/xydan83) in [#69](https://github.com/sbtinstruments/asyncio-mqtt/pull/69)
- Export `ProtocolVersion` from the main module. Contributed by [André (@tropxy)](https://github.com/tropxy) in [#65](https://github.com/sbtinstruments/asyncio-mqtt/pull/65) (1/2)
- Add documentation about publishers, client arguments, etc. Contributed by [André (@tropxy)](https://github.com/tropxy) in [#65](https://github.com/sbtinstruments/asyncio-mqtt/pull/65) (2/2)

### Fixed

- Fix race condition that caused `InvalidStateError` in `force_disconnect()`. Contributed by [@functionpointer](https://github.com/functionpointer) in [#67](https://github.com/sbtinstruments/asyncio-mqtt/pull/67)

## [0.9.1] - 2021-05-13

### Fixed

- Fix handling of MQTTv5 reason codes. Contributed by [Jakob Schlyter (@jschlyter)](https://github.com/jschlyter) in [#59](https://github.com/sbtinstruments/asyncio-mqtt/pull/59)
- Account for `-1` socket handles in the close callback. Contributed by [@wrobell](https://github.com/wrobell) in [#60](https://github.com/sbtinstruments/asyncio-mqtt/pull/60)

## [0.9.0] - 2021-05-03

### Added

- Add type hints. Contributed by [Ellis Percival (@flyte)](https://github.com/flyte) in [#37](https://github.com/sbtinstruments/asyncio-mqtt/pull/37)
- Add the `keepalive`, `bind_address`, `bind_port`, `clean_start`, `properties` arguments. Contributed by [Marcin Jaworski (@yawor)](https://github.com/yawor) in [#56](https://github.com/sbtinstruments/asyncio-mqtt/pull/56)

### Fixed

- Fix Python 3.6 compatibility. Contributed by [(@fipwmaqzufheoxq92ebc)](https://github.com/fipwmaqzufheoxq92ebc) in [#57](https://github.com/sbtinstruments/asyncio-mqtt/pull/57). Note that asyncio-mqtt officially targets Python 3.7. Compatibility with 3.6 is community-driven.
- Fix "Broken pipe" error. Contributed by [Gilbert (@gilbertsmink)](https://github.com/gilbertsmink) in [#55](https://github.com/sbtinstruments/asyncio-mqtt/pull/55)
- Fix socket check when you select the WebSocket transport. Contributed by [Robert Chmielowiec (@chmielowiec)](https://github.com/chmielowiec) in [#54](https://github.com/sbtinstruments/asyncio-mqtt/pull/54)
- Fix `TypeError` on invalid username and password combination
- Check that \_misc_task is not None before trying to cancel it. Contributed by [Ellis Percival (@flyte)](https://github.com/flyte) in [#41](https://github.com/sbtinstruments/asyncio-mqtt/pull/41)
- Fix exception in `on_socket_open`: Non-thread-safe operation invoked on an event loop other than the current one. Contributed by [Ellis Percival (@flyte)](https://github.com/flyte) in [#40](https://github.com/sbtinstruments/asyncio-mqtt/pull/40)

## [0.8.1] - 2021-02-23

### Fixed

- Fix `AttributeError` when you use WebSockets. Contributed by [Robert Chmielowiec (@chmielowiec)](https://github.com/chmielowiec) in [#36](https://github.com/sbtinstruments/asyncio-mqtt/pull/36)
- Fix `asyncio.InvalidStateError` in the `_on_connect` callback. Contributed by [Maxim Shmalovsky (@vitalalerter)](https://github.com/vitalalerter) in [#31](https://github.com/sbtinstruments/asyncio-mqtt/pull/31)
- Fix "Future exception was never retrieved" on disconnect. Contributed by [Martin Hjelmare (@martinhjelmare)](https://github.com/martinhjelmare) in [#25](https://github.com/sbtinstruments/asyncio-mqtt/pull/25)
- Fix `connect` so it no longer blocks the event loop. Contributed by [Øystein Haug Olsen (@oholsen)](https://github.com/oholsen) in [#23](https://github.com/sbtinstruments/asyncio-mqtt/pull/23)

## [0.8.0] - 2020-11-09

### Added

- Add `transport` argument to `Client`. Contributed by [@opengs](https://github.com/opengs) in [#21](https://github.com/sbtinstruments/asyncio-mqtt/pull/21)
- Add `clean_session` argument to `Client`. Contributed by [@nadyka](https://github.com/madnadyka) in [#17](https://github.com/sbtinstruments/asyncio-mqtt/pull/17)

## [0.7.0] - 2020-08-04

I've tested the library for production use at SBT Instruments. This uncovered a bunch of bugs and missing features that I've addressed in this release. We are approaching a 1.0.0 release. Let me know if you want something changed before that via the issue tracker on GitHub.

### Added

- Add support for MQTTv5.
- Add `will` keyword argument to `Client`.
- Add `MqttConnectError` with specific error messages for connection failures.
- Add `Client.id` property that returns the client ID (or `None` if the client ID was not specified during construction).

### Fixed

- Fix unhandled exception error.
- Fix "Task was destroyed but it is pending" error.
- Fix compatibility with `asyncqt`'s event loop.
- Fix race condition in `Client.connect` that raised an `AttributeError`.
- Fix "[asyncio] Future exception was never retrieved" debug message.
- Fix support for python 3.6. Contributed by [Derrick Lyndon Pallas (@pallas)](https://github.com/pallas) in [#12](https://github.com/sbtinstruments/asyncio-mqtt/pull/12)

## [0.6.0] - 2020-06-26

### Changed

- No longer logs exception in `Client.__aexit__`. It's perfectly valid to exit due to, e.g., `asyncio.CancelledError` so let's not treat it as an error.

## [0.5.0] - 2020-06-08

### Added

- Add support for python 3.6. Contributed by [Derrick Lyndon Pallas (@pallas)](https://github.com/pallas) in [#7](https://github.com/sbtinstruments/asyncio-mqtt/pull/7) (1/2).
- Add `client_id` and `tls_context` keyword arguments to the `Client` constructor. Contributed by [Derrick Lyndon Pallas (@pallas)](https://github.com/pallas) in [#7](https://github.com/sbtinstruments/asyncio-mqtt/pull/7) (2/2).
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

- Add `username` and `password` keyword arguments to the `Client` constructor. Contributed by [@gluap](https://github.com/gluap) in [#1](https://github.com/sbtinstruments/asyncio-mqtt/pull/1).

### Fixed

- Fix log message context for `Client.filtered_messages`.

## [0.2.1] - 2020-04-07

### Fixed

- Fix regression with the `Client._wait_for` helper method introduced in the latest release.

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
