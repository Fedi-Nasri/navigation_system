# Navigation System for USV

This project is a Python-based application designed for visualizing and setting a coverage path planning for an Unmanned Surface Vehicle (USV). The application outputs navigation points to guide the vehicle along a specified path, which can also be customized as per user requirements.

## Features
- Visualize coverage path planning for USVs.
- Generate navigation points for path following.
- Customizable path planning to suit specific needs.

## Prerequisites
Ensure you have Python installed on your system. This project requires Python 3.6 or higher.

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/your-repo/navigation_system.git
    cd navigation_system
    ```

2. Install the required Python libraries:
    ```bash
    pip install pyproj numpy opencv-python PyQt5
    ```

## Usage

1. Run the html file to get cordinate for the area that you need to work in 

2. Run the python Generate map to generate a pgm file that have the picture of map  in pgm formate
    ```bash
    python generatePGM_Map.py
    ```
3. copie the map.pgm in  the pathplannig folder 

4. Run the application:
    ```bash
    python main.py map.pgm
    ```


## Contributing
Contributions are welcome! Feel free to submit issues or pull requests to improve the project.

## Contact
For any questions or feedback, please contact [fedinasri.fsb@gmail.com].
