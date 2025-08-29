# GPlates Utilities

GPlates Utilities is an open-source tool (in future, set of tools) for making the use of [GPlates](https://www.gplates.org/) easier for casual users.
This tool is written in Python using PyGPlates and NumPy packages, with a Qt GUI powered by PySide.

## Features

The current version (v0.2.0) allows you to:

- Split features with polygon geometry using a `ContinentalRift` or `SubductionZone` feature at a given time in the reconstruction history.
- Split two lines features based on their point of intersection. This let's you clean up rifts, as well as split subduction zones and MORs.
- Union, intersect, or difference any two arbitrary polygon features. Useful for merging land masses.
- Filter features by valid time and plate ID(s).
- Easily load, unload, and reload feature collections.
- Project files (`.json`) allow for easy return to ongoing projects.
- Save newly created split features in a new feature collection[^1]

[^1]: Currently, this has to be a **new** feature collection, as the saving process is destructive

## Installation

If you know how to set one up, I would recommend using a Python virtual environment to not pollute your main installation.

0. Ensure [Python](https://www.python.org/) is installed and updated
    - This tool was developed with version `3.13.1`, I cannot guarantee that it will work with previous versions
1. Either download the [latest release](https://github.com/iccan-coder/gplates-utilities/releases/latest) or clone this repository with `git clone https://github.com/iccan-coder/gplates-utilities.git`
2. Open a terminal in the downloaded folder or navigate to the clones repository with `cd gplates-utilities`
3. Install the required packages with `pip install -r requirements.txt`
4. Run the application with `python main.py`

## How to Use

**v0.2 introduction video coming soon!**

Video below is outdated now but still explains the basic operations, even if buttons have moved.

[![Watch the video](https://img.youtube.com/vi/Vikk2rcL9M4/maxresdefault.jpg)](https://www.youtube.com/watch?v=Vikk2rcL9M4)

## Help! I've encountered a bug!

Please open a new issue on this project, or comment on existing issues that match what you have experienced. I will try to respond quickly but please understand that I am just one person atm.

## Future Development

Aside from ongoing bug hunts, there are plans for more features in future version.
Note that this listing is just a rough overview, goals may change or be dropped as development continues.

### v0.2

- [X] New screen for splitting line features using rifts (useful for quickly splitting `SubductionZone` features) _(implemented v0.2.0)_
- [X] [Boolean operations](https://en.wikipedia.org/wiki/Boolean_operations_on_polygons) for polygon features (at least Union and Intersection)
- [ ] 1-Click Removal of duplicate points on geometries (Topologies can cause these)
- [ ] Statistics screen (for example, total feature area by plate ID) with the ability to query features by plate ID, valid time, feature type.

### One day ...

These features will require more research into how they work (or how best to tackle this) before I can plan them in:

- [ ] Recreating flow lines (having to manually do this is pretty annoying)
- [ ] Rotation file tools (creating new plates, have A stop following B, make plates follow each other)
- [X] Splitting a polygon feature with another polygon (useful for subducted `OceanCrust` features)
- [ ] Save split features in original feature collection instead of creating new one (I first have to ensure that this tool does not mess things up)

## Credits

I just want to say that without [this post](https://blog.mbedded.ninja/mathematics/geometry/spherical-geometry/finding-the-intersection-of-two-arcs-that-lie-on-a-sphere/) I would have had a much harder time making the splitting
work. Spherical geometry is just not something I know anything about.

- South America featured in icons taken from [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Continents.svg)
- Scissors featured in icons taken from [uxwing](https://uxwing.com/cut-scissor-icon/)

## Contributing

GPlates Utilities is an open-source project and we welcome contributions from the community.

If you'd like to contribute, please fork the repository and make changes as you'd like. Pull requests are warmly welcome.

## License

This project is licensed under the MIT License. Please check out the full license terms in the `LICENSE.md` file
