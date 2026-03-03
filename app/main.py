"""AS1100 Sensor Data Collector - Main Application Entry Point."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

# Add app to path for imports
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from app.gui.main_window import MainWindow


def main():
    """Run the application."""
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
