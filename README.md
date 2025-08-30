# GPlates Utilities - Geological Operations Suite

GPlates Utilities is a comprehensive, open-source geological modeling suite designed to make advanced [GPlates](https://www.gplates.org/) operations accessible through an intuitive graphical interface. This tool bridges the gap between complex geological modeling and user-friendly software, enabling researchers and students to perform sophisticated plate tectonic reconstructions without extensive programming knowledge.

Built with Python using PyGPlates, NumPy, and PySide6, the suite provides a modern tabbed interface with guided workflows for geological operations.

## Key Features

### 🌍 **Geological Processes & Worldbuilding**

- **Continental Rifting**: Model rift formation and continental breakup with realistic plate splitting algorithms
- **Subduction Dynamics**: Simulate subduction zone processes and their effects on plate boundaries  
- **Seafloor Spreading**: Model mid-ocean ridge spreading and oceanic plate creation
- **Plate Reconstruction**: Advanced time-based geological reconstructions with proper rotation models

### 🗺️ **Plate Operations & Geometry**

- **Feature Splitting**: Split polygon and line features using rifts, subduction zones, or custom boundaries
- **Boolean Operations**: Union, intersect, or difference operations on arbitrary polygon features
- **Line Intersection Tools**: Clean up and split line features (rifts, subduction zones, mid-ocean ridges)
- **Geometric Validation**: Built-in validation for geological feature integrity and consistency

### ⚙️ **Rotation Management & Modeling**

- **Rotation Model Creation**: Initialize rotation models from existing geological features
- **Plate ID Management**: Create new plates with proper rotation entries and time constraints
- **Model Validation**: Comprehensive rotation model validation and consistency checking
- **Temporal Continuity**: Ensure proper time-based geological reconstructions

### 🎯 **Advanced Filtering & Data Management**

- **Time-Based Filtering**: Filter features by geological time periods and valid time ranges
- **Plate ID Filtering**: Organize and filter features by reconstruction plate IDs
- **Feature Type Filtering**: Work with specific geological feature types (polygons, lines, points)
- **Multi-Collection Support**: Load, unload, and manage multiple feature collections simultaneously

### 💾 **Project Management & Workflow**

- **Project Persistence**: Save and reload complete project states with all loaded data
- **Session Management**: Maintain geological modeling sessions across application restarts
- **Export Capabilities**: Save results in standard GPlates formats (.gpml, .rot files)
- **Batch Operations**: Process multiple geological features efficiently

## Installation & Setup

### Prerequisites

- **Python 3.13+** (developed and tested with Python 3.13.1)
- **PyGPlates 1.0.0** (essential for geological operations)
- **PySide6** (for the modern Qt6-based interface)

### Recommended Installation (Virtual Environment)

Using a Python virtual environment is strongly recommended to avoid dependency conflicts:

```bash
# Create and activate virtual environment
python -m venv gplates-env

# On Windows:
gplates-env\Scripts\activate

# On macOS/Linux:
source gplates-env/bin/activate

# Clone the repository
git clone https://github.com/mochi-moshi/gplates-utilities.git
cd gplates-utilities

# Install dependencies
pip install -r requirements.txt

# Launch the application
python main.py
```

### Quick Installation (System-wide)

For direct installation without virtual environment:

```bash
git clone https://github.com/mochi-moshi/gplates-utilities.git
cd gplates-utilities
pip install -r requirements.txt
python main.py
```

### Dependencies

The application requires these key packages:

- `pygplates==1.0.0` - Core geological reconstruction library
- `PySide6==6.9.1` - Modern Qt6-based GUI framework  
- `numpy==2.3.1` - Numerical computing support

### Troubleshooting Installation

**PyGPlates Installation Issues**: PyGPlates can be challenging to install. If you encounter issues:

- Ensure you have the correct Python version (3.9-3.13 recommended)
- On Windows, you may need Visual C++ redistributables
- Consider using conda: `conda install -c conda-forge pygplates`

**Qt/PySide6 Issues**: If the GUI doesn't start:

- Verify PySide6 installation: `python -c "from PySide6.QtWidgets import QApplication"`
- On Linux, you may need additional Qt6 system packages

## Getting Started

After installation, launch the application with `python main.py`. The interface is organized into several main sections:

### 🏠 **Welcome Tab**

- Overview of available operations and recent projects
- Quick access to commonly used features
- Guided workflow recommendations

### 🌋 **Geological Processes**

- **Subduction & Rifting**: Model continental rifting and subduction zone dynamics
- **Divergent Boundaries**: Simulate seafloor spreading processes
- **Plate Reconstructions**: Time-based geological reconstructions

### 🗺️ **Plate Operations**

- **Feature Splitting**: Split geological features using boundaries or intersection points
- **Boolean Operations**: Union, intersect, or difference operations on polygons
- **Geometry Cleanup**: Clean up and validate geological feature geometries

### ⚙️ **Rotation Management**

- **Model Initialization**: Create rotation models from geological features
- **Plate Creation**: Generate new plates with proper rotation entries
- **Validation Tools**: Ensure rotation model consistency and completeness

### 💾 **Data Management**

- Load and manage multiple GPlates feature collections (.gpml files)
- Filter features by time, plate ID, and feature type
- Save projects and export results in standard formats

## Project Architecture

### Core Modules

- `core/` - Geological algorithms and session management
  - `worldbuilding/` - Geological process modeling (rift, subduct, diverge)
  - `rotations.py` - Rotation model creation and management
  - `plate_splitter.py` - Advanced plate splitting algorithms
- `ui/` - Modern Qt6-based user interface components
  - `improved_*_window.py` - Main operation windows
  - `widgets/` - Reusable UI components
  - `components/` - Process workflow components

## Help & Support

### 🐛 **Found a Bug?**

Please open a new issue on this project, or comment on existing issues that match your experience. Issues are triaged and addressed as quickly as possible.

### 📖 **Need Help?**

- Check the built-in help tooltips throughout the interface
- Examine the test data in `tests/` for example workflows
- Review the geological process documentation in the code

## Development Roadmap

### Current Version: v0.3.0

- [x] Comprehensive UI overhaul with tabbed interface
- [x] Advanced geological process modeling (rift, subduct, diverge)
- [x] Rotation management and validation tools
- [x] Boolean operations for polygon features

### Future Enhancements

- [ ] **Statistics & Analysis**: Feature area calculations, plate motion statistics
- [ ] **Topology Support**: Enhanced geological topology generation and validation
- [ ] **Automated Workflows**: Pre-configured workflows for common geological scenarios

## Technical References & Credits

### Algorithmic Foundations

This project builds on established geological and mathematical algorithms:

- **Spherical Geometry**: Implementation based on [spherical arc intersection algorithms](https://blog.mbedded.ninja/mathematics/geometry/spherical-geometry/finding-the-intersection-of-two-arcs-that-lie-on-a-sphere/) for accurate geological feature processing
- **PyGPlates**: Leverages the comprehensive [GPlates](https://www.gplates.org/) geological reconstruction framework

### Visual Resources

- **Icons**: South America continent outline from [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Continents.svg)
- **UI Icons**: Scissors and operation icons from [UXWing](https://uxwing.com/cut-scissor-icon/)

### Development Contributors

- **Initial Development**: [@iccan-coder](https://github.com/iccan-coder)
- **Worldbuilding Development**: [@mochi-moshi](https://github.com/mochi-moshi)
- **UI/UX Enhancement**: Claude Code for comprehensive interface development and workflow design
- **Geological Algorithm Implementation**: Based on established GPlates and PyGPlates methodologies

## Contributing

GPlates Utilities is an open-source project welcoming contributions from the geological modeling and software development communities.

### How to Contribute

1. **Fork the repository** and create a feature branch
2. **Follow the existing code style** and architectural patterns
3. **Add tests** for new geological algorithms or UI components (TODO for me)
4. **Document new features** with clear geological context
5. **Submit pull requests** with detailed descriptions of changes

### Areas for Contribution

- Geological algorithm optimization and validation
- Additional export format support
- UI/UX improvements and accessibility features
- Documentation and geological workflow examples
- Testing with diverse geological datasets

## License

This project is licensed under the **MIT License**. See the `LICENSE` file for complete terms.

The MIT License permits use, modification, and distribution while maintaining attribution to original contributors and providing the software "as is" without warranty.
