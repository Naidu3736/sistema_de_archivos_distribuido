import sys
from PyQt6.QtWidgets import QApplication
from client.gui.app import FileManagerGUI

def main():
    app = QApplication(sys.argv)
    
    # Configurar fuente global
    font = app.font()
    font.setFamily("Segoe UI")
    font.setPointSize(9)
    app.setFont(font)
    
    window = FileManagerGUI()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()