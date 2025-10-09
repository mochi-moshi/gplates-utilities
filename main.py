
if __name__ == "__main__":
    import sys, os


    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtGui import QIcon
    from core.session import Session
    from ui.improved_geological_operations_window import ImprovedGeologicalOperationsWindow
    from media import LOGO_PATH
    
    print(os.path.dirname(__file__), LOGO_PATH)
    try:
        from ctypes import windll  # Only exists on Windows.
        myappid = 'moshi-mochi.gplates-utilities.app.0.3.0'
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except ImportError:
        pass
    
    app = QApplication(sys.argv)
    app.setApplicationName("Geological Operations Suite")
    app.setWindowIcon(QIcon(LOGO_PATH))
    # session = Session()

    # main_window = MainWindow(session)
    # main_window.show()

    # sys.exit(app.exec())
    
    # Set application style
    app.setStyleSheet("""
        QTabWidget::pane {
            border: 1px solid #C0C0C0;
            background-color: white;
        }
        
        QTabBar::tab {
            background-color: #f0f0f0;
            padding: 8px 16px;
            margin-right: 2px;
            border: 1px solid #C0C0C0;
            border-bottom-color: #C0C0C0;
        }
        
        QTabBar::tab:selected {
            background-color: white;
            border-bottom-color: white;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #e6f3ff;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #C0C0C0;
            border-radius: 5px;
            margin-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 10px 0 10px;
        }
    """)
    
    session = Session()

    window = ImprovedGeologicalOperationsWindow(session)
    window.show()
    
    sys.exit(app.exec_())