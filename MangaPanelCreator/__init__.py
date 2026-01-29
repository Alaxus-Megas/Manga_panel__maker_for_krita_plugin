from krita import DockWidgetFactory, DockWidgetFactoryBase
from .manga_panel_docker import MangaPanelDocker

def initialize(krita_instance):
    factory = DockWidgetFactory("manga_panel_creator_id", 
                                DockWidgetFactoryBase.DockRight, 
                                MangaPanelDocker)
    krita_instance.addDockWidgetFactory(factory)
