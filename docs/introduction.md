# Introduction

This documentation aims to cover everything you need to know to use aiomqtt in your projects. We expect some knowledge of MQTT and asyncio, but we try to explain things as clearly as possible. If you get stuck, don't hesitate to start a new discussion on GitHub. We're happy to help!

If you're new to MQTT, we recommend reading the [HiveMQ MQTT essentials](https://www.hivemq.com/mqtt-essentials/) guide as an introduction. Afterward, the [OASIS specification](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html) is a great reference. For asyncio, we recommend the [RealPython asyncio walkthrough](https://realpython.com/async-io-python/) as an introduction and the [asyncio docs](https://docs.python.org/3/library/asyncio.html) as a reference.

Thanks for being part of our community! ☀️

```{admonition} A little bit of history
Frederik ([@frederikaalund](https://github.com/frederikaalund)) started aiomqtt in 2020 to power bacteria sensors at [SBT Instruments](https://sbtinstruments.com/). One of his central ideas for the project was to use [structured concurrency](https://vorpus.org/blog/notes-on-structured-concurrency-or-go-statement-considered-harmful/) principles. The project was called asyncio-mqtt until 2023, when Jonathan ([@mossblaser](https://github.com/mossblaser)) graciously offered to pass along the aiomqtt name. In August 2024, Frederik passed on aiomqtt's stewardship to Felix ([@empicano](https://github.com/empicano)) due to changing priorities and to better serve the project overall.
```
