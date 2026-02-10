# History

Frederik ([@frederikaalund](https://github.com/frederikaalund)) started aiomqtt in 2020 to power bacteria sensors at [SBT Instruments](https://sbtinstruments.com). One central idea was to build on [structured concurrency principles](https://vorpus.org/blog/notes-on-structured-concurrency-or-go-statement-considered-harmful). The project was called asyncio-mqtt until 2023, when Jonathan ([@mossblaser](https://github.com/mossblaser)) graciously offered to transfer the aiomqtt name to the project.

In August 2024, Frederik handed aiomqtt over to Felix ([@empicano](https://github.com/empicano)). The biggest change since then was the switch from [paho.mqtt](https://github.com/eclipse-paho/paho.mqtt.python) to our own sans-I/O [mqtt5](https://github.com/empicano/mqtt5) protocol library, written in Rust. This change made it possible to implement automatic reconnection, flow control, and fine-grained control over message acknowledgements.
