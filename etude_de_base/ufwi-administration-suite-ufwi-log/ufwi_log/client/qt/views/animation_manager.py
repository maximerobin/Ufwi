from PyQt4.QtCore import QObject, SIGNAL

from ufwi_log.client.qt.views.graphics_view import GraphicsView

class AnimationManager(QObject):

    __views = []
    __done = []

    def __init__(self, mainwindow):
        QObject.__init__(self)
        self.mainwindow = mainwindow
        self.animation_on = True
        self.nb_updated = 0
        self.auto_refresh = True
        self.mseconds = 30000
        self.lastPacket = False
        self.timer_id = None
        #if views.fragment.title == "LastPacket":
        #self.timer_id = self.startTimer(self.mseconds)

    def timerEvent(self, event):
        GraphicsView.UPDATE_ALL = True
        frags = self.mainwindow.frag_widgets
        for frag in frags:
            frag.view.emit(SIGNAL("autoRefresh"))

    def setAutoRefresh(self, auto_refresh, seconds):
        self.mseconds = seconds * 1000
        self.auto_refresh = auto_refresh

        self._initTimer()

    def _initTimer(self):
        if self.timer_id:
            self.killTimer(self.timer_id)
            self.timer_id = None

        if self.auto_refresh and self.lastPacket:
            self.timer_id = self.startTimer(self.mseconds)

    def autoRefresh(self):
        return self.auto_refresh

    def setEnableAnimation(self, animation_on):

        self.animation_on = not animation_on

        frags = self.mainwindow.frag_widgets
        for frag in frags:
            if frag.view.is_graphics_view:
                frag.view.animation_on = self.animation_on

    def addView(self, view):
        view.animation_on = self.animation_on
        if view.uuid not in AnimationManager.__views:
            AnimationManager.__views.append(view.uuid)

        if view.fragment.name == "LastPacket":
            self.lastPacket = True


        self.connect(view, SIGNAL('animation_done(QString)'), self.startNewAnimation)
        self.connect(view, SIGNAL("resized(QString)"), self.resizeEvent)

    def resizeEvent(self, uuid):
        if uuid in AnimationManager.__done:
            AnimationManager.__done.remove(uuid)
        if uuid not in AnimationManager.__views:
            AnimationManager.__views.append(uuid)

    def _addDoneAnimation(self, uuid):
        if uuid not in AnimationManager.__done:
            AnimationManager.__done.append(uuid)
        if uuid in AnimationManager.__views:
            AnimationManager.__views.remove(uuid)

    def _moveToAnimationDone(self, uuid):
        if uuid not in AnimationManager.__done:
            AnimationManager.__done.append(uuid)
        if uuid in AnimationManager.__views:
            AnimationManager.__views.remove(uuid)

    def startNewAnimation(self, uuid):
        self._moveToAnimationDone(uuid)

        if GraphicsView.IN_ANIMATION:
            return

        if len(self.__views) == 0 or not GraphicsView.UPDATE_ALL:
            AnimationManager.__views = AnimationManager.__done
            AnimationManager.__done = []
            GraphicsView.UPDATE_ALL = False
            return

        frags = self.mainwindow.frag_widgets

        is_graph_view = False
        cpt = 0
        while not is_graph_view and cpt < len(AnimationManager.__views):
            next_uuid = AnimationManager.__views[cpt]
            cpt += 1

            for frag in frags:
                if frag.view.uuid == next_uuid:
                    if frag.view.is_graphics_view:
                        is_graph_view = True
                        break;
                    else:
                        self._moveToAnimationDone(frag.view.uuid)
#                    break

        if not is_graph_view:
            self.init()

        for frag in frags:
            if frag.view.is_graphics_view:
                if self.animation_on:
                    if frag.view.uuid == next_uuid and frag.view.result:
                        GraphicsView.IN_ANIMATION = True
                        frag.view.show()
                        break
                else:
                    GraphicsView.IN_ANIMATION = False
                    frag.view.show()
            else:
                self._addDoneAnimation(frag.view.uuid)

    def init(self):
        AnimationManager.__views = list(set(AnimationManager.__views + AnimationManager.__done))
        AnimationManager.__done = []
        GraphicsView.UPDATE_ALL = True

    def reset(self):
        AnimationManager.__views = []
        AnimationManager.__done = []
        self.nb_updated = 0
        self.lastPacket = False

    def remove(self, uuid):
        if uuid in AnimationManager.__views:
            AnimationManager.__views.remove(uuid)
            self.nb_updated -= 1
        if uuid in AnimationManager.__done:
            AnimationManager.__done.remove(uuid)
            self.nb_updated -= 1
        GraphicsView.IN_ANIMATION = False
