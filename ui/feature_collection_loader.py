from PyQt5.QtWidgets import QAbstractItemView, QFileDialog, QHBoxLayout, QLabel, QListView, QMessageBox, QPushButton, QVBoxLayout, QWidget, QLayout
from core.session import Session

class FeatureCollectionLoader(QWidget):
    def __init__(self, session: Session):
        super().__init__()

        self.session = session

        self.setWindowTitle("Add and Remove Feature Collections - GPlateUtils")

        add_button = QPushButton("Add")
        add_button.clicked.connect(self.load_feature_collection)

        self.remove_button = QPushButton("Remove")
        self.remove_button.setEnabled(False)     # Button is disabled until a list item is selected
        self.remove_button.clicked.connect(self.on_remove)

        self.fc_list = QListView()
        self.fc_list.setModel(session.get_feature_collection_model())
        self.fc_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)      # Do not allow editing the names
        self.fc_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)  # Only one name may be selected at a time
        self.fc_list.clicked.connect(self.on_selection_changed)

        button_layout = QHBoxLayout()
        button_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        button_layout.addWidget(add_button)
        button_layout.addWidget(self.remove_button)

        reload_button = QPushButton('Reload All')
        reload_button.clicked.connect(lambda: (self.session.reload_features(), self.session.reload_rotation_model()))

        layout = QVBoxLayout()
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        layout.addWidget(QLabel("Here is a list of all loaded feature collections:"))
        layout.addWidget(self.fc_list)
        layout.addWidget(reload_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setMinimumSize(layout.minimumSize())
    
    def load_feature_collection(self):
        fc_filepaths, _ = QFileDialog.getOpenFileNames(self, "Open Feature Collection(s)", self.session._project_path if self.session._project_path else ".", "GPlates Markup Language (*.gpml)")
        if len(fc_filepaths) == 0:
            return

        self.session.load_feature_collections(fc_filepaths)
        
    
    def on_selection_changed(self):
        if not self.remove_button.isEnabled():
            self.remove_button.setEnabled(True)
    
    def on_remove(self):
        current_item_name = self.fc_list.currentIndex().data()
        self.remove_button.setEnabled(False)

        ret = QMessageBox.warning(self, "Remove Feature Collection", f"Are you sure you want to remove '{current_item_name}' from this project?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if ret == QMessageBox.StandardButton.Yes:
            self.session.unload_feature_collection(current_item_name)