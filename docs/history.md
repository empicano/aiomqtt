# History

Frederik ([@frederikaalund](https://github.com/frederikaalund)) started aiomqtt in 2020 to power bacteria sensors at [SBT Instruments](https://sbtinstruments.com). One central idea was to build on [structured concurrency principles](https://vorpus.org/blog/notes-on-structured-concurrency-or-go-statement-considered-harmful). The project was called asyncio-mqtt until 2023, when Jonathan ([@mossblaser](https://github.com/mossblaser)) graciously offered to transfer the aiomqtt name to the project.

In August 2024, Frederik handed aiomqtt over to Felix ([@empicano](https://github.com/empicano)). aiomqtt's sole dependency is now [mqtt5](https://github.com/empicano/mqtt5), a sans-I/O MQTT 5.0 protocol library written in Rust.
