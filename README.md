# Navigation System for USV

This project is a Python-based application designed for visualizing and setting a coverage path planning for an Unmanned Surface Vehicle (USV). The application outputs navigation points to guide the vehicle along a specified path, which can also be customized as per user requirements.

## Features
- Visualize coverage path planning for USVs.
- Generate navigation points for path following.
- Upload path points to a database firebase
- Customizable path planning to suit specific needs.
- import or setup maps or area for navigation 

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

1. Run the html file in the 'mapGenerating' folder to get cordinate for the area that you want to work with  

2. copie and paste the cordinates to the map_data you can use the testing cordinates already in the scripte 


4. Run the application:
    ```bash
    cd pathPlannig
    python3 main.py 
    ```


## Contributing
Contributions are welcome! Feel free to submit issues or pull requests to improve the project.

## Contact
For any questions or feedback, please contact [fedinasri.fsb@gmail.com].
