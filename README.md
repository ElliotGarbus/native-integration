# native-integration

**A convention for Python packages to declare what they need from a native mobile app build.**

> **Status: being redesigned.** The next version is being worked out in
> [discussion #1](https://github.com/ElliotGarbus/native-integration/discussions/1).
> The previous specification, its reference reader and conformance corpus, and
> every earlier round are kept in [`archive/`](archive/README.md).

## The problem

`pip install` faithfully installs what a wheel contains — and has no convention
for translating a dependency's Android or iOS integration requirements into the
application's Gradle or Xcode configuration.

Take [KivMob](https://github.com/MichaelStott/KivMob), AdMob support for Kivy on
PyPI. Installing it works. Then you hand-copy a screenful of settings out of its
README: Maven coordinates, a custom repository, manifest `meta-data`,
permissions, toolchain flags. Every app repeats that transcription, every version
bump risks silent drift, and when the package is a **transitive** dependency the
person on the hook may not know it is in the tree at all.

The package knows what it needs. The app author is the one obliged to say it.
That inversion **is** the problem.

## The model

WIP.

## License

[MIT](LICENSE)
